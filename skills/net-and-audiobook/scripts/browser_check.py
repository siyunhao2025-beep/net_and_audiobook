#!/usr/bin/env python3
"""Exercise actual browser state over HTTP/file at desktop/mobile widths (Playwright)."""
from __future__ import annotations
import argparse, functools, http.server, json, tempfile, threading
from pathlib import Path
from common import *

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_): pass

def run(stage, audio=False, executable=None):
    from playwright.sync_api import sync_playwright
    stage = Path(stage).resolve(); hashes = delivery_hashes(stage); p = read_json(stage / "project.json")
    errors, checks = [], []
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(stage)))
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    urls = [("http", f"http://127.0.0.1:{server.server_port}/index.html"), ("file", (stage / "index.html").as_uri())]
    try:
        with sync_playwright() as pw:
            options = {"headless": True, "args": ["--autoplay-policy=no-user-gesture-required"]}
            if executable: options["executable_path"] = executable
            try: browser = pw.chromium.launch(**options)
            except Exception:
                if executable: raise
                browser = pw.chromium.launch(channel="msedge", **options)
            for transport, url in urls:
                for width in (1280, 390):
                    ctx = browser.new_context(viewport={"width": width, "height": 900}, accept_downloads=True)
                    page = ctx.new_page(); js_errors = []; page.on("pageerror", lambda e: js_errors.append(str(e)))
                    label = f"{transport}:{width}"
                    try:
                        page.goto(url); page.wait_for_selector("[data-chapter]", state="attached")
                        assert page.title() == p["title_zh"], "Title/data failed"
                        if width == 390: page.locator("#menu").click()
                        first = p["chapters"][0]; page.locator(f'[data-chapter="{first["id"]}"]').click()
                        if p.get("ui", {}).get("sequential") and len(p["chapters"]) > 1:
                            assert "🔒" in page.locator(f'[data-chapter="{p["chapters"][1]["id"]}"]').inner_text(), "Initial lock missing"
                        unit = first["units"][0]; b = page.locator(f'[data-unit-check="{unit["id"]}"]'); b.click()
                        assert b.get_attribute("aria-pressed") == "true", "Unit check did not persist"
                        page.reload(); page.wait_for_selector(f'#{unit["id"]}', state="visible")
                        assert page.locator(f'[data-unit-check="{unit["id"]}"]').get_attribute("aria-pressed") == "true", "Reload lost unit state"
                        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2"), "Page overflows viewport"
                        page.locator("#theme").click(); theme = page.locator("html").get_attribute("data-theme"); page.reload()
                        assert page.locator("html").get_attribute("data-theme") == theme, "Theme lost on reload"
                        for _ in range(3):
                            page.locator("#language").click(); language = page.locator("html").get_attribute("data-lang")
                            active_unit = page.locator(f'#{unit["id"]}')
                            if language == "en": assert not active_unit.locator(".zh").first.is_visible() and active_unit.locator(".en").first.is_visible(), "English switch failed"
                            if language == "zh": assert not active_unit.locator(".en").first.is_visible() and active_unit.locator(".zh").first.is_visible(), "Chinese switch failed"
                        if width == 390: page.locator("#menu").click()
                        page.locator("#search").fill(unit["title_zh"]); assert page.locator("#results button").count() >= 1, "Search failed"
                        with page.expect_download() as dl: page.locator("#export").click()
                        exported = read_json(dl.value.path()); assert exported["project_id"] == p["project_id"], "Export has wrong project"
                        page.locator("#search").fill("")
                        with tempfile.TemporaryDirectory() as temp:
                            foreign = Path(temp) / "foreign.json"; write_json(foreign, {"schema_version": 1, "project_id": "foreign-project", "state": {"done": []}})
                            page.locator("#import").set_input_files(str(foreign)); page.wait_for_function("document.getElementById('storage-status').textContent.includes('导入失败')")
                            local = Path(temp) / "local.json"; write_json(local, {"schema_version": 1, "project_id": p["project_id"], "state": {"done": [unit["id"], "unknown-unit"], "lang": "both", "theme": theme}})
                            page.locator("#import").set_input_files(str(local)); page.wait_for_function("document.getElementById('storage-status').textContent.includes('已导入')")
                            saved = page.evaluate("k => JSON.parse(localStorage.getItem(k))", f"nba.{p['project_id']}.study.v1")
                            assert saved["done"] == [unit["id"]], "Import accepted an unknown unit"
                        page.locator(f'[data-chapter="{first["id"]}"]').click()
                        for formula in page.locator(".chapter:not([hidden]) [data-formula]").all():
                            assert formula.bounding_box()["height"] > 10, "Invisible formula"
                            if formula.locator("math").count(): assert formula.locator("math").bounding_box()["width"] > 5, "MathML failed"
                            formula.locator("summary").click()
                            page.wait_for_function("el => el.complete && el.naturalWidth > 0", arg=formula.locator("details img").element_handle())
                        for image in page.locator(".chapter:not([hidden]) figure img").all():
                            image.scroll_into_view_if_needed(); page.wait_for_function("el => el.complete && el.naturalWidth > 0", arg=image.element_handle())
                            image.click(); assert page.locator("#lightbox").is_visible(); page.keyboard.press("Escape")
                        page.locator("#timer-toggle").click(); page.wait_for_timeout(1200); page.locator("#home").click()
                        before = page.locator("#timer").inner_text(); page.wait_for_timeout(1200)
                        assert page.locator("#timer").inner_text().split(" · ")[0] == before.split(" · ")[0], "Timer runs on overview"
                        if audio:
                            audio_url = url.rsplit("/", 1)[0] + "/audiobook/index.html"
                            page.goto(audio_url); page.locator(".episode button").first.click()
                            page.wait_for_function("document.getElementById('audio').readyState >= 1", timeout=30000)
                            assert page.evaluate("document.getElementById('audio').playbackRate === 1 && document.getElementById('audio').defaultPlaybackRate === 1"), "Actual default rate differs from display"
                            page.locator("#speed").select_option("0.9"); page.reload(); page.wait_for_function("document.getElementById('audio').readyState >= 1", timeout=30000)
                            assert page.evaluate("document.getElementById('audio').playbackRate === 0.9 && document.getElementById('audio').defaultPlaybackRate === 0.9"), "Manual speed failed to persist"
                            page.evaluate("k => { const s=JSON.parse(localStorage.getItem(k)); s.version='old-version'; s.speed=0.8; localStorage.setItem(k,JSON.stringify(s)); }", f"nba.{p['project_id']}.audio.v1")
                            page.reload(); assert page.locator("#speed").input_value() == "1", "New audio version did not reset speed"
                            page.locator(".episode button").first.click(); page.wait_for_function("document.getElementById('audio').readyState >= 1", timeout=30000)
                            assert page.evaluate("document.getElementById('audio').playbackRate === 1"), "Version-reset actual rate failed"
                            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2"), "Audio page overflows"
                        assert not js_errors, "JS errors: " + str(js_errors)
                        checks.append({"case": label, "passed": True})
                    except Exception as e: errors.append({"case": label, "error": str(e)})
                    finally: ctx.close()
            browser.close()
    finally: server.shutdown(); server.server_close()
    if delivery_hashes(stage) != hashes: errors.append({"error": "Files changed during browser QA"})
    report = {"schema_version": 1, "project_id": p["project_id"], "transports": ["http", "file"], "widths": [1280, 390], "audio_checked": audio,
              "errors": errors, "checks": checks, "delivery_hashes": hashes, "limitations": "Behavior/layout checks do not evaluate scientific correctness or voice naturalness."}
    write_json(stage / "browser-report.json", report); print(json.dumps({"errors": errors, "cases": checks}, ensure_ascii=False)); return report

def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument("--stage", required=True); ap.add_argument("--audio", action="store_true"); ap.add_argument("--browser-executable"); a = ap.parse_args()
    raise SystemExit(bool(run(a.stage, a.audio, a.browser_executable)["errors"]))
if __name__ == "__main__": main()
