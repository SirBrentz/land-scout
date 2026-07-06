"""Shared browser session for scrapers.

Both LandWatch (Akamai) and LandSearch (Cloudflare) block headless Chromium,
but pass a real installed Chrome running headed. We launch Chrome with the
window positioned off-screen so scheduled runs don't flash a window.
"""
from contextlib import contextmanager

from playwright.sync_api import sync_playwright

PAGE_DELAY_MS = 2500  # politeness delay between page loads


@contextmanager
def browser_context():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            headless=False,
            args=["--window-position=-2400,-2400", "--window-size=1400,900"],
        )
        ctx = browser.new_context(viewport={"width": 1400, "height": 900}, locale="en-US")
        try:
            yield ctx
        finally:
            browser.close()


def get_page_html(ctx, url: str, wait_ms: int = 4000, timeout_ms: int = 45000) -> str:
    page = ctx.new_page()
    try:
        resp = page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
        page.wait_for_timeout(wait_ms)
        html = page.content()
        status = resp.status if resp else 0
        title = page.title().lower()
        if status != 200 or "just a moment" in title or "access denied" in title:
            raise RuntimeError(f"blocked: status={status} title={title[:60]!r} url={url}")
        return html
    finally:
        page.close()
