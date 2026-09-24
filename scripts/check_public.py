"""Fail when publishable source contains maintainer paths or obvious private artifacts."""

import re
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
try:
    files = [
        root / p
        for p in subprocess.check_output(["git", "ls-files"], cwd=root, text=True).splitlines()
    ]
except subprocess.CalledProcessError:
    files = [
        p
        for p in root.rglob("*")
        if p.is_file() and not any(x.startswith(".") for x in p.relative_to(root).parts)
    ]
patterns = [
    re.compile(r"/Users/[A-Za-z][^/\s]*"),
    re.compile(r"/home/[A-Za-z][^/\s]*"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
]
problems = []
for p in files:
    if not p.is_file():
        continue
    if p.suffix.lower() in (".png", ".jpg", ".whl", ".gz"):
        continue
    try:
        text = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    if any(pattern.search(text) for pattern in patterns):
        problems.append(str(p.relative_to(root)))
if problems:
    raise SystemExit("Public-content check failed: " + ", ".join(problems))
print("Public-content check passed.")
