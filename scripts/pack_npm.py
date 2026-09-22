"""Stage the npm package with registry-friendly documentation links."""

import json
import re
import shutil
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
package = json.loads((root / "package.json").read_text())
stage = root / "build/npm/main"
if stage.exists():
    shutil.rmtree(stage)
stage.mkdir(parents=True)
for name in package["files"]:
    source = root / name
    target = stage / name
    if source.is_dir():
        shutil.copytree(source, target)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
base = f"https://github.com/apixly-ai/jev-context/blob/v{package['version']}/"
raw = f"https://raw.githubusercontent.com/apixly-ai/jev-context/v{package['version']}/"
for name in ("README.md", "README.zh-CN.md"):
    p = stage / name
    text = p.read_text()
    text = re.sub(r"(!\[[^\]]*\]\()([^:)#]+)(\))", lambda m: m[1] + raw + m[2] + m[3], text)
    text = re.sub(r"(\]\()([^:)#]+)(\))", lambda m: m[1] + base + m[2] + m[3], text)
    text = re.sub(r'(src=")([^":]+)(")', lambda m: m[1] + raw + m[2] + m[3], text)
    text = re.sub(
        r'(href=")([^"#:]\S*?)(")',
        lambda m: m[0] if "://" in m[2] else m[1] + base + m[2] + m[3],
        text,
    )
    p.write_text(text)
package.pop("scripts", None)
(stage / "package.json").write_text(json.dumps(package, indent=2) + "\n")
(root / "dist").mkdir(exist_ok=True)
subprocess.run(
    ["npm", "pack", "--ignore-scripts", "--pack-destination", str(root / "dist")],
    cwd=stage,
    check=True,
)
