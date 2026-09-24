"""Install actual tarballs and run without any system Python/ripgrep on PATH."""

import json
import os
import platform
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

root = Path(__file__).resolve().parents[1]
package = json.loads((root / "package.json").read_text(encoding="utf-8"))
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
            str(root / f"dist/apixly-jev-filter-{version}.tgz"),
            str(root / f"dist/apixly-jev-filter-{os_name}-{arch}-{version}.tgz"),
        ],
        check=True,
    )
    node_bin = base / "only-node"
    node_bin.mkdir()
    (node_bin / "node").symlink_to(shutil.which("node"))
    env = {
        **os.environ,
        "PATH": str(node_bin),
        "PYTHONPATH": "/nonexistent",
        "JEV_STATS_DIR": str(base / "stats"),
    }
    cli = base / "node_modules/.bin/jev-filter"
    result = subprocess.run(
        [str(cli), "doctor"], env=env, capture_output=True, text=True, check=True
    )
    doctor = json.loads(result.stdout)
    assert doctor["version"] == version and doctor["tree_sitter"] and doctor["ripgrep"], doctor
    subprocess.run(
        [
            str(cli),
            "stats",
            "configure",
            "--model",
            "fixture",
            "--counter",
            "bytes",
            "--input-rate",
            "1",
        ],
        env=env,
        capture_output=True,
        check=True,
    )
    contract = base / "contract.json"
    contract.write_text(json.dumps({"mode": "passthrough"}), encoding="utf-8")
    fixture = base / "code"
    fixture.mkdir()
    (fixture / "example.py").write_text('def example():\n    return "needle"\n', encoding="utf-8")
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
    telemetry = subprocess.run(
        [str(cli), "stats", "report"], env=env, capture_output=True, text=True, check=True
    )
    assert json.loads(telemetry.stdout)["summary"]["runs"] == 1
    dashboard = base / "dashboard.html"
    subprocess.run(
        [str(cli), "stats", "dashboard", "--html", str(dashboard)],
        env=env,
        capture_output=True,
        check=True,
    )
    assert "__DATA__" not in dashboard.read_text(
        encoding="utf-8"
    ) and "JEV FILTER" in dashboard.read_text(encoding="utf-8")
    # Repeated default launches must both return usable, distinct loopback URLs.
    servers = []
    try:
        urls = []
        for _ in range(2):
            process = subprocess.Popen(
                [str(cli), "stats", "dashboard", "--no-open"],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            servers.append(process)
            urls.append(json.loads(process.stdout.readline())["dashboard"])
        assert urlsplit(urls[0]).port != urlsplit(urls[1]).port
        for url in urls:
            with urllib.request.urlopen(url, timeout=10) as response:
                assert response.status == 200
    finally:
        for process in servers:
            process.terminate()
            process.communicate(timeout=10)
    print(
        json.dumps(
            {
                "npm_install": True,
                "system_python_on_path": False,
                "system_rg_on_path": False,
                "doctor": doctor,
                "code_search": True,
                "repeated_dashboard_start": True,
            }
        )
    )
