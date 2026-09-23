import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing

import pytest

from jev_context import stats


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("JEV_STATS_DIR", str(tmp_path / "stats"))
    monkeypatch.delenv("JEV_STATS_DISABLED", raising=False)
    stats.configure("test-model", "bytes", 10, 0.042, 0, price_source="test")
    return tmp_path / "stats"


def result(complete=True, usage_complete=True):
    return {
        "ok": True,
        "complete": complete,
        "telemetry": {
            "usage": {"input_tokens": 100, "output_tokens": 10},
            "usage_complete": usage_complete,
        },
    }


def test_ledger_privacy_and_net_arithmetic(home):
    stats.record("query", "SECRET source " * 100, "small output", result())
    data = stats.report()
    row = data["events"][0]
    assert row["saved_tokens"] == row["before_tokens"] - row["after_tokens"]
    assert row["net_usd"] == pytest.approx(row["saved_tokens"] * 10 / 1e6 - 100 * 0.042 / 1e6)
    assert row["method"] == "utf8_bytes_div_4_estimate"
    assert b"SECRET" not in (home / "usage.sqlite3").read_bytes()
    assert "SECRET" not in json.dumps(data)
    assert (home / "usage.sqlite3").stat().st_mode & 0o777 == 0o600


def test_unknown_usage_and_incomplete_are_not_zero_savings(home):
    stats.record("query", "x" * 1000, "x", result(usage_complete=False))
    stats.record("locate", "x" * 1000, "x", result(complete=False))
    data = stats.report()
    assert data["summary"]["net_usd"] is None
    assert data["summary"]["unpriced_runs"] == 1
    assert data["summary"]["incomplete_runs"] == 1
    assert next(r for r in data["events"] if r["status"] == "incomplete")["saved_tokens"] is None


def test_negative_savings_and_batch_not_misrepresented(home):
    stats.record("query", "x", "x" * 500, result())
    stats.record("batch", None, "output", result(), comparable=False)
    rows = stats.report()["events"]
    assert next(r for r in rows if r["tool"] == "query")["saved_tokens"] < 0
    assert next(r for r in rows if r["tool"] == "batch")["saved_tokens"] is None
    assert stats.report()["summary"]["net_usd"] is None


def test_disabled_and_fail_open(tmp_path, monkeypatch):
    monkeypatch.setenv("JEV_STATS_DIR", str(tmp_path / "unused"))
    assert stats.record("query", "a", "b", result()) is None
    assert not (tmp_path / "unused").exists()
    monkeypatch.setenv("JEV_STATS_DISABLED", "1")
    assert stats.record("query", "a", "b", result()) is None


def test_concurrent_records_and_filters(home):
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda _: stats.record("query", "x" * 500, "y", result()), range(16)))
    assert stats.report()["summary"]["runs"] == 16
    assert stats.report(model="missing")["summary"]["runs"] == 0
    with closing(sqlite3.connect(home / "usage.sqlite3")) as conn:
        assert conn.execute("select count(*) from events").fetchone()[0] == 16


def test_config_validation_preserves_previous(home):
    original = (home / "config.json").read_bytes()
    for rate in [float("nan"), float("inf"), -1]:
        with pytest.raises(ValueError):
            stats.configure("test", "bytes", rate, 0, 0)
    assert (home / "config.json").read_bytes() == original


def test_counter_failure_is_unknown(home, monkeypatch):
    monkeypatch.setattr(
        stats, "count_pair", lambda *a: (_ for _ in ()).throw(ValueError("private"))
    )
    stats.record("query", "sensitive", "output", result())
    row = stats.report()["events"][0]
    assert row["before_tokens"] is None and row["net_usd"] is None
    assert row["count_error"] == "ValueError"
    assert "private" not in json.dumps(row)


