import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jev_context import analysis as a
from jev_context.command import collect_command


class CommandTests(unittest.TestCase):
    def test_literal_argv_no_shell_expansion(self):
        records, meta = collect_command(
            [sys.executable, "-c", "import sys; print(sys.argv[1])", "$(touch /tmp/not-executed)"]
        )
        self.assertEqual(records[0]["text"].strip(), "$(touch /tmp/not-executed)")
        self.assertTrue(meta["ok"])

    def test_failure_keeps_stderr_exit_and_partial_output(self):
        records, meta = collect_command(
            [
                sys.executable,
                "-c",
                'import sys; print("partial"); print("failed",file=sys.stderr);sys.exit(7)',
            ]
        )
        self.assertEqual(meta["exit_code"], 7)
        self.assertFalse(meta["ok"])
        self.assertIn("failed", meta["stderr"])
        self.assertIn("partial", records[0]["text"])

    def test_timeout_and_output_cap(self):
        _, meta = collect_command(
            [sys.executable, "-c", "import time; time.sleep(10)"], timeout=0.1
        )
        self.assertEqual(meta["stop_reason"], "timeout")
        records, meta = collect_command([sys.executable, "-c", 'print("x"*100000)'], max_bytes=100)
        self.assertEqual(meta["stop_reason"], "output_limit")
        self.assertEqual(meta["captured_bytes"], 100)

    def test_json_and_accepted_exit(self):
        records, meta = collect_command(
            [sys.executable, "-c", 'import sys; print("[]");sys.exit(1)'],
            split="json",
            accept_exit=[0, 1],
        )
        self.assertEqual(records, [])
        self.assertTrue(meta["ok"])
        _, meta = collect_command([sys.executable, "-c", 'print("oops")'], split="json")
        self.assertFalse(meta["ok"])

    def test_invalid_record_schema_keeps_command_output(self):
        records, meta = collect_command(
            [sys.executable, "-c", 'import json; print(json.dumps(["not a record"]))'], split="json"
        )
        self.assertFalse(meta["ok"])
        self.assertIn("parse_error", meta)
        self.assertIn("not a record", records[0]["text"])

    def test_cli_rejects_bad_spec_before_executing(self):
        with tempfile.TemporaryDirectory() as d:
            marker = Path(d) / "marker"
            spec = Path(d) / "bad.json"
            spec.write_text('{"questions":{}}')
            cli = "-m"
            p = subprocess.run(
                [
                    sys.executable,
                    cli,
                    "jev_context",
                    "exec",
                    "--task",
                    "task",
                    "--analysis",
                    str(spec),
                    "--",
                    sys.executable,
                    "-c",
                    f'open({str(marker)!r}, "w").write("x")',
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(p.returncode, 0)
            self.assertFalse(marker.exists())

    def test_cli_command_failure_runs_once_and_skips_inference(self):
        with tempfile.TemporaryDirectory() as d:
            marker = Path(d) / "marker"
            cli = "-m"
            p = subprocess.run(
                [
                    sys.executable,
                    cli,
                    "jev_context",
                    "exec",
                    "--task",
                    "task",
                    "--",
                    sys.executable,
                    "-c",
                    f'import sys;open({str(marker)!r}, "a").write("x");print("partial");sys.exit(7)',
                ],
                capture_output=True,
                text=True,
            )
            output = json.loads(p.stdout)
            self.assertEqual(marker.read_text(), "x")
            self.assertEqual(p.returncode, 2)
            self.assertEqual(output["collection"]["exit_code"], 7)
            self.assertEqual(output["telemetry"]["network_questions"], 0)
            self.assertEqual(output["excerpts"][0]["status"], "NOT_EVALUATED")
            Path(output["archive"]).unlink()


class AnalysisTests(unittest.TestCase):
    def spec(self):
        return a.validate(
            {
                "questions": {
                    "severity": {
                        "type": "score",
                        "instructions": "How severe?",
                        "criteria": ["none", "high"],
                    }
                },
                "filter": {"question": "severity", "min": 0.5},
                "order": {"question": "severity", "descending": True},
                "fields": ["source_id", "answers"],
                "format": "jsonl",
            }
        )

    def test_score_filter_and_unknown_retained(self):
        spec = self.spec()
        parts = [
            {"id": str(i), "source_id": str(i), "text": "data", "start": 0, "end": 4}
            for i in range(3)
        ]
        judgments = {
            "0": {"status": "OK", "answers": {"severity": {"type": "score", "score": 0.2}}},
            "1": {"status": "OK", "answers": {"severity": {"type": "score", "score": 0.8}}},
        }
        rows = a.select(parts, judgments, spec, 100)
        self.assertEqual([r["id"] for r in rows], ["1", "2"])
        rendered = [
            json.loads(s) for s in a.render({"excerpts": rows, "archive": "x"}, spec).splitlines()
        ]
        self.assertEqual(set(rendered[1]), {"source_id", "answers", "decision"})
        self.assertEqual(rendered[0]["meta"]["archive"], "x")

    def test_custom_nested_output_schema(self):
        spec = self.spec()
        spec["format"] = "json"
        spec["output"] = {
            "record": "source_id",
            "rating": "answers.severity.score",
            "evidence": {"quote": "text", "url": "source.url"},
        }
        spec = a.validate(spec)
        rendered = json.loads(
            a.render(
                {
                    "excerpts": [
                        {
                            "source_id": "r",
                            "text": "verbatim",
                            "answers": {"severity": {"type": "score", "score": 0.8}},
                        }
                    ]
                },
                spec,
            )
        )
        self.assertEqual(
            rendered["excerpts"][0],
            {"record": "r", "rating": 0.8, "evidence": {"quote": "verbatim", "url": None}},
        )

    def test_bad_spec_rejected_before_command(self):
        with self.assertRaises(ValueError):
            a.validate(
                {
                    "questions": a.DEFAULT["questions"],
                    "filter": {"question": "missing", "in": ["yes"]},
                }
            )
        with self.assertRaises(ValueError):
            a.validate({"questions": a.DEFAULT["questions"], "fields": ["__dict__"]})

    def test_custom_question_and_context_transport(self):
        parts = [{"id": "p0", "text": "test", "source": {"line": 1}}]
        spec = self.spec()
        spec["context"] = {"scope": "custom"}
        with patch(
            "jev_context.pool.run",
            return_value={
                "ok": True,
                "results": [
                    {"id": "0", "ok": True, "answers": {"p0q0": {"type": "score", "score": 0.8}}}
                ],
            },
        ) as run:
            judgments, _ = a.evaluate(parts, "task", spec=spec)
            request = run.call_args.args[0][0]["request"]
            self.assertEqual(request["state"]["context"], {"scope": "custom"})
            self.assertEqual(
                request["questions"]["p0q0"]["instructions"]["target_record"]["text"], "test"
            )
            self.assertIsNone(run.call_args.kwargs["cache"])
            self.assertEqual(judgments["p0"]["answers"]["severity"]["score"], 0.8)


if __name__ == "__main__":
    unittest.main()
