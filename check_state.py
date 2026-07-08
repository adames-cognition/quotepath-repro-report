"""Render the DeepWiki page and capture the post-indexing UI state + screenshot."""
import sys
from playwright.sync_api import sync_playwright

REPO_URL = sys.argv[1] if len(sys.argv) > 1 else "https://deepwiki.com/adames-cognition/quotepath-repro-strict"
SHOT = sys.argv[2] if len(sys.argv) > 2 else "/Users/ah/CascadeProjects/quotepath-repro-report/evidence/08_strict_ui_state.png"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    responses = []
    def on_resp(r):
        if "api.devin.ai" in r.url:
            try:
                body = r.text()[:300]
            except Exception:
                body = "<unavailable>"
            responses.append((r.request.method, r.status, r.url, body))
    page.on("response", on_resp)
    page.goto(REPO_URL, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(5000)
    page.screenshot(path=SHOT, full_page=True)
    print("--- api.devin.ai calls ---")
    for m, s, u, b in responses:
        print(m, s, u)
        print("  BODY:", b)
    print("\n--- rendered body text (first 1200 chars) ---")
    print(page.inner_text("body")[:1200])
    browser.close()