def test_cli_automatically_records_exact_rendered_output(home, monkeypatch, capsys, tmp_path):
    from jev_context import cli

    path = tmp_path / "records.json"
    path.write_text(json.dumps([{"id": "a", "text": "hello"}]))
    monkeypatch.setattr(
        "sys.argv",
        ["jev-filter", "query", "--input", str(path), "--task", "read", "--mode", "passthrough"],
    )
    assert cli.main() == 0
    output = capsys.readouterr().out
    row = stats.report()["events"][0]
    assert row["after_bytes"] == len(output.encode())
    assert row["status"] == "passthrough"
    assert row["saved_tokens"] is None


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_official_counters_no_generation_or_redirects(home, monkeypatch, provider):
    import httpx

    requests = []

    def handler(request):
        requests.append(request)
        assert request.url.host in ("api.openai.com", "api.anthropic.com")
        return httpx.Response(200, json={"input_tokens": 20 if len(requests) == 1 else 5})

    original = httpx.Client
    monkeypatch.setattr(
        stats.httpx, "Client", lambda **kw: original(transport=httpx.MockTransport(handler), **kw)
    )
    monkeypatch.setenv(provider.upper() + "_API_KEY", "synthetic-test-only")
    stats.configure("model", provider, 10, 0.042, 0)
    stats.record("query", "before", "after", result())
    row = stats.report()["events"][0]
    assert row["saved_tokens"] == 15
    assert len(requests) == 2
    assert all("count_tokens" in r.url.path or "input_tokens" in r.url.path for r in requests)


def test_invalid_api_count_and_missing_credentials(home, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    stats.configure("model", "openai", 10, 0.042, 0)
    stats.record("query", "secret", "after", result())
    assert stats.report()["events"][0]["count_error"] == "ValueError"


def test_tiktoken_counts_exact_text_under_selected_encoding(home, monkeypatch):
    import sys
    from types import SimpleNamespace

    encoding = SimpleNamespace(name="fixture", encode=lambda s, **kw: s.split())
    monkeypatch.setitem(
        sys.modules,
        "tiktoken",
        SimpleNamespace(get_encoding=lambda n: encoding, encoding_for_model=lambda n: encoding),
    )
    stats.configure("model", "tiktoken", 10, 0.042, 0, encoding="fixture")
    stats.record("query", "a b c d", "a b", result())
    assert stats.report()["events"][0]["saved_tokens"] == 2


def test_cli_config_report_export_disable(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("JEV_STATS_DIR", str(tmp_path / "stats"))
    assert stats.main(["configure", "--model", "example", "--input-rate", "1"]) == 0
    capsys.readouterr()
    assert stats.main(["report", "--since", "2026-01-01", "--until", "2026-12-31"]) == 0
    assert json.loads(capsys.readouterr().out)["summary"]["runs"] == 0
    target = tmp_path / "dashboard.html"
    stats.main(["dashboard", "--html", str(target)])
    assert "__DATA__" not in target.read_text()
    with pytest.raises(FileExistsError):
        stats.main(["dashboard", "--html", str(target)])
    stats.main(["disable"])
    assert not (tmp_path / "stats/config.json").exists()
    with pytest.raises(ValueError):
        stats.report(since="2026-12-31", until="2026-01-01")


def test_database_failure_keeps_output_safe(home, monkeypatch, capsys):
    monkeypatch.setattr(stats, "connect", lambda: (_ for _ in ()).throw(OSError("PRIVATE")))
    assert stats.record("query", "a", "b", result()) is None
    error = capsys.readouterr().err
    assert "stats_warning" in error and "PRIVATE" not in error


def test_dashboard_escapes_script_data_and_rejects_other_hosts(home):
    import threading

    import httpx

    from jev_context.dashboard import page, server

    html = page({"events": [], "example": "</script><script>alert(1)</script>"})
    assert "</script><script>alert" not in html
    httpd, url = server(0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        with httpx.Client(trust_env=False) as client:
            assert client.get(url).status_code == 200
            assert client.get(url.replace("/?", "/data?")).json()["summary"]["runs"] == 0
            assert client.get(url.split("?")[0]).status_code == 403
            assert client.get(url, headers={"Host": "attacker.invalid"}).status_code == 403
            assert client.get(url.replace("/?", "/no-file?")).status_code == 404
    finally:
        httpd.shutdown()
        thread.join()
        httpd.server_close()
