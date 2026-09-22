"""Export only typed decisions from one explicitly supplied evaluation directory."""

import argparse
import json
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--private-dir", required=True)
p.add_argument("--report", required=True)
p.add_argument("--output", required=True)
a = p.parse_args()
private = Path(a.private_dir).resolve(strict=True)
report = json.loads(Path(a.report).read_text())
rows = []
for row in report["rows"]:
    name = f"{row['model']}-{row['case']}-{row['arm']}-{row['repeat']}"
    answer = None
    judgments = None
    for line in (private / (name + ".events.jsonl")).read_text().splitlines():
        event = json.loads(line)
        item = event.get("item", {})
        if event.get("type") != "item.completed":
            continue
        if item.get("type") == "agent_message":
            try:
                answer = json.loads(item["text"])
            except ValueError:
                pass
        if row["arm"] == "filtered" and item.get("type") == "command_execution":
            try:
                packet = json.loads(item.get("aggregated_output", ""))
            except ValueError:
                continue
            receipt = packet.get("analysis_receipt") or packet.get("receipt")
            if receipt:
                record = json.loads(Path(receipt).read_text())
                judgments = {
                    key: {
                        field: value
                        for field, value in value.items()
                        if field in ("status", "answers", "decision")
                    }
                    for key, value in record.get("judgments", {}).items()
                }
    rows.append(
        {
            **{k: row[k] for k in ("model", "case", "arm", "repeat")},
            "main_answer": answer,
            "jev_judgments": judgments,
        }
    )
output = {
    "scope": "Synthetic test decisions only. Provider request state, local paths, agent configuration and raw event streams are excluded.",
    "rows": rows,
}
encoded = json.dumps(output, ensure_ascii=False, indent=2) + "\n"
if "/Users/" in encoded or "/home/" in encoded:
    raise ValueError("Unexpected local path in selected fields")
Path(a.output).write_text(encoded)
print(
    f"Exported {len(rows)} answer records and {sum(r['jev_judgments'] is not None for r in rows)} Jev judgment sets."
)
