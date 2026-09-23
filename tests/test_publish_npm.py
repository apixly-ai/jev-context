"""Offline release transactions: artifacts, retries and partial-publication recovery."""

import hashlib
import importlib.util
import io
import json
import tarfile
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "publish_npm", Path(__file__).resolve().parents[1] / "scripts/publish_npm.py"
)
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


@pytest.fixture
def artifacts(tmp_path):
    for suffix in ("-darwin-arm64", "-darwin-x64", "-linux-arm64", "-linux-x64", ""):
        name = "@apixly/jev-filter" + suffix
        manifest = {
            "name": name,
            "version": "0.2.0",
            "repository": {"url": "git+https://github.com/apixly-ai/jev-filter.git"},
        }
        if not suffix:
            manifest["optionalDependencies"] = {
                "@apixly/jev-filter" + s: "0.2.0"
                for s in ("-darwin-arm64", "-darwin-x64", "-linux-arm64", "-linux-x64")
            }
        payload = json.dumps(manifest).encode()
        with tarfile.open(tmp_path / f"apixly-jev-filter{suffix}-0.2.0.tgz", "w:gz") as tar:
            info = tarfile.TarInfo("package/package.json")
            info.size = len(payload)
            tar.addfile(info, io.BytesIO(payload))
    (tmp_path / "SHA256SUMS").write_text(
        "".join(
            hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.name + "\n"
            for p in tmp_path.glob("*.tgz")
        )
    )
    return tmp_path


def test_all_artifacts_verified_and_main_last(artifacts):
    packages = publisher.verified_packages(artifacts, "v0.2.0")
    assert len(packages) == 5
    assert packages[-1]["name"] == "@apixly/jev-filter"
    (artifacts / packages[0]["file"]).write_bytes(b"bad")
    with pytest.raises(ValueError, match="checksum"):
        publisher.verified_packages(artifacts, "v0.2.0")


def test_missing_and_extra_artifacts_fail_closed(artifacts):
    (artifacts / "unexpected.tgz").write_bytes(b"not allowed")
    with pytest.raises(ValueError):
        publisher.verified_packages(artifacts, "v0.2.0")
    (artifacts / "unexpected.tgz").unlink()
    next(artifacts.glob("*.tgz")).unlink()
    with pytest.raises(ValueError):
        publisher.verified_packages(artifacts, "v0.2.0")


def test_partial_release_resumes_without_republishing(artifacts):
    packages = publisher.verified_packages(artifacts, "v0.2.0")
    registry = {packages[0]["name"]: packages[0]["integrity"]}
    published = []

    def publish(package):
        published.append(package["name"])
        registry[package["name"]] = package["integrity"]

    results = publisher.publish_packages(
        packages, lookup=lambda p: registry.get(p["name"]), publish=publish, sleep=lambda _: None
    )
    assert len(published) == 4
    assert published[-1] == "@apixly/jev-filter"
    assert results[0]["status"] == "already_published"
    publisher.publish_packages(
        packages, lookup=lambda p: registry.get(p["name"]), publish=publish, sleep=lambda _: None
    )
    assert len(published) == 4


def test_mismatched_existing_version_stops_before_any_write(artifacts):
    packages = publisher.verified_packages(artifacts, "v0.2.0")
    calls = []

    def lookup(package):
        return "sha512-wrong" if package == packages[-1] else None

    with pytest.raises(ValueError, match="different"):
        publisher.publish_packages(packages, lookup=lookup, publish=calls.append)
    assert calls == []


def test_failed_upload_never_blindly_retries_or_publishes_main(artifacts):
    packages = publisher.verified_packages(artifacts, "v0.2.0")
    calls = []

    def publish(package):
        calls.append(package["name"])
        raise RuntimeError("uncertain upload")

    with pytest.raises(RuntimeError):
        publisher.publish_packages(packages, lookup=lambda p: None, publish=publish)
    assert calls == [packages[0]["name"]]


def test_visibility_failure_stops_before_main(artifacts):
    packages = publisher.verified_packages(artifacts, "v0.2.0")
    calls = []
    with pytest.raises(RuntimeError, match="visible"):
        publisher.publish_packages(
            packages, lookup=lambda p: None, publish=calls.append, sleep=lambda _: None
        )
    assert len(calls) == 1


@pytest.mark.parametrize("tag", ["main", "v0.2.0;echo bad", "../v0.2.0", "v01.2.3"])
def test_untrusted_tags_rejected(artifacts, tag):
    with pytest.raises(ValueError):
        publisher.verified_packages(artifacts, tag)


def test_upload_uses_unambiguous_local_tarball_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    artifact = tmp_path / "artifacts/example.tgz"
    artifact.parent.mkdir()
    artifact.write_bytes(b"synthetic")
    calls = []
    monkeypatch.setattr(publisher.subprocess, "run", lambda argv, **kw: calls.append(argv))
    publisher.upload({"path": "artifacts/example.tgz"})
    assert calls[0][2] == str(artifact.resolve())
