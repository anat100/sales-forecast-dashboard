"""Render the dashboard locally and save PNG screenshots into ./assets.

Usage:  pip install playwright && playwright install chromium
        python scripts/screenshot.py
Serves the repo on a local port, opens preview/index.html in headless Chromium,
and captures the full page plus the key cards.
"""
import contextlib
import functools
import http.server
import os
import socketserver
import threading

from playwright.sync_api import sync_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "assets")
os.makedirs(OUT, exist_ok=True)


@contextlib.contextmanager
def serve():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
    handler = functools.partial(Quiet, directory=ROOT)
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as httpd:
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        yield f"http://127.0.0.1:{httpd.server_address[1]}"
        httpd.shutdown()


def open_page(browser, base, width, query="", height=900):
    page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=2)
    errors = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{base}/preview/index.html{query}")
    page.wait_for_selector("html[data-ready='1']")
    page.wait_for_timeout(600)
    if errors:
        raise SystemExit("Page errors: " + " | ".join(errors))
    return page


def shot(page, name, selector=None, full=False):
    path = os.path.join(OUT, name)
    if selector:
        page.locator(selector).screenshot(path=path)
    else:
        page.screenshot(path=path, full_page=full)
    print("saved", os.path.relpath(path, ROOT))


with serve() as base, sync_playwright() as p:
    browser = p.chromium.launch()
    page = open_page(browser, base, 1360, "?theme=light")
    shot(page, "dashboard-full.png", full=True)
    shot(page, "overview.png")  # first screen: takeaway + headline figures
    shot(page, "cumulative-forecast.png", "#cum-card")
    shot(page, "quarter-categories.png", "#q-card")
    shot(page, "rep-scorecard.png", "#reps")
    shot(page, "mrr-vs-plan.png", "#mrr-card")
    page.close()

    page = open_page(browser, base, 1360, "?theme=light&rep=A.%20Becker")
    shot(page, "rep-drilldown.png")
    page.close()

    page = open_page(browser, base, 1360, "?theme=dark")
    shot(page, "dashboard-dark.png")
    page.close()

    page = open_page(browser, base, 420, "?theme=light", height=860)
    shot(page, "mobile.png")
    page.close()
    browser.close()
