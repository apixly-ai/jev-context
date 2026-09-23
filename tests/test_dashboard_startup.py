"""Busy defaults should recover; explicit binds and unrelated failures stay distinct."""

import errno
import json

import pytest

from jev_context import dashboard, stats


def test_busy_default_chooses_an_available_loopback_port(monkeypatch):
    first, _ = dashboard.server(0)
    monkeypatch.setattr(dashboard, "DEFAULT_PORT", first.server_port, raising=False)
    try:
        second, url = dashboard.server()
        try:
            assert second.server_address[0] == "127.0.0.1"
            assert second.server_port != first.server_port
            assert url.startswith(f"http://127.0.0.1:{second.server_port}/?token=")
        finally:
            second.server_close()
    finally:
        first.server_close()


def test_explicit_busy_port_returns_actionable_error_without_fallback(capsys):
    first, _ = dashboard.server(0)
    try:
        assert dashboard.serve(first.server_port) == 1
        error = json.loads(capsys.readouterr().err)
        assert error["error_type"] == "PortInUse"
        assert "--port 0" in error["message"]
        assert error["port"] == first.server_port
    finally:
        first.server_close()


def test_permission_errors_do_not_trigger_port_fallback(monkeypatch):
    calls = []

    def denied(*args, **kwargs):
        calls.append(args)
        raise PermissionError(errno.EACCES, "denied")

    monkeypatch.setattr(dashboard, "DashboardHTTPServer", denied)
    with pytest.raises(PermissionError):
        dashboard.server()
    assert len(calls) == 1


def test_cli_default_and_explicit_port_and_exit_status(monkeypatch):
    calls = []
    monkeypatch.setattr(dashboard, "serve", lambda port, *args: calls.append(port) or 1)
    assert stats.main(["dashboard"]) == 1
    assert stats.main(["dashboard", "--port", "0"]) == 1
    assert calls == [None, 0]


@pytest.mark.parametrize("value", ["-1", "65536", "text"])
def test_cli_rejects_invalid_ports(value):
    with pytest.raises(SystemExit) as exc:
        stats.main(["dashboard", "--port", value])
    assert exc.value.code == 2
