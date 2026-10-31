#!/usr/bin/env python3
"""Fail closed on obvious private/binary artifacts in a public skill repository export."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

FORBIDDEN_SUFFIX = {".pdf", ".mp3", ".wav", ".flac", ".zip", ".pt", ".pth", ".onnx", ".npz", ".npy", ".pkl", ".pyc", ".pem", ".key", ".sqlite", ".db"}
PATTERNS = {
    "credential": r"\b(?:github_pat_[A-Za-z0-9_]{15,}|gh[pousr]_[A-Za-z0-9]{15,}|sk-[A-Za-z0-9_-]{20,}|hf_[A-Za-z0-9]{20,}|AKIA[A-Z0-9]{16})\b",
    "private_key": r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    "private_home": r"(?i)(?:[A-Z]:[\\/]+Users[\\/]+(?!EXAMPLE(?:[\\/]|$))(?![\[(])[^\\/\s\"']+|/(?:Users|home)/(?!EXAMPLE/)(?![\[(])[^/\s\"']+)",
    "device_identity": r"(?i)DESKTOP-[A-Z0-9]{5,}",
}

def scan(root, allow_readme_images=False):
    root = Path(root).resolve(); errors = []; count = 0
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root).as_posix()
        if ".git" in p.relative_to(root).parts: continue
        if p.is_symlink(): errors.append([rel, "symlink"]); continue
        if not p.is_file(): continue
        count += 1
        if p.suffix.lower() in FORBIDDEN_SUFFIX or p.name.startswith(".env") or any(x in ("__pycache__", "tts_cache", "corpus", "node_modules", "backup") for x in p.relative_to(root).parts): errors.append([rel, "private/generated/large artifact"])
        if p.stat().st_size > 2_000_000: errors.append([rel, "file exceeds 2 MB"]); continue
        if allow_readme_images and re.fullmatch(r"assets/readme/[a-z0-9-]+\.png", rel):
            try:
                from PIL import Image
                if not p.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"): raise ValueError("PNG signature mismatch")
                with Image.open(p) as im:
                    im.load()
                    if im.format != "PNG" or not all(0 < d <= 8192 for d in im.size): raise ValueError("Invalid PNG size/format")
                    if set(im.info) - {"dpi", "gamma", "srgb", "transparency"}: raise ValueError("Unreviewed PNG metadata")
            except Exception as e: errors.append([rel, "README PNG rejected: " + type(e).__name__])
            continue
        try: text = p.read_text(encoding="utf-8")
        except UnicodeError: errors.append([rel, "non-text file needs explicit review"]); continue
        for name, pattern in PATTERNS.items():
            if re.search(pattern, text): errors.append([rel, name])
    return {"files": count, "errors": errors, "limitations": "Heuristic scan; also review the explicit export allowlist and diff. No scanner proves absence of secrets."}

def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument("--root", required=True)
    ap.add_argument("--allow-readme-images", action="store_true", help="Allow only reviewed PNGs under assets/readme, with signature, size and metadata checks")
    a = ap.parse_args(); report = scan(a.root, a.allow_readme_images); print(json.dumps(report, ensure_ascii=False, indent=2)); raise SystemExit(bool(report["errors"]))
if __name__ == "__main__": main()
