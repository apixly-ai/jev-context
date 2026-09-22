"""Deterministic public fixtures for paired whole-operation evaluation."""

import json
from pathlib import Path


def build(base):
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True)
    code = base / "code"
    code.mkdir(exist_ok=True)
    chunks = ["import json\nimport os\nfrom pathlib import Path\n\n"]
    for i in range(60):
        if i == 19:
            text = 'def persist_session(destination, state):\n    """Persist session state through a temporary file and replacement."""\n    temporary = str(destination) + ".tmp"\n    with open(temporary, "w") as stream:\n        json.dump(state, stream)\n    os.replace(temporary, destination)\n    return destination\n\n'
        elif i == 43:
            text = 'def persist_session_unsafely(destination, state):\n    """Persist session state directly; a partial write can corrupt it."""\n    with open(destination, "w") as stream:\n        json.dump(state, stream)\n    return destination\n\n'
        else:
            text = f'def session_presentation_{i}(state):\n    """Format session details for display without persisting anything."""\n    label = "Session panel {i}"\n    fields = sorted(state.keys())\n    return {{"label": label, "fields": fields, "preview_only": True}}\n\n'
        chunks.append(text)
    (code / "session_store.py").write_text("".join(chunks))
    logs = []
    for i in range(60):
        rid = f"req-{i:03}"
        logs.append(
            {"request_id": rid, "timestamp": "2026-09-22T10:00:00Z", "message": "Request started."}
        )
        if i in (13, 47):
            logs.append(
                {
                    "request_id": rid,
                    "timestamp": "2026-09-22T10:00:01Z",
                    "message": "Current attempt failed at TLS certificate verification before HTTP; no response headers arrived.",
                }
            )
        elif i == 31:
            logs.append(
                {
                    "request_id": rid,
                    "timestamp": "2026-09-22T10:00:01Z",
                    "message": "HTTP 200 response headers arrived; body was empty.",
                }
            )
        else:
            logs.append(
                {
                    "request_id": rid,
                    "timestamp": "2026-09-22T10:00:01Z",
                    "message": "Earlier attempt had a connection timeout.",
                }
            )
            logs.append(
                {
                    "request_id": rid,
                    "timestamp": "2026-09-22T10:00:02Z",
                    "message": "After recovery, the CURRENT attempt received HTTP 200 and a valid body.",
                }
            )
    (base / "events.jsonl").write_text("\n".join(json.dumps(r) for r in logs) + "\n")
    html = """<!doctype html><meta charset="utf-8"><style>body{font:12px sans-serif;margin:10px}section{display:grid;grid-template-columns:repeat(10,90px);gap:3px}h2{grid-column:1/-1;margin:5px}button{font:10px sans-serif;height:48px;width:90px}</style>"""
    for group in ["Current project", "All projects"]:
        html += f'<section aria-label="{group}"><h2>{group}</h2>'
        for i in range(30):
            if i == 12:
                text = "Download audit records as JSON"
                identifier = "target" if group == "Current project" else "other-scope"
                disabled = ""
            elif i == 20:
                text = "Download audit records as JSON"
                identifier = "disabled-" + group.replace(" ", "")
                disabled = " disabled"
            else:
                text = f"Download visual theme {i} as JSON"
                identifier = group.replace(" ", "") + str(i)
                disabled = ""
            html += f'<button id="{identifier}"{disabled}>{text}</button>'
        html += "</section>"
    (base / "page.html").write_text(html)
    code_spec = {
        "mode": "filter",
        "requirements": [
            {
                "id": "persists",
                "statement": "The function writes session state to a temporary file and then replaces the destination file.",
                "expected": True,
            }
        ],
        "fields": ["source_id", "text", "source", "answers"],
    }
    log_spec = {
        "mode": "filter",
        "requirements": [
            {
                "id": "connection_failure",
                "statement": "The CURRENT attempt fails during DNS, TCP or TLS establishment.",
                "expected": True,
            },
            {
                "id": "http_response",
                "statement": "The CURRENT attempt received HTTP response headers.",
                "expected": False,
            },
        ],
        "fields": ["source_id", "answers", "source"],
    }
    (base / "code-analysis.json").write_text(json.dumps(code_spec))
    (base / "triage-analysis.json").write_text(json.dumps(log_spec))
    command_records = []
    for i in range(80):
        if i in (11, 52):
            text = "Current release has a confirmed authentication bypass. It is unresolved and blocks release."
        elif i == 23:
            text = "A past release had an authentication bypass, but the current release contains the verified fix."
        elif i == 64:
            text = "Security documentation lists authentication bypass as an example. No current vulnerability was observed."
        else:
            text = f"Review item {i}: documentation formatting improvement. Current security checks passed; no release blocker."
        command_records.append({"id": f"item-{i:03}", "text": text})
    (base / "command-records.json").write_text(json.dumps(command_records))
    (base / "command-analysis.json").write_text(
        json.dumps(
            {
                "mode": "filter",
                "requirements": [
                    {
                        "id": "current",
                        "statement": "The current release has a confirmed, unresolved authentication bypass that blocks release.",
                        "expected": True,
                    }
                ],
                "fields": ["source_id", "answers", "source"],
            }
        )
    )
    (base / "cases.json").write_text(
        json.dumps(
            [
                {
                    "name": "code-search",
                    "task": "Find functions that persist session state by writing a temporary file and replacing the destination. Exclude presentation-only functions and direct unsafe writes.",
                },
                {
                    "name": "locate",
                    "task": "Choose the enabled control that downloads audit records as JSON, scoped EXACTLY to the current project. Exclude visual-theme downloads and all-project exports.",
                },
                {
                    "name": "triage",
                    "task": "Select requests whose CURRENT attempt fails during DNS, TCP or TLS establishment before any HTTP response. Exclude recovered history and failures after response headers.",
                },
                {
                    "name": "exec",
                    "task": "Select current confirmed and unresolved authentication-bypass release blockers. Exclude past resolved defects and documentation-only examples.",
                },
            ],
            indent=2,
        )
    )


if __name__ == "__main__":
    import sys

    build(sys.argv[1])
