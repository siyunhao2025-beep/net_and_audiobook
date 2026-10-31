#!/usr/bin/env python3
"""Capture the original, two-term demo for documentation, without browser chrome/accounts."""
import argparse, functools, hashlib, http.server, json, threading
from pathlib import Path

def capture(stage, out):
    from playwright.sync_api import sync_playwright
    stage, out = Path(stage).resolve(), Path(out).resolve()
    project = json.loads((stage / "project.json").read_text(encoding="utf-8-sig"))
    if project.get("project_id") != "space-weather-demo" or len(project.get("terms", [])) != 2:
        raise ValueError("Capture only the original make_demo.py project, not user documents")
    catalog = json.loads((stage / "audiobook/catalog.json").read_text(encoding="utf-8-sig"))
    if not catalog.get("episodes") or not all(e.get("ready") for e in catalog["episodes"]):
        raise ValueError("Generate and verify the original demo audio first")
    if out == stage or out.is_relative_to(stage): raise ValueError("Keep documentation captures outside the demo stage")
    out.mkdir(parents=True, exist_ok=True)
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *_): pass
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(stage)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as pw:
            opts = {"headless": True, "args": ["--autoplay-policy=no-user-gesture-required"]}
            try: browser = pw.chromium.launch(**opts)
            except Exception: browser = pw.chromium.launch(channel="msedge", **opts)
            try:
                page = browser.new_page(viewport={"width": 1440, "height": 960}, device_scale_factor=1)
                base = f"http://127.0.0.1:{server.server_port}"
                page.goto(base + "/index.html"); page.locator('[data-chapter="ch-solar-wind"]').click()
                page.locator('#timer-toggle').click(); page.screenshot(path=str(out / "learning-preview.png"))
                page.goto(base + "/audiobook/index.html")
                page.evaluate("document.getElementById('audio').muted=true")
                page.locator('.episode button').first.click()
                page.wait_for_function("document.getElementById('audio').currentTime>=1.1 && !document.getElementById('audio').paused")
                page.evaluate("()=>{const a=document.getElementById('audio');a.pause();a.muted=false}")
                page.wait_for_function("!document.getElementById('audio-status').textContent.includes('interrupted')")
                page.screenshot(path=str(out / "audiobook-preview.png"))
            finally: browser.close()
    finally: server.shutdown(); server.server_close()
    print(json.dumps([{ "file": f.name, "sha256": hashlib.sha256(f.read_bytes()).hexdigest(), "bytes": f.stat().st_size }
                      for f in sorted(out.glob("*-preview.png"))], indent=2))

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument("--stage", required=True); ap.add_argument("--out", required=True)
    args = ap.parse_args(); capture(args.stage, args.out)
