"""Exercise observation and stale-target rejection on a fully local page."""

from pathlib import Path

import pytest


@pytest.mark.browser
def test_observe_excludes_values_and_guard_rejects_change():
    sync = pytest.importorskip("playwright.sync_api")
    script = (Path(__file__).resolve().parents[1] / "src/jev_context/locator_dom.js").read_text(
        encoding="utf-8"
    )
    with sync.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.route(
            "https://fixture.invalid/**",
            lambda route: route.fulfill(
                body='<main><button id="go">Continue</button><input aria-label="Name" value="PRIVATE_VALUE"><input type="password" value="SECRET"></main>',
                content_type="text/html",
            ),
        )
        page.goto("https://fixture.invalid/")
        policy = {"origin": "https://fixture.invalid", "scope": "main", "limit": 20}
        observed = page.evaluate(script, {"op": "observe", "policy": policy})
        assert len(observed["records"]) == 2
        assert "PRIVATE_VALUE" not in str(observed) and "SECRET" not in str(observed)
        req = {"op": "guard", "policy": policy, "token": observed["token"], "id": "1"}
        assert page.evaluate(script, req)["ok"]
        page.locator("#go").evaluate('(e) => e.textContent = "Delete"')
        assert page.evaluate(script, req) == {"ok": False, "reason": "target_changed"}
        browser.close()
