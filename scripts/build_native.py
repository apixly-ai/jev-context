"""Build a platform npm tarball containing the interpreter and runtime dependencies."""

import hashlib
import http.client
import io
import json
import platform
import shutil
import ssl
import subprocess
import sys
import tarfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def download(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                return response.read()
        except (OSError, http.client.IncompleteRead):
            if attempt == 2:
                raise
            time.sleep(attempt + 1)
    raise RuntimeError("Download failed")


def main():
    package = json.loads((ROOT / "package.json").read_text())
    os_name = {"Darwin": "darwin", "Linux": "linux"}[platform.system()]
    arch = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "x64", "AMD64": "x64"}[
        platform.machine()
    ]
    target = f"{os_name}-{arch}"
    out = ROOT / "build/native" / target
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--name",
        "jev-filter",
        "--distpath",
        str(out),
        "--workpath",
        str(ROOT / "build/pyinstaller" / target),
        "--specpath",
        str(ROOT / "build"),
        "--copy-metadata",
        "jev-filter",
        "--collect-all",
        "jev_context",
        "--collect-all",
        "certifi",
        "--collect-all",
        "tiktoken",
        "--collect-all",
        "tiktoken_ext",
        "--exclude-module",
        "matplotlib",
        "--exclude-module",
        "playwright",
        "--exclude-module",
        "pytest",
    ]
    for grammar in [
        "tree_sitter",
        "tree_sitter_javascript",
        "tree_sitter_typescript",
        "tree_sitter_go",
    ]:
        command += ["--collect-all", grammar]
    subprocess.run([*command, str(ROOT / "scripts/native_entry.py")], check=True, cwd=ROOT)
    stage = ROOT / "build/npm" / target
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    shutil.copytree(out / "jev-filter", stage / "bin")
    # Installer origin metadata can contain a local checkout path; it is not runtime data.
    for metadata_file in (stage / "bin").rglob("direct_url.json"):
        metadata_file.unlink()
    metadata = {
        "name": f"@apixly/jev-filter-{target}",
        "version": package["version"],
        "description": "Platform runtime for Jev Filter",
        "os": [os_name],
        "cpu": [arch],
        "license": "MIT",
        "repository": package["repository"],
        "files": ["bin", "LICENSE", "NOTICE", "THIRD_PARTY_LICENSES", "BUILDINFO.json"],
    }
    (stage / "package.json").write_text(json.dumps(metadata, indent=2) + "\n")
    for name in ["LICENSE", "NOTICE"]:
        shutil.copy2(ROOT / name, stage / name)
    # Include installed runtime license texts alongside the bundled binaries.
    import importlib.metadata

    licenses = stage / "THIRD_PARTY_LICENSES"
    licenses.mkdir()
    for name in [
        "httpx",
        "httpcore",
        "anyio",
        "certifi",
        "idna",
        "h11",
        "tree-sitter",
        "tree-sitter-javascript",
        "tree-sitter-typescript",
        "tree-sitter-go",
        "pyinstaller",
        "tiktoken",
        "regex",
        "requests",
        "urllib3",
        "charset-normalizer",
    ]:
        dist = importlib.metadata.distribution(name)
        for file in dist.files or []:
            if any(token in file.name.lower() for token in ("license", "copying", "notice")):
                source = Path(dist.locate_file(file))
                if source.is_file():
                    shutil.copy2(source, licenses / f"{name}-{file.name}")
    python_license = (
        f"https://raw.githubusercontent.com/python/cpython/v{platform.python_version()}/LICENSE"
    )
    (licenses / "PYTHON-LICENSE.txt").write_bytes(download(python_license))
    rg = json.loads((ROOT / "npm/ripgrep.json").read_text())[target]
    archive = download(rg["url"])
    if hashlib.sha256(archive).hexdigest() != rg["sha256"]:
        raise ValueError("ripgrep release digest mismatch")
    found = False
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        for member in tar.getmembers():
            name = Path(member.name).name
            if not member.isfile():
                continue
            if name == "rg":
                (stage / "bin/rg").write_bytes(tar.extractfile(member).read())
                (stage / "bin/rg").chmod(0o755)
                found = True
            elif name.startswith(("LICENSE", "COPYING", "UNLICENSE")):
                (licenses / f"ripgrep-{name}").write_bytes(tar.extractfile(member).read())
    if not found:
        raise ValueError("ripgrep executable missing")
    openssl_version = ssl.OPENSSL_VERSION.split()[1]
    openssl_license = (
        f"https://raw.githubusercontent.com/openssl/openssl/openssl-{openssl_version}/LICENSE.txt"
    )
    (licenses / "OPENSSL-LICENSE.txt").write_bytes(download(openssl_license))
    inventory = {
        "package": metadata["name"],
        "version": metadata["version"],
        "target": target,
        "python": platform.python_version(),
        "openssl": openssl_version,
        "pyinstaller": importlib.metadata.version("pyinstaller"),
        "ripgrep_archive_sha256": rg["sha256"],
        "runtime_files": {
            str(file.relative_to(stage)): {
                "bytes": file.stat().st_size,
                "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
            }
            for file in sorted((stage / "bin").rglob("*"))
            if file.is_file()
        },
    }
    (stage / "BUILDINFO.json").write_text(json.dumps(inventory, indent=2) + "\n")
    destination = ROOT / "dist"
    destination.mkdir(exist_ok=True)
    subprocess.run(
        ["npm", "pack", "--ignore-scripts", "--pack-destination", str(destination)],
        cwd=stage,
        check=True,
    )


if __name__ == "__main__":
    main()
