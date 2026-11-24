"""Click through the local page with the vignette example in headless Chromium and save screenshots.

Starts sigshell-ui on a free port with a throwaway Sigshell folder, then follows the demo path:
example data, check, scores with the heatmap, significance with one histogram, the R script.
It also uploads one broken matrix (decimal commas) to show the check refusing it.
Every step waits for the page's own result, so a failure here is a failure of the page.

Usage, from the repository root (needs R, the pinned sigscores, and Playwright's Chromium):
    uv run --with playwright python examples/screenshots.py <output folder>
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

HERE = Path(__file__).parent
BROKEN = HERE / "malformed-inputs" / "06-decimal-comma" / "matrix.tsv"
LONG = 300_000  # ms; R steps on a cold runner can be slow


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> None:
    out = Path(sys.argv[1]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    port = free_port()
    home = tempfile.mkdtemp()
    env = os.environ | {"SIGSHELL_HOME": home}
    ui = subprocess.Popen([sys.executable, "-m", "sigshell.web", "--no-browser", "--port", str(port)], env=env)
    url = f"http://127.0.0.1:{port}/"
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(url, timeout=2)
                break
            except OSError:
                time.sleep(1)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900}, color_scheme="light", device_scale_factor=2)
            page.goto(url)
            expect(page.locator("#status")).to_have_class("status ok", timeout=LONG)

            page.click("#example")
            page.select_option("#expression-scale", "other")
            expect(page.locator("#s-check")).to_be_visible(timeout=LONG)
            expect(page.locator("#s-scores")).to_be_visible(timeout=LONG)
            page.screenshot(path=out / "01-data-and-check.png", full_page=False)
            page.locator("#s-check").screenshot(path=out / "02-check.png")

            page.get_by_role("button", name="Recommended start: mean + median").click()
            page.click("#run-scores")
            expect(page.locator("#scores-out table")).to_be_visible(timeout=LONG)
            page.get_by_role("button", name="Heatmap (raw values)").click()
            expect(page.locator("#scores-out figure img")).to_be_visible(timeout=LONG)
            page.locator("#s-scores").screenshot(path=out / "03-scores-and-heatmap.png")

            page.click("#run-sig")
            expect(page.locator("#sig-out table")).to_be_visible(timeout=LONG)
            page.locator("#sig-out").get_by_role("button", name="Histogram").first.click()
            expect(page.locator("#sig-out figure img")).to_be_visible(timeout=LONG)
            page.locator("#s-sig").screenshot(path=out / "04-significance.png")

            page.click("#show-script")
            expect(page.locator("#script-out")).not_to_be_empty(timeout=LONG)
            page.locator("#s-script").screenshot(path=out / "05-reproduce.png")
            page.screenshot(path=out / "00-whole-page.png", full_page=True)

            page.locator('.picker[data-role="matrix"] input[type=file]').set_input_files(str(BROKEN))
            expect(page.locator("#check-out")).to_contain_text("decimal commas", timeout=LONG)
            page.locator("#s-check").screenshot(path=out / "06-check-refuses-decimal-commas.png")

            narrow = browser.new_page(viewport={"width": 390, "height": 844}, color_scheme="dark", device_scale_factor=2)
            narrow.goto(url)
            expect(narrow.locator("#status")).to_have_class("status ok", timeout=LONG)
            narrow.screenshot(path=out / "07-phone-width-dark.png")
            browser.close()
    finally:
        ui.terminate()
        ui.wait(timeout=10)
    print("\n".join(sorted(p.name for p in out.glob("*.png"))))


if __name__ == "__main__":
    main()
