import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jev_context import tools as s


class SemanticTools(unittest.TestCase):
    def test_python_function_boundary_and_decorator(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.py"
            p.write_text(
                "@decorate\ndef write_state(x):\n    # needle\n    return x\n\ndef other():\n    return 2\n"
            )
            rows, meta = s.collect_code(d, "needle")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["symbol"], "write_state")
            self.assertEqual(rows[0]["line"], 1)
            self.assertEqual(rows[0]["end_line"], 4)
            self.assertNotIn("def other", rows[0]["text"])

    def test_javascript_method_braces_in_strings(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.js"
            p.write_text(
                'class Store {\n save(x) {\n const text = "} needle {";\n return x;\n }\n other() { return 2; }\n}\n'
            )
            rows, _ = s.collect_code(d, "needle")
            self.assertEqual(rows[0]["symbol"], "Store.save")
            self.assertEqual(rows[0]["end_line"], 5)
            self.assertNotIn("other()", rows[0]["text"])

    def test_contained_symbols_do_not_duplicate_full_parent_context(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.py"
            p.write_text(
                'def outer():\n    def inner():\n        return "needle"\n    return inner() # needle\n'
            )
            rows, _ = s.collect_code(d, "needle")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["symbol"], "outer")
            self.assertIn("def inner", rows[0]["text"])
            self.assertEqual(rows[0]["nested_symbols"][0]["symbol"], "outer.inner")

    def test_typescript_type_assertion_parses_as_symbol(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.ts"
            p.write_text(
                "function decode(x: unknown) {\n const needle = <string>x;\n return needle;\n}\n"
            )
            rows, _ = s.collect_code(d, "needle")
            self.assertEqual(rows[0]["symbol"], "decode")
            self.assertNotIn("fetch_error", rows[0])

    def test_search_limit_never_claims_exhaustive(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.py"
            p.write_text('def a():\n return "needle"\ndef b():\n return "needle"\n')
            rows, meta = s.collect_code(d, "needle", limit=1)
            self.assertTrue(meta["candidate_limit_reached"])

    def test_parser_unavailable_retains_reviewable_source(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.js"
            p.write_text('function f() { return "needle"; }')
            with patch("jev_context.symbols.parse_symbols", side_effect=ImportError()):
                rows, _ = s.collect_code(d, "needle")
            self.assertEqual(rows[0]["fetch_error"], "parser_unavailable")
            self.assertIn("needle", rows[0]["text"])

    def test_code_revision_change_is_not_returned_as_match(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.py"
            p.write_text('def f():\n return "needle"\n')

            def analysis(records, *args):
                p.write_text('def f():\n return "changed"\n')
                rid = records[0]["id"]
                return {
                    "ok": True,
                    "complete": True,
                    "selected_ids": [rid],
                    "review_ids": [],
                    "excerpts": [{"source_id": rid, "decision": "MATCH"}],
                    "receipt": "fixture",
                }

            output = io.StringIO()
            with (
                patch("jev_context.tools.analyze_records", side_effect=analysis),
                contextlib.redirect_stdout(output),
            ):
                code = s.main(["code-search", "needle", "--root", d, "--task", "Find the function"])
            result = json.loads(output.getvalue())
            self.assertEqual(code, 2)
            self.assertFalse(result["complete"])
            self.assertEqual(result["selected_ids"], [])
            self.assertEqual(result["excerpts"][0]["decision"], "REVIEW")

    def test_log_grouping_keeps_history_order_and_duplicates(self):
        text = "\n".join(
            json.dumps(r)
            for r in [
                {"request_id": "a", "message": "old error"},
                {"request_id": "b", "message": "DNS failure"},
                {"request_id": "a", "message": "recovered"},
                {"request_id": "a", "message": "recovered"},
            ]
        )
        rows, meta = s.collect_logs(text)
        data = json.loads(rows[0]["text"])
        self.assertEqual(
            [e["event"]["message"] for e in data["events"]], ["old error", "recovered"]
        )
        self.assertEqual(data["events"][1]["occurrences"], 2)
        self.assertEqual(meta["event_count"], 4)

    def test_redaction_metadata_reports_actual_changes(self):
        _, meta = s.collect_logs(json.dumps({"message": "HTTP 200"}))
        self.assertFalse(meta["redacted"])
        self.assertEqual(meta["redacted_events"], 0)

    def test_logs_redact_credentials_before_inference(self):
        text = json.dumps(
            {
                "request_id": "a",
                "authorization": "Bearer secret-value",
                "message": "Authorization: Bearer secret-value",
            }
        )
        rows, _ = s.collect_logs(text)
        self.assertNotIn("secret-value", json.dumps(rows))
        self.assertIn("REDACTED", rows[0]["text"])

    def test_embedded_secret_payload_is_redacted(self):
        message = 'payload={"api_key":"SECRET_PAYLOAD"}; Cookie: session=SECRET_COOKIE'
        rows, _ = s.collect_logs(json.dumps({"message": message}))
        self.assertNotIn("SECRET_PAYLOAD", str(rows))
        self.assertNotIn("SECRET_COOKIE", str(rows))

    def test_invalid_log_line_is_visible_not_dropped(self):
        rows, meta = s.collect_logs("{bad json}\n" + json.dumps({"message": "ok"}))
        self.assertEqual(meta["parse_errors"], 1)
        self.assertTrue(meta["truncated"])
        self.assertEqual(len(rows), 2)

    def test_browser_control_omits_url_credentials_and_input_values(self):
        row = s.safe_control(
            {
                "id": "1",
                "text": "Download",
                "href": "https://user:password@example.invalid/export?token=SECRET#private",
                "value": "PRIVATE_VALUE",
            }
        )
        self.assertEqual(row["href"], "https://example.invalid/export")
        self.assertNotIn("SECRET", json.dumps(row))
        self.assertNotIn("PRIVATE_VALUE", json.dumps(row))

    def test_indistinguishable_controls_require_review(self):
        rows = [
            {
                "id": "1",
                "text": "Export",
                "role": "button",
                "section": "Current",
                "href": None,
                "dom_id": "original",
            },
            {
                "id": "2",
                "text": "Export",
                "role": "button",
                "section": "Current",
                "href": None,
                "dom_id": "copy",
            },
        ]
        self.assertEqual(s.ambiguous_controls(rows, "1"), ["1", "2"])
        rows[1]["section"] = "Archive"
        self.assertEqual(s.ambiguous_controls(rows, "1"), [])

    def test_changed_browser_target_not_returned(self):
        result = {
            "ok": True,
            "complete": True,
            "selected_ids": ["1"],
            "review_ids": [],
            "excerpts": [{"source_id": "1"}],
        }
        guarded = s.apply_guard(result, {"ok": False, "reason": "target_changed"})
        self.assertFalse(guarded["complete"])
        self.assertEqual(guarded["selected_ids"], [])
        self.assertEqual(guarded["review_ids"], ["1"])
        self.assertFalse(guarded["executed"])


if __name__ == "__main__":
    unittest.main()
