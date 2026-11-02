"""Browser tests for the core interactions, run against the Pages-like dev server.

Needs `playwright` (requirements-dev.txt) and a Chromium: `python -m playwright install
chromium`, or set CHROME_PATH to an installed Chrome. Skipped when neither is available.
"""

from __future__ import annotations

import importlib.util
import os
import re
import threading
from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright.sync_api")

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "art_of_thinking_clearly.md"


def _load_serve():
    spec = importlib.util.spec_from_file_location("serve", ROOT / "scripts" / "serve.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def base_url():
    server = _load_serve().make_server(port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}/playbooks-notes/"
    server.shutdown()


@pytest.fixture(scope="module")
def browser():
    with playwright.sync_playwright() as p:
        try:
            b = p.chromium.launch(executable_path=os.environ.get("CHROME_PATH") or None)
        except Exception as exc:  # no browser installed
            pytest.skip(f"Chromium not available: {exc}")
        yield b
        b.close()


@pytest.fixture
def page(browser, base_url):
    ctx = browser.new_context(accept_downloads=True)
    pg = ctx.new_page()
    pg.errors = []
    pg.on("pageerror", lambda e: pg.errors.append(str(e)))
    pg.on("console", lambda m: m.type == "error" and pg.errors.append(m.text))
    pg.goto(base_url)
    pg.wait_for_selector("#dropzone[data-state=ready]")
    yield pg
    ctx.close()


def upload(page, path=FIXTURE):
    page.set_input_files("#file-input", str(path))


def test_landing_page_basics(page):
    assert page.title() == "Play Books Notes to Markdown: organize your highlights"
    assert page.locator("h1").count() == 1
    assert page.get_attribute('link[rel="canonical"]', "href") == "https://destroyer-droid.github.io/playbooks-notes/"
    assert page.get_attribute('meta[property="og:image"]', "content").endswith("/og-image.png")
    assert page.is_enabled("#choose")
    assert page.is_hidden("#result")
    assert page.errors == []


def test_upload_shows_summary_and_preview(page):
    upload(page)
    page.wait_for_selector("#result:not([hidden])")
    assert page.text_content("#book-title") == "The Art of Thinking Clearly"
    assert page.text_content("#counts").startswith("351 notes across 98 chapters")
    assert page.inner_text("#legend").split() == ["Yellow", "30", "Green", "109", "Blue", "135", "Red", "77"]
    assert page.text_content("#preview").startswith("# The Art of Thinking Clearly\n\n## Introduction\n\n- ")
    # Focus moves to the new content so screen readers announce it.
    assert page.evaluate("document.activeElement.id") == "book-title"
    # The preview is read-only text, never an editable field.
    assert page.evaluate("document.getElementById('preview').isContentEditable") is False
    assert page.errors == []


def test_options_rerender_and_download(page):
    upload(page)
    page.wait_for_selector("#result:not([hidden])")
    page.click("label[for=g-both]")
    page.click("label[for=s-quote]")
    md = page.text_content("#preview")
    assert re.search(r"^## Yellow\n\n### 1: ", md, re.M)
    assert "\n> " in md
    assert page.text_content("#preview-meta") == "Grouped by color, then chapter, as quote blocks."
    with page.expect_download() as info:
        page.click("#download")
    download = info.value
    assert download.suggested_filename == "The Art of Thinking Clearly - Notes.md"
    assert Path(download.path()).read_text(encoding="utf-8") == md


def test_keyboard_only_flow(page):
    page.keyboard.press("Tab")  # skip link first
    assert page.evaluate("document.activeElement.className") == "skip-link"
    # Enter on the button must open the file picker. Record the input's click and stop
    # the native dialog (intercepting the OS dialog itself is flaky in headless runs).
    page.evaluate(
        """() => document.getElementById('file-input').addEventListener('click', (e) => {
               window.__pickerOpened = true; e.preventDefault(); }, { once: true })"""
    )
    page.focus("#choose")
    page.keyboard.press("Enter")
    page.wait_for_function("window.__pickerOpened === true")
    upload(page)
    page.wait_for_selector("#result:not([hidden])")
    page.focus("#g-chapter")
    page.keyboard.press("ArrowRight")  # radios move with arrow keys
    assert page.is_checked("#g-color")
    assert page.text_content("#preview").split("\n")[2] == "## Yellow"


def test_wrong_file_shows_error(page, tmp_path):
    essay = tmp_path / "essay.md"
    essay.write_text("# My essay\n\nNot a notes export.\n", encoding="utf-8")
    upload(page, essay)
    alert = page.locator("#upload-alert")
    alert.wait_for(state="visible")
    assert alert.text_content() == "This doesn't look like a Play Books notes export."
    assert page.is_hidden("#result")

    txt = tmp_path / "notes.txt"
    txt.write_text("hello", encoding="utf-8")
    upload(page, txt)
    assert alert.text_content().startswith("That isn't a Markdown file.")


def test_reset_returns_to_upload(page):
    upload(page)
    page.wait_for_selector("#result:not([hidden])")
    page.click("#reset")
    assert page.is_hidden("#result")
    assert page.evaluate("document.activeElement.id") == "choose"


def test_theme_toggle_persists(page):
    page.click("#theme-toggle")
    first = page.evaluate("document.documentElement.dataset.theme")
    assert first in ("light", "dark")
    page.reload()
    assert page.evaluate("document.documentElement.dataset.theme") == first
    assert page.get_attribute("#theme-toggle", "aria-label").startswith("Switch to ")


def test_error_boundary(page):
    page.evaluate("setTimeout(() => { throw new Error('boom'); })")
    page.wait_for_selector("#app-error:not([hidden])")
    assert page.text_content("#app-error-title") == "Something went wrong on this page"


def test_404_page(browser, base_url):
    pg = browser.new_page()
    response = pg.goto(base_url + "no/such/page")
    assert response.status == 404
    assert pg.locator("h1").count() == 1
    assert pg.get_attribute('meta[name="robots"]', "content") == "noindex"
    assert pg.get_attribute("a.button-primary", "href") == "/playbooks-notes/"
    # Assets load from absolute paths even at depth.
    assert pg.evaluate("getComputedStyle(document.body).fontFamily").startswith('"Google Sans"')
    pg.close()


@pytest.mark.parametrize("path", ["robots.txt", "sitemap.xml", "manifest.webmanifest", "og-image.png", "icons/icon-512.png"])
def test_static_files_exist(browser, base_url, path):
    pg = browser.new_page()
    assert pg.goto(base_url + path).status == 200
    pg.close()


def test_how_it_works_link(page):
    page.click("#nav-how")
    section = page.locator("#how-it-works")
    page.wait_for_function("location.hash === '#how-it-works'")
    box = section.bounding_box()
    assert box["y"] < 200  # scrolled to the section
    assert page.locator("#how-it-works h2").text_content() == "How it works"
    assert page.locator("#how-it-works h3").count() == 4
    page.wait_for_function("document.getElementById('nav-how').getAttribute('aria-current') === 'location'")


def test_coffee_link_in_navbar(page):
    link = page.locator('nav a[href="https://buymeacoffee.com/immanuelvivek"]')
    assert link.count() == 1
    assert link.get_attribute("target") == "_blank"
    assert "noopener" in link.get_attribute("rel")
    assert " ".join(link.text_content().split()) == "Buy me a coffee (opens in a new tab)"


@pytest.mark.parametrize("width, height", [(1280, 800), (1680, 1000), (820, 1180)])
def test_how_it_works_starts_one_screen_down(browser, base_url, width, height):
    pg = browser.new_page(viewport={"width": width, "height": height})
    pg.goto(base_url)
    pg.wait_for_selector("#dropzone[data-state=ready]")
    top = pg.evaluate("document.getElementById('how-it-works').getBoundingClientRect().top + scrollY")
    assert abs(top - height) <= 2  # exactly one viewport from the top
    pg.close()
