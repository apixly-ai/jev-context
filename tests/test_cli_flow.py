import json
import sys

from jev_context import analysis, cli, tools


def decisions(parts, *args, **kwargs):
    return (
        {
            p["id"]: {
                "status": "OK",
                "answers": {
                    "relevance": {
                        "type": "choice",
                        "choice": "RELEVANT" if "keep" in p["text"] else "OTHER",
                    }
                },
            }
            for p in parts
        },
        {
            "ok": True,
            "usage": {"input_tokens": 12, "output_tokens": 1},
            "usage_complete": True,
            "requests": 1,
            "workers": 1,
        },
    )


def invoke(monkeypatch, capsys, args):
    monkeypatch.setattr(sys, "argv", ["jev-context", *args])
    code = cli.main()
    return code, json.loads(capsys.readouterr().out)


def test_query_plan_inference_and_original_recovery(tmp_path, monkeypatch, capsys):
    source = tmp_path / "input.json"
    source.write_text(
        json.dumps([{"id": "a", "text": "keep this"}, {"id": "b", "text": "discard this"}]),
        encoding="utf-8",
    )
    code, p = invoke(
        monkeypatch,
        capsys,
        ["query", "--input", str(source), "--task", "Find", "--mode", "filter", "--plan"],
    )
    assert code == 0 and p["requests"] == 1
    monkeypatch.setattr(analysis, "evaluate", decisions)
    code, p = invoke(
        monkeypatch,
        capsys,
        ["query", "--input", str(source), "--task", "Find", "--mode", "filter", "--diagnostics"],
    )
    assert p["selected_ids"] == ["a"] and p["complete"]
    _, original = invoke(monkeypatch, capsys, ["read", p["archive"], "--id", "b"])
    assert original["text"] == "discard this"
    _, listing = invoke(monkeypatch, capsys, ["list", p["archive"]])
    assert len(listing) == 2


def test_small_passthrough_and_exec(tmp_path, monkeypatch, capsys):
    source = tmp_path / "input.json"
    source.write_text('[{"text":"small"}]', encoding="utf-8")
    code, p = invoke(monkeypatch, capsys, ["query", "--input", str(source), "--task", "Read"])
    assert code == 0 and p["mode"] == "passthrough"
    code, p = invoke(
        monkeypatch,
        capsys,
        ["exec", "--task", "Read", "--", sys.executable, "-c", 'print("small")'],
    )
    assert code == 0 and p["collection"]["exit_code"] == 0


def test_search_integration(tmp_path, monkeypatch, capsys):
    (tmp_path / "x.py").write_text("keep = 1\n", encoding="utf-8")
    monkeypatch.setattr(analysis, "evaluate", decisions)
    code, p = invoke(
        monkeypatch,
        capsys,
        ["search", "keep", "--root", str(tmp_path), "--task", "Find", "--mode", "filter"],
    )
    assert code == 0 and p["selected_ids"]


def test_batch_and_safe_entrypoint(monkeypatch, capsys, tmp_path):
    from jev_context import batch

    p = tmp_path / "batch.json"
    p.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(batch, "run", lambda *a, **k: {"ok": True, "results": []})
    code, result = invoke(monkeypatch, capsys, ["batch", "--input", str(p)])
    assert code == 0 and result["ok"]
    monkeypatch.setattr(cli, "main", lambda: (_ for _ in ()).throw(ValueError("PRIVATE_DATA")))
    assert cli.entrypoint() == 1
    assert "PRIVATE_DATA" not in capsys.readouterr().err


def test_tools_triage_success_and_invalid_input(tmp_path, monkeypatch, capsys):
    p = tmp_path / "logs.jsonl"
    p.write_text('{"request_id":"a","message":"keep this"}\n', encoding="utf-8")
    monkeypatch.setattr(analysis, "evaluate", decisions)
    assert tools.main(["triage", "--input", str(p), "--task", "Find"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["selected_ids"] == ["correlated:a"]
    assert "keep this" not in json.dumps(result["excerpts"])


def test_locator_collect_decide_guard(monkeypatch, capsys):
    def browser(*args, **kwargs):
        if len(args) > 3:
            return {"ok": True, "selector": "#safe", "dom_id": "safe"}
        return {
            "records": [{"id": "a", "text": "Export", "enabled": True, "section": "current"}],
            "token": "t",
            "truncated": False,
        }

    monkeypatch.setattr(tools, "browser_call", browser)
    monkeypatch.setattr(
        analysis,
        "evaluate",
        lambda *a, **k: (
            {"pa:0": {"status": "OK", "decision": "MATCH", "answers": {}}},
            {"ok": True, "usage": {}, "usage_complete": True, "requests": 1},
        ),
    )
    assert (
        tools.main(
            [
                "locate",
                "--session",
                "test",
                "--tab",
                "id",
                "--origin",
                "https://example.invalid",
                "--task",
                "Find export",
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert result["target_guard"]["selector"] == "#safe"
    assert not result["executed"]
