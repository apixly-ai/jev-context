import json
import unittest

from jev_context import batch as t


def item(i, state=None, questions=None):
    return {
        "id": str(i),
        "request": {
            "model": "jev-1.13.0",
            "state": state or {"signal": f"observed {i}"},
            "questions": questions
            or {
                "label": {
                    "type": "choice",
                    "instructions": "Classify this state.",
                    "criteria": {"YES": "yes", "NO": "no"},
                }
            },
        },
    }


class TypedBatch(unittest.TestCase):
    def test_homogeneous_states_pack_but_never_share_record_text(self):
        items = [item(i) for i in range(20)]
        plan = t.plan(items)
        self.assertLess(len(plan["items"]), 20)
        request = plan["items"][0]["request"]
        self.assertNotIn("observed 0", json.dumps(request["state"]))
        for question in request["questions"].values():
            text = question["instructions"]["target_record"]["text"]
            self.assertEqual(len(json.loads(text)), 1)

    def test_different_questions_do_not_mix(self):
        other = {"route": {"type": "noul", "instructions": "Is this a route?"}}
        plan = t.plan([item("a"), item("b", questions=other)])
        self.assertEqual(len(plan["items"]), 2)
        self.assertEqual(plan["items"][0]["request"], item("a")["request"])

    def test_results_keep_original_ids_and_question_names_no_raw_state(self):
        def runner(items, **kwargs):
            return {
                "ok": True,
                "results": [
                    {
                        "id": x["id"],
                        "ok": True,
                        "model": "jev-1.13.0",
                        "answers": {
                            k: {"type": "choice", "choice": "YES"}
                            for k in x["request"]["questions"]
                        },
                    }
                    for x in items
                ],
                "usage": {"input_tokens": 42, "output_tokens": 2},
                "usage_complete": True,
            }

        out = t.run([item("a", {"secret_fixture": "UNIQUE_RAW_BODY"}), item("b")], runner=runner)
        self.assertEqual([r["id"] for r in out["results"]], ["a", "b"])
        self.assertEqual(set(out["results"][0]["answers"]), {"label"})
        self.assertNotIn("UNIQUE_RAW_BODY", json.dumps(out))
        self.assertEqual(out["usage"]["input_tokens"], 42)
        self.assertFalse(out["cache_enabled"])

    def test_partial_failure_preserves_all_original_records(self):
        def runner(items, **kwargs):
            return {
                "ok": False,
                "results": [
                    {"id": i["id"], "ok": False, "error_type": "RuntimeError"} for i in items
                ],
                "usage": {"input_tokens": 0, "output_tokens": 0},
                "usage_complete": False,
            }

        out = t.run([item("a"), item("b")], runner=runner)
        self.assertEqual(len(out["results"]), 2)
        self.assertTrue(all(not r["ok"] for r in out["results"]))
        self.assertFalse(out["usage_complete"])

    def test_duplicate_ids_and_cache_rejected(self):
        with self.assertRaises(ValueError):
            t.run([item("a"), item("a")])
        with self.assertRaises(ValueError):
            t.run([item("a")], cache=object())

    def test_large_single_request_preserved_instead_of_silent_truncation(self):
        original = item("a", {"source": "x" * 60000})
        plan = t.plan([original])
        self.assertEqual(plan["items"][0]["request"], original["request"])

    def test_valid_legacy_contract_outside_packer_limits_is_preserved(self):
        questions = {
            str(i): {"type": "noul", "instructions": "Is this observed?"} for i in range(17)
        }
        records = [item("a", questions=questions), item("b", questions=questions)]
        planned = t.plan(records)
        self.assertEqual([x["request"] for x in planned["items"]], [x["request"] for x in records])

    def test_ui_and_conversations_preserve_independent_contracts(self):
        ui = item(
            "ui",
            {"components": [{"id": "button", "label": "Open"}]},
            {
                "open": {
                    "type": "choice",
                    "instructions": "Choose a component.",
                    "criteria": {"button": "Open", "NONE": "none"},
                }
            },
        )
        plan = t.plan(
            [
                ui,
                item("customer1", {"messages": [{"direction": "in", "text": "One"}]}),
                item("customer2", {"messages": [{"direction": "in", "text": "Two"}]}),
            ]
        )
        self.assertEqual(plan["items"][0]["request"], ui["request"])
        conversations = plan["items"][1]["request"]
        self.assertNotIn("components", json.dumps(conversations))


if __name__ == "__main__":
    unittest.main()
