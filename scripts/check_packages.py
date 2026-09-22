"""Inspect built archives for private paths and required native distribution files."""

import re
import tarfile
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
patterns = [
    re.compile(rb"/Users/[A-Za-z][^/\s]*"),
    re.compile(rb"/home/[A-Za-z][^/\s]*"),
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]
count = 0
for archive in (root / "dist").glob("*"):
    if archive.suffix == ".whl":
        with zipfile.ZipFile(archive) as handle:
            entries = [
                (name, handle.read(name)) for name in handle.namelist() if not name.endswith("/")
            ]
    elif archive.name.endswith((".tgz", ".tar.gz")):
        with tarfile.open(archive) as handle:
            entries = [
                (member.name, handle.extractfile(member).read())
                for member in handle.getmembers()
                if member.isfile()
            ]
    else:
        continue
    names = {name for name, _ in entries}
    if archive.name.startswith("apixly-jev-filter-") and any(
        f"-{p}-" in archive.name for p in ("darwin", "linux")
    ):
        for required in (
            "package/BUILDINFO.json",
            "package/bin/jev-filter",
            "package/bin/rg",
            "package/THIRD_PARTY_LICENSES/PYTHON-LICENSE.txt",
            "package/THIRD_PARTY_LICENSES/OPENSSL-LICENSE.txt",
        ):
            if required not in names:
                raise SystemExit(f"{archive.name}: missing {required}")
    for name, body in entries:
        if name.endswith("direct_url.json"):
            raise SystemExit(f"{archive.name}: installer origin metadata must not ship")
        if len(body) > 2_000_000:
            continue
        try:
            body.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if any(pattern.search(body) for pattern in patterns):
            raise SystemExit(f"{archive.name}: private content in {name}")
    count += 1
if not count:
    raise SystemExit("No built package archives found")
print(f"Inspected {count} built archives: public-content and native manifest checks passed.")
