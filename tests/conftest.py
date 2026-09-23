"""Never use a developer's configured ledger or remote counting mode in tests."""

import pytest


@pytest.fixture(autouse=True)
def isolate_statistics(tmp_path, monkeypatch):
    monkeypatch.setenv("JEV_STATS_DIR", str(tmp_path / "isolated-statistics"))
    monkeypatch.delenv("JEV_STATS_DISABLED", raising=False)
