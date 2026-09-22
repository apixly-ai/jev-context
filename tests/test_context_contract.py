import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jev_context import analysis as a


def part(i, source=None):
    return {"id": str(i), "source_id": str(i), "text": "Export report", "source": source or {}}


class ContextContract(unittest.TestCase):
    def test_missing_shared_context_does_not_call_model(self):
        spec = {"mode": "choose", "required_context": ["scope.project"], "context": {}}
        with patch("jev_context.pool.run", side_effect=AssertionError("must not infer")):
            judgments, stats = a.evaluate([part(1)], "Choose export", spec=spec)
        self.assertEqual(judgments["1"]["status"], "NEEDS_CONTEXT")
        self.assertEqual(stats["missing_context"], ["scope.project"])
        self.assertEqual(stats["requests"], 0)

    def test_cli_missing_context_prevents_collector_execution(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            spec = d / "spec.json"
            marker = d / "marker"
            spec.write_text(json.dumps({"required_context": ["scope.project"]}))
            command = [
                sys.executable,
                "-m",
                "jev_context",
                "exec",
                "--task",
                "Find target",
                "--analysis",
                str(spec),
                "--",
                sys.executable,
                "-c",
                f'open({str(marker)!r},"w").write("ran")',
            ]
            result = subprocess.run(command, capture_output=True, text=True)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "NEEDS_CONTEXT")
            self.assertEqual(payload["telemetry"]["requests"], 0)
            self.assertFalse(marker.exists())

    def test_required_false_and_zero_values_are_present(self):
        spec = {
            "mode": "choose",
            "required_context": ["allow_delete", "budget"],
            "context": {"allow_delete": False, "budget": 0},
        }
        self.assertEqual(len(a.plan([part(1)], "Choose export", spec)["items"]), 1)

    def test_missing_one_record_context_does_not_hide_other_candidates(self):
        spec = {"mode": "choose", "required_record_fields": ["source.project"]}
        plan = a.plan([part(1, {"project": "A"}), part(2)], "Choose export", spec)
        self.assertEqual(plan["items"], [])
        self.assertEqual(set(plan["deferred"]), {"1", "2"})

    def test_filter_evaluates_only_records_with_required_context(self):
        spec = {**a.DEFAULT, "required_record_fields": ["source.conversation_context"]}
        plan = a.plan(
            [part(1, {"conversation_context": "trial offered"}), part(2)], "Classify message", spec
        )
        self.assertEqual(plan["deferred"], {"2": "NEEDS_CONTEXT"})
        self.assertEqual(len(plan["items"]), 1)

    def test_missing_record_details_use_original_source_ids(self):
        record = {"id": "internal-part", "source_id": "customer-a", "text": "Yes", "source": {}}
        _, stats = a.evaluate(
            [record],
            "Interpret reply",
            spec={**a.DEFAULT, "required_record_fields": ["source.conversation_context"]},
        )
        self.assertEqual(
            stats["missing_record_fields"], {"customer-a": ["source.conversation_context"]}
        )

    def test_no_records_does_not_hide_missing_required_context(self):
        spec = a.validate({"mode": "choose", "required_context": ["goal.scope"]})
        summary = a.summarize([], {}, spec)
        self.assertFalse(summary["complete"])
        self.assertEqual(summary["missing_context"], ["goal.scope"])


if __name__ == "__main__":
    unittest.main()
