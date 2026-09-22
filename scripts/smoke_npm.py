"""Install actual tarballs and run without any system Python/ripgrep on PATH."""

import json
import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
package = json.loads((root / "package.json").read_text())
os_name = {"Darwin": "darwin", "Linux": "linux"}[platform.system()]
arch = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "x64", "AMD64": "x64"}[platform.machine()]
version = package["version"]
with tempfile.TemporaryDirectory() as temp:
    base = Path(temp)
    subprocess.run(
        [
            "npm",
            "install",
            "--prefix",
            str(base),
            "--ignore-scripts",
            "--omit=optional",
            "--no-audit",
            "--no-fund",
            str(root / f"dist/apixly-jev-context-{version}.tgz"),
            str(root / f"dist/apixly-jev-context-{os_name}-{arch}-{version}.tgz"),
        ],
        check=True,
    )
    node_bin = base / "only-node"
    node_bin.mkdir()
    (node_bin / "node").symlink_to(shutil.which("node"))
    env = {**os.environ, "PATH": str(node_bin), "PYTHONPATH": "/nonexistent"}
    cli = base / "node_modules/.bin/jev-context"
    result = subprocess.run(
        [str(cli), "doctor"], env=env, capture_output=True, text=True, check=True
    )
    doctor = json.loads(result.stdout)
    assert doctor["version"] == version and doctor["tree_sitter"] and doctor["ripgrep"], doctor
    contract = base / "contract.json"
    contract.write_text(json.dumps({"mode": "passthrough"}))
    fixture = base / "code"
    fixture.mkdir()
    (fixture / "example.py").write_text('def example():\n    return "needle"\n')
    result = subprocess.run(
        [
            str(cli),
            "code-search",
            "needle",
            "--root",
            str(fixture),
            "--task",
            "Find needle",
            "--analysis",
            str(contract),
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    # Passthrough collects source without claiming a semantic decision.
    assert result.returncode in (0, 2), result.stderr
    packet = json.loads(result.stdout)
    assert packet["ok"] and packet["telemetry"]["requests"] == 0, packet
    assert "example" in result.stdout, result.stdout
    print(
        json.dumps(
            {
                "npm_install": True,
                "system_python_on_path": False,
                "system_rg_on_path": False,
                "doctor": doctor,
                "code_search": True,
            }
        )
    )
