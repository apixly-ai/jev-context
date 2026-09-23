"""Rendered dashboard controls, reconciliation and responsive layout on synthetic data."""

import json
from pathlib import Path

import pytest

from jev_context import stats
from jev_context.dashboard import page


@pytest.mark.browser
def test_dashboard_filters_export_and_mobile(tmp_path, monkeypatch):
    sync = pytest.importorskip("playwright.sync_api")
    monkeypatch.setenv("JEV_STATS_DIR", str(tmp_path / "ledger"))
    stats.configure("fixture-gpt", "bytes", 10, 0.042, 0, price_source="synthetic fixture")
    result = {
        "ok": True,
        "complete": True,
        "telemetry": {"usage": {"input_tokens": 100, "output_tokens": 10}, "usage_complete": True},
    }
    stats.record("query", "a" * 4000, "b" * 400, result)
    stats.configure("fixture-claude", "bytes", 3, 0.042, 0, price_source="synthetic fixture")
    stats.record("triage", "a" * 400, "b" * 800, result)
    data = stats.report()
    errors = []
    with sync.sync_playwright() as p:
        browser = p.chromium.launch()
        tab = browser.new_page(viewport={"width": 1440, "height": 1100})
        tab.on("pageerror", lambda error: errors.append(str(error)))
        tab.route(
            "http://fixture.invalid/",
            lambda route: route.fulfill(body=page(data), content_type="text/html"),
        )
        tab.goto("http://fixture.invalid/")
        assert tab.locator("#tokens").inner_text() == "800"
        assert tab.locator("#net").inner_text() == "$0.008692"
        assert tab.locator("#daily .bar").count() == 1
        assert tab.locator("#tools .bar").count() == 2
        assert tab.locator("#tools .neg").count() == 1
        tab.locator("#model").select_option("fixture-gpt")
        assert tab.locator("#tokens").inner_text() == "900"
        with tab.expect_download() as download:
            tab.locator("#export").click()
        exported = json.loads(Path(download.value.path()).read_text())
        assert len(exported["events"]) == 1
        assert exported["events"][0]["model"] == "fixture-gpt"
        tab.locator("#reset").click()
        assert tab.locator("#tokens").inner_text() == "800"
        tab.locator("#since").fill("2099-01-01")
        tab.locator("#since").dispatch_event("change")
        assert tab.locator("#empty").is_visible()
        assert tab.locator("#tokens").inner_text() == "—"
        tab.locator("#reset").click()
        tab.screenshot(path=str(tmp_path / "dashboard-desktop.png"), full_page=True)
        tab.set_viewport_size({"width": 390, "height": 844})
        assert tab.evaluate("document.documentElement.scrollWidth <= innerWidth")
        tab.screenshot(path=str(tmp_path / "dashboard-mobile.png"), full_page=True)
        assert not errors
        browser.close()
