import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jev_context import analysis as analysis
from jev_context import cli as cli


class ContextTests(unittest.TestCase):
    def test_exact_recovery_including_unicode_and_newlines(self):
        text = "中文\n" * 4000
        records = cli.normalize([{"id": "x", "text": text}])
        parts = list(cli.chunks(records))
        self.assertEqual("".join(p["text"] for p in parts), text)
        for p in parts:
            self.assertEqual(p["text"], text[p["start"] : p["end"]])

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError):
            cli.normalize([{"id": "a", "text": "x"}, {"id": "a", "text": "y"}])

    def test_budget_ranking_and_failure_preserved(self):
        parts = list(
            cli.chunks(
                cli.normalize([{"text": "unrelated"}, {"text": "evidence"}, {"text": "unknown"}])
            )
        )
        labels = dict(zip([p["id"] for p in parts], ["OTHER", "RELEVANT", "UNAVAILABLE"]))
        judgments = {
            p["id"]: {
                "status": "UNAVAILABLE" if labels[p["id"]] == "UNAVAILABLE" else "OK",
                "answers": {}
                if labels[p["id"]] == "UNAVAILABLE"
                else {"relevance": {"type": "choice", "choice": labels[p["id"]]}},
            }
            for p in parts
        }
        shown = analysis.select(parts, judgments, analysis.DEFAULT, 11)
        self.assertEqual(shown[0]["text"], "evidence")
        self.assertEqual(shown[1]["status"], "UNAVAILABLE")
        self.assertEqual(shown[1]["text"], "unk")
        self.assertTrue(shown[1]["display_truncated"])

    def test_archive_private_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "archive.json"
            payload = {"records": [{"text": "original"}]}
            cli.save_archive(payload, path)
            if os.name == "posix":  # Windows has no Unix mode bits.
                self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                cli.save_archive({}, path)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), payload)

    def test_search_real_lines_and_scope_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.txt"
            path.write_text("before\nneedle\nafter\nextra\n", encoding="utf-8", newline="\n")
            records, scope = cli.collect_search(directory, "needle", 10)
            self.assertEqual(records[0]["line"], 1)
            self.assertEqual(records[0]["end_line"], 4)
            self.assertIn("needle\n", records[0]["text"])
            self.assertFalse(scope["candidate_limit_reached"])
            records, scope = cli.collect_search(directory, "needle", 1)
            self.assertTrue(scope["candidate_limit_reached"])

    def test_bad_regex_is_not_empty_success(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                cli.collect_search(directory, "[", 10)

    def test_empty_input_no_network(self):
        labels, telemetry = analysis.evaluate([], "task", 1)
        self.assertEqual(labels, {})
        self.assertEqual(telemetry["network_questions"], 0)

    def test_batch_failure_and_no_cache(self):
        parts = list(cli.chunks(cli.normalize([{"text": "one"}, {"text": "two"}])))
        with patch(
            "jev_context.pool.run",
            return_value={
                "ok": False,
                "results": [{"id": "0", "ok": False}],
                "usage_complete": False,
            },
        ) as run:
            labels, telemetry = analysis.evaluate(parts, "task", 2)
            self.assertEqual({r["status"] for r in labels.values()}, {"UNAVAILABLE"})
            self.assertIsNone(run.call_args.kwargs["cache"])
            request = run.call_args.args[0][0]["request"]
            self.assertEqual(len(request["questions"]), 2)
            self.assertEqual(
                request["questions"]["p1q0"]["instructions"]["target_record"]["text"], "two"
            )
            self.assertEqual(
                request["questions"]["p1q0"]["instructions"]["target_record"]["text"], "two"
            )
            self.assertFalse(telemetry["usage_complete"])


if __name__ == "__main__":
    unittest.main()
