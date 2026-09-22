"""Verify that a release tag matches package metadata before uploading artifacts."""

import re
import sys
from pathlib import Path

text = Path("pyproject.toml").read_text()
version = re.search(r'^version = "([^"]+)"', text, re.M).group(1)
if sys.argv[1] != "v" + version:
    raise SystemExit("Tag does not match package version")
print("Release version verified:", version)
