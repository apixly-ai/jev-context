import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jev_context import analysis as a
from jev_context import cli as cli


def parts(n=60):
    return [
        {
            "id": f"p{i}",
            "source_id": f"s{i}",
            "text": f"Candidate {i} offers a different function.",
            "source": {"ref": f"e{i}", "section": "current project"},
            "start": 0,
            "end": 40,
        }
        for i in range(n)
    ]


class PlanningTests(unittest.TestCase):
    def test_question_owns_exact_record_not_an_index_lookup(self):
        records = parts(128)
        records[116]["text"] = "HTTP 200 received; body empty."
        planned = a.plan(records, "Select network establishment failures", None)
        # The question itself contains its evidence; it cannot bind to another numbered record.
        q = next(
            item["request"]["questions"][key]
            for item in planned["items"]
            for key, pid, _ in planned["routes"][item["id"]]
            if pid == "p116"
        )
        self.assertEqual(
            q["instructions"]["target_record"]["text"], "HTTP 200 received; body empty."
        )
        self.assertNotIn("records", planned["items"][0]["request"]["state"])

    def test_atomic_expected_values_and_unknown_reduction(self):
        spec = a.validate(
            {
                "requirements": [
                    {"id": "failure", "statement": "Current establishment fails", "expected": True},
                    {
                        "id": "response",
                        "statement": "Current HTTP response arrived",
                        "expected": False,
                    },
                ]
            }
        )

        def entry(x, y):
            return {
                "status": "OK",
                "answers": {
                    "failure": {"type": "choice", "choice": x},
                    "response": {"type": "choice", "choice": y},
                },
            }

        self.assertEqual(a.decision(entry("SUPPORTED", "CONTRADICTED"), spec), "MATCH")
        self.assertEqual(a.decision(entry("SUPPORTED", "SUPPORTED"), spec), "EXCLUDE")
        self.assertEqual(a.decision(entry("UNKNOWN", "SUPPORTED"), spec), "EXCLUDE")
        self.assertEqual(a.decision(entry("UNKNOWN", "CONTRADICTED"), spec), "REVIEW")
        plan = a.plan(parts(2), "Task", spec)
        self.assertEqual(len(plan["items"][0]["request"]["questions"]), 4)

    def test_failed_retry_attempts_are_not_underreported(self):
        a.validate(None)
        from jev_context.pool import run

        class Client:
            stats = {"requests": 5, "new_connections": 2, "reused_connections": 3}

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        success = {
            "ok": True,
            "answers": {},
            "usage": {"input_tokens": 20, "output_tokens": 1},
            "usage_complete": False,
            "attempts": 2,
            "unknown_usage_attempts": 1,
        }
        with (
            patch("jev_context.provider.Client", return_value=Client()),
            patch("jev_context.provider.evaluate", side_effect=[success, RuntimeError("failed")]),
        ):
            result = run([{"id": "a", "request": {}}, {"id": "b", "request": {}}], workers=1)
        self.assertEqual(result["unknown_usage_attempts"], 4)
        self.assertFalse(result["usage_complete"])
        self.assertEqual(result["usage"]["input_tokens"], 20)

    def test_concurrency_cap_is_thirty(self):
        from jev_context.pool import worker_count

        self.assertEqual(worker_count(60, "auto"), 30)
        self.assertEqual(worker_count(60, 30), 30)
        self.assertEqual(worker_count(2, 30), 2)
        with self.assertRaises(ValueError):
            worker_count(60, 31)

    def test_choose_is_one_question_over_all_candidates(self):
        plan = a.plan(parts(), "Choose the matching button", {"mode": "choose"})
        self.assertEqual(len(plan["items"]), 1)
        body = plan["items"][0]["request"]
        self.assertEqual(len(body["questions"]), 1)
        self.assertEqual(len(body["questions"]["target"]["criteria"]), 62)
        self.assertIn("NONE", body["questions"]["target"]["criteria"])
        self.assertIn("REVIEW", body["questions"]["target"]["criteria"])

    def test_auto_batch_shares_instructions_and_reduces_requests(self):
        plan = a.plan(parts(), "Find matching candidates", None)
        self.assertLess(len(plan["items"]), 15)
        for item in plan["items"]:
            body = item["request"]
            self.assertLessEqual(len(json.dumps(body, ensure_ascii=False).encode()), 48000)
            self.assertIn("question_instructions", body["state"])

    def test_oversized_choice_requires_narrowing_no_hidden_tournament(self):
        plan = a.plan(parts(254), "Choose one", {"mode": "choose"})
        self.assertEqual(plan["items"], [])
        self.assertEqual(len(plan["deferred"]), 254)

    def test_large_record_not_silently_cut(self):
        records = cli.normalize([{"id": "code", "text": "abc\n" * 10000}])
        p = list(cli.chunks(records))
        self.assertEqual(len(p), 1)
        self.assertEqual(p[0]["text"], records[0]["text"])
        plan = a.plan(p, "Read the whole function", None)
        self.assertEqual(plan["items"], [])
        self.assertEqual(plan["deferred"][p[0]["id"]], "NEEDS_SEGMENTATION")

    def test_search_merges_contiguous_context_lines(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "x.py"
            path.write_text('def function():\n    # needed context\n    return "needle"\n')
            records, _ = cli.collect_search(d, "needle", 100)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["text"], path.read_text())
            self.assertEqual(records[0]["line"], 1)
            self.assertEqual(records[0]["end_line"], 3)

    def test_choose_maps_exact_source_and_none(self):
        a.validate(None)
        for answer, expected in [("c1", "s1"), ("NONE", None)]:
            response = {
                "ok": True,
                "results": [
                    {
                        "id": "choose",
                        "ok": True,
                        "answers": {"target": {"type": "choice", "choice": answer}},
                    }
                ],
                "usage_complete": True,
            }
            with patch("jev_context.pool.run", return_value=response) as run:
                judgments, stats = a.evaluate(parts(3), "Choose one", spec={"mode": "choose"})
                selected = [
                    p["source_id"] for p in parts(3) if judgments[p["id"]]["decision"] == "MATCH"
                ]
                self.assertEqual(selected, [expected] if expected else [])
                self.assertEqual(run.call_args.kwargs["workers"], 1)
                self.assertIsNone(run.call_args.kwargs["cache"])

    def test_failure_review_and_unevaluated_visible_outside_projection(self):
        ps = parts(3)
        js = {
            "p0": {
                "status": "OK",
                "answers": {"relevance": {"type": "choice", "choice": "RELEVANT"}},
            },
            "p1": {
                "status": "OK",
                "answers": {"relevance": {"type": "choice", "choice": "REVIEW"}},
            },
        }
        result = a.summarize(ps, js, a.validate(None))
        self.assertEqual(result["selected_ids"], ["s0"])
        self.assertEqual(result["review_ids"], ["s1", "s2"])
        self.assertFalse(result["complete"])

    def test_multiquestion_keeps_atomic_questions(self):
        spec = {
            "questions": {
                "a": {"type": "noul", "instructions": "Is enabled?"},
                "b": {"type": "noul", "instructions": "Is current?"},
            }
        }
        plan = a.plan(parts(2), "Inspect flags", spec)
        self.assertEqual(len(plan["items"][0]["request"]["questions"]), 4)

    def test_partial_failure_keeps_success_and_bounds_workers(self):
        response = {
            "ok": False,
            "results": [
                {
                    "id": "0",
                    "ok": True,
                    "answers": {"p0q0": {"type": "choice", "choice": "RELEVANT"}},
                },
                {"id": "1", "ok": False},
            ],
            "usage_complete": False,
        }
        spec = dict(a.DEFAULT, batch_size=1)
        with patch("jev_context.pool.run", return_value=response) as run:
            js, stats = a.evaluate(parts(2), "Task", workers=8, spec=spec)
            self.assertEqual(run.call_args.kwargs["workers"], 2)
            self.assertEqual(js["p0"]["status"], "OK")
            self.assertEqual(js["p1"]["status"], "UNAVAILABLE")
            self.assertFalse(stats["usage_complete"])

    def test_compact_result_keeps_decisions_without_full_distributions(self):
        spec = a.validate(None)
        row = {
            "id": "p0",
            "source_id": "s0",
            "text": "quote",
            "status": "OK",
            "decision": "MATCH",
            "answers": {
                "relevance": {
                    "type": "choice",
                    "choice": "RELEVANT",
                    "probabilities": {"RELEVANT": 1},
                }
            },
        }
        text = a.render(
            {"excerpts": [row], "selected_ids": ["s0"], "review_ids": [], "complete": True}, spec
        )
        self.assertIn("MATCH", text)
        self.assertNotIn("probabilities", text)


if __name__ == "__main__":
    unittest.main()
