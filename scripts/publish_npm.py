"""Publish verified release tarballs in dependency order, resuming only identical versions."""

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import tarfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REGISTRY = "https://registry.npmjs.org/"
SUFFIXES = ("-darwin-arm64", "-darwin-x64", "-linux-arm64", "-linux-x64", "")
REPOSITORY = "git+https://github.com/apixly-ai/jev-filter.git"


def verified_packages(directory, tag):
    if not re.fullmatch(r"v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", tag):
        raise ValueError("An exact stable release tag vMAJOR.MINOR.PATCH is required")
    version = tag[1:]
    directory = Path(directory)
    expected = {f"apixly-jev-filter{s}-{version}.tgz" for s in SUFFIXES}
    if {p.name for p in directory.glob("*.tgz")} != expected:
        raise ValueError("Exactly the four native tarballs and main tarball are required")
    checksums = {}
    for line in (directory / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, filename = line.split()
        if filename in checksums or not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise ValueError("Invalid or duplicate checksum")
        checksums[filename] = digest
    packages = []
    for suffix in SUFFIXES:
        name = "@apixly/jev-filter" + suffix
        filename = f"apixly-jev-filter{suffix}-{version}.tgz"
        path = directory / filename
        if path.is_symlink():
            raise ValueError("Release artifacts must be regular files")
        body = path.read_bytes()
        if hashlib.sha256(body).hexdigest() != checksums.get(filename):
            raise ValueError("Release checksum mismatch: " + filename)
        with tarfile.open(path, "r:gz") as archive:
            entries = [m for m in archive.getmembers() if m.name == "package/package.json"]
            if len(entries) != 1 or not entries[0].isfile() or entries[0].size > 100000:
                raise ValueError("Invalid package manifest")
            manifest = json.load(archive.extractfile(entries[0]))
        if (manifest.get("name"), manifest.get("version")) != (name, version):
            raise ValueError("Package identity/version mismatch: " + filename)
        if manifest.get("repository", {}).get("url") != REPOSITORY:
            raise ValueError("Package repository mismatch")
        if not suffix and manifest.get("optionalDependencies") != {
            "@apixly/jev-filter" + s: version for s in SUFFIXES if s
        }:
            raise ValueError("Native dependency versions do not match the release")
        packages.append(
            dict(
                name=name,
                version=version,
                file=filename,
                path=str(path),
                integrity="sha512-" + base64.b64encode(hashlib.sha512(body).digest()).decode(),
            )
        )
    return packages


def registry_integrity(package):
    url = REGISTRY + urllib.parse.quote(package["name"], safe="") + "/" + package["version"]
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise RuntimeError(f"Registry lookup failed (HTTP {exc.code})") from None
    if data.get("name") != package["name"] or data.get("version") != package["version"]:
        raise ValueError("Registry identity mismatch")
    integrity = data.get("dist", {}).get("integrity")
    if not isinstance(integrity, str) or not integrity.startswith("sha512-"):
        raise ValueError("Registry did not return SHA-512 integrity")
    return integrity


def registry_index_integrity(package):
    url = REGISTRY + urllib.parse.quote(package["name"], safe="")
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise RuntimeError(f"Registry index lookup failed (HTTP {exc.code})") from None
    if data.get("name") != package["name"]:
        raise ValueError("Registry index identity mismatch")
    return data.get("versions", {}).get(package["version"], {}).get("dist", {}).get("integrity")


def wait_for_index(packages, lookup=registry_index_integrity, sleep=time.sleep):
    for attempt in range(61):
        pending = []
        for package in packages:
            integrity = lookup(package)
            if integrity is None:
                pending.append(package["name"])
            elif integrity != package["integrity"]:
                raise ValueError("Registry index contains different bytes: " + package["name"])
        if not pending:
            return
        print(json.dumps({"status": "waiting_for_registry_index", "packages": pending}), flush=True)
        if attempt == 60:
            raise RuntimeError("Registry index is not ready; uploads were not repeated")
        sleep(10)


def upload(package):
    subprocess.run(
        [
            "npm",
            "publish",
            str(Path(package["path"]).resolve(strict=True)),
            "--access",
            "public",
            "--provenance",
            "--registry",
            REGISTRY,
            "--ignore-scripts",
        ],
        check=True,
    )


def publish_packages(packages, lookup=registry_integrity, publish=upload, sleep=time.sleep):
    # Check every existing version before any write. A version collision is not a retry.
    existing = {p["name"]: lookup(p) for p in packages}
    for p in packages:
        if existing[p["name"]] not in (None, p["integrity"]):
            raise ValueError("Registry already contains different bytes: " + p["name"])
    result = []
    for p in packages:
        status = "already_published"
        if existing[p["name"]] is None:
            publish(p)  # Never retry an uncertain upload; a rerun inspects registry first.
            status = "published"
            for attempt in range(31):
                observed = lookup(p)
                if observed == p["integrity"]:
                    break
                if observed is not None:
                    raise ValueError("Published version has different registry integrity")
                if attempt == 30:
                    raise RuntimeError("Published version is not visible; inspect before rerunning")
                sleep(min(2**attempt, 8))
        row = {"name": p["name"], "version": p["version"], "status": status}
        result.append(row)
        print(json.dumps(row), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--directory", default="artifacts")
    parser.add_argument("--publish", action="store_true", help="Publish using GitHub OIDC")
    args = parser.parse_args()
    packages = verified_packages(args.directory, args.tag)
    if args.publish:
        if not all(
            os.environ.get(k)
            for k in ("ACTIONS_ID_TOKEN_REQUEST_URL", "ACTIONS_ID_TOKEN_REQUEST_TOKEN")
        ):
            raise ValueError("Publication requires a GitHub Actions OIDC identity")
        if os.environ.get("GITHUB_REPOSITORY") != "apixly-ai/jev-filter":
            raise ValueError("Publication is restricted to the maintained repository")
        publish_packages(packages)
        wait_for_index(packages)
    else:
        print(
            json.dumps(
                [{"name": p["name"], "version": p["version"], "verified": True} for p in packages]
            )
        )


if __name__ == "__main__":
    main()
