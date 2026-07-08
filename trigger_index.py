"""Automate the DeepWiki 'Index Repository' submission with a real browser (reCAPTCHA runs natively)."""
import sys
from playwright.sync_api import sync_playwright

REPO_URL = "https://deepwiki.com/adames-cognition/quotepath-repro-strict"
EMAIL = "adames.hodelin@cognition.ai"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    ctx = browser.new_context(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )
    page = ctx.new_page()
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
    print("PAGE TITLE:", page.title())

    body_text = page.inner_text("body")[:500]
    if "Not Indexed" not in body_text and "Index Repository" not in body_text:
        print("Page does not show Not-Indexed state. Body head:")
        print(body_text)

    email_input = page.locator('input[type="email"], input[placeholder*="mail" i]').first
    email_input.wait_for(state="visible", timeout=15000)
    email_input.fill(EMAIL)
    print("Filled email:", EMAIL)

    btn = page.get_by_role("button", name="Index Repository")
    btn.click()
    print("Clicked Index Repository")

    for i in range(36):
        page.wait_for_timeout(5000)
        if any("index_public_repo" in u for _, _, u, _ in responses):
            page.wait_for_timeout(3000)
            break
        txt = page.inner_text("body")
        if "queued for indexing" in txt or "Indexing in Progress" in txt:
            break
        if "timeout" in txt.lower():
            print("reCAPTCHA timeout detected, retrying click...")
            try:
                page.get_by_role("button", name="Index Repository").click()
            except Exception as e:
                print("retry click failed:", e)
    print("\n--- api.devin.ai responses ---")
    for method, status, url, body in responses:
        print(method, status, url)
        if "index_public_repo" in url:
            print("  BODY:", body)

    print("\n--- page state after submit ---")
    print(page.inner_text("body")[:600])
    browser.close()
