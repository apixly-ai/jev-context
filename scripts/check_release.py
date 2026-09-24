"""Keep Git tags, Python metadata and npm versions aligned."""

import json
import re
import sys
from pathlib import Path

version = re.search(
    r'^version = "([^"]+)"', Path("pyproject.toml").read_text(encoding="utf-8"), re.M
).group(1)
package = json.loads(Path("package.json").read_text(encoding="utf-8"))
if sys.argv[1] != "v" + version or package["version"] != version:
    raise SystemExit("Tag, npm and Python versions must match")
print("Release version verified:", version)
