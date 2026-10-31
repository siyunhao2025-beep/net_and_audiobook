#!/usr/bin/env python3
"""Check README local links, image metadata and GitHub-compatible SVGs, without network."""
import json, re
from pathlib import Path
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit, unquote

ROOT = Path(__file__).resolve().parents[1]

def check():
    from PIL import Image
    errors = []; readme = (ROOT / "README.md").read_text(encoding="utf-8")
    links = re.findall(r'\]\(([^)\s]+)\)', readme)
    links += re.findall(r'<(?:img|a)\b[^>]*\b(?:src|href)=["\']([^"\']+)["\']', readme)
    anchors = set(re.findall(r'<a\b[^>]*\bid=["\']([^"\']+)["\']', readme))
    for link in links:
        u = urlsplit(link)
        if u.scheme:
            if u.scheme != "https": errors.append("Non-HTTPS external link: " + link)
            continue
        if not u.path:
            if u.fragment not in anchors: errors.append("Missing explicit anchor: " + link)
            continue
        p = (ROOT / unquote(u.path)).resolve()
        if not p.is_relative_to(ROOT) or not p.exists(): errors.append("Missing/unsafe local link: " + link)
    for tag in re.findall(r'<img\b[^>]*>', readme):
        if not re.search(r'\balt=["\'][^"\']+["\']', tag): errors.append("Image lacks meaningful alt text")
    image_files = list((ROOT / "assets/readme").glob("*"))
    for p in image_files:
        if p.stat().st_size > 2_000_000: errors.append("Image exceeds 2 MB: " + p.name)
        if p.suffix == ".png":
            with Image.open(p) as im:
                im.load()
                if im.format != "PNG" or not all(0 < d <= 8192 for d in im.size): errors.append("Invalid PNG: " + p.name)
                if set(im.info) - {"dpi", "gamma", "srgb", "transparency"}: errors.append("Review PNG metadata: " + p.name)
        elif p.suffix == ".svg":
            root = ET.parse(p).getroot(); ids = []
            if not root.get("viewBox") or not any(n.tag.endswith("}title") for n in root): errors.append("SVG needs title/viewBox: " + p.name)
            if not any(n.tag.endswith("}desc") for n in root): errors.append("SVG needs description: " + p.name)
            for n in root.iter():
                tag = n.tag.rsplit("}", 1)[-1]
                if tag in {"script", "foreignObject", "image", "animate", "animateTransform"}: errors.append("Unsupported SVG element: " + p.name + ":" + tag)
                if n.get("id"): ids.append(n.get("id"))
                for key, value in n.attrib.items():
                    if key.lower().startswith("on") or (key.rsplit("}", 1)[-1] == "href" and not value.startswith("#")): errors.append("Active/external SVG reference: " + p.name)
                if tag == "text" and float(n.get("font-size", 20)) < 18: errors.append("SVG text below 18 units: " + p.name)
            if len(ids) != len(set(ids)): errors.append("Duplicate SVG IDs: " + p.name)
    result = {"local_and_external_links": len(links), "images": len(image_files), "errors": errors,
              "limits": "Static checks do not replace wide/mobile visual inspection or scientific review."}
    print(json.dumps(result, ensure_ascii=False, indent=2)); return result

if __name__ == "__main__": raise SystemExit(bool(check()["errors"]))
