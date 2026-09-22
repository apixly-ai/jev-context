"""Paired source/native CLI benchmark; explicit --live, synthetic records only."""

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", required=True, help="Native or installed npm CLI executable")
    parser.add_argument("--output", required=True)
    parser.add_argument("--live", action="store_true", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        parser.error("Use a new output path; failed runs must be retained")
    native = Path(args.native).resolve(strict=True)
    records = [
        {
            "id": str(i),
            "request": {
                "model": "jev-1.13.0",
                "state": {
                    "signal": "DNS still fails before connection."
                    if i % 2 == 0
                    else "DNS has recovered and requests now succeed."
                },
                "questions": {
                    "label": {
                        "type": "choice",
                        "instructions": "Does the observed signal show an unresolved DNS failure?",
                        "criteria": {
                            "YES": "Unresolved DNS failure",
                            "NO": "Recovered or healthy",
                            "REVIEW": "Insufficient evidence",
                        },
                    }
                },
            },
        }
        for i in range(32)
    ]
    payload = json.dumps(records)
    commands = {"python": [sys.executable, "-I", "-m", "jev_context"], "native": [str(native)]}
    rows = []
    for repeat in range(2):
        for name in ["python", "native"] if repeat == 0 else ["native", "python"]:
            start = time.perf_counter()
            call = subprocess.run(
                [*commands[name], "batch", "--input", "-", "--workers", "30"],
                input=payload,
                text=True,
                capture_output=True,
            )
            row = {
                "arm": name,
                "repeat": repeat,
                "elapsed_ms": round((time.perf_counter() - start) * 1000),
                "exit_code": call.returncode,
                "stdout_chars": len(call.stdout),
            }
            try:
                result = json.loads(call.stdout)
                row.update(
                    exact=result["ok"]
                    and len(result["results"]) == 32
                    and all(
                        r["answers"]["label"]["choice"]
                        == ("YES" if int(r["id"]) % 2 == 0 else "NO")
                        for r in result["results"]
                    ),
                    usage=result["usage"],
                    usage_complete=result["usage_complete"],
                )
            except (ValueError, KeyError, TypeError):
                row.update(exact=False, usage_complete=False)
            rows.append(row)
            print(json.dumps(row), flush=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "kind": "source-versus-distribution",
                "scope": "32 synthetic DNS signals, two alternating-order runs; includes process startup and Jev, excludes installation. No main-agent continuation.",
                "platform": platform.system(),
                "fixture_sha256": hashlib.sha256(payload.encode()).hexdigest(),
                "native_sha256": hashlib.sha256(native.read_bytes()).hexdigest(),
                "cache_enabled": False,
                "model": "jev-1.13.0",
                "rows": rows,
            },
            indent=2,
        )
        + "\n"
    )
    return 0 if all(row["exact"] for row in rows) else 2


if __name__ == "__main__":
    raise SystemExit(main())
