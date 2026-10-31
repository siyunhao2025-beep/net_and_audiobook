#!/usr/bin/env python3
"""Build a new isolated bilingual site and validated, unspoken-source glossary plans."""
from __future__ import annotations
import argparse, hashlib, json, shutil
from pathlib import Path
from common import *

ASSETS = Path(__file__).resolve().parents[1] / "assets" / "site"

def build(project_path, stage, sources_root):
    project_path = Path(project_path).resolve(); sources_root = Path(sources_root).resolve()
    p = validate_project(read_json(project_path))
    stage = outside(stage, [sources_root])
    if stage.exists() and any(stage.iterdir()): raise ValueError("Use a new empty stage; never rebuild a live site")
    # Validate every referenced asset before writing anything.
    assets = {}
    for s in p["sources"]:
        f = under(sources_root, s["path"])
        if not f.is_file() or sha(f) != s["sha256"]: raise ValueError("Source changed or missing: " + s["id"])
        assets[s["path"]] = f
    for v in p.get("visuals", []): assets[v["path"]] = under(sources_root, v["path"])
    for f in p.get("formulas", []):
        for key in ("source_image", "display_image"):
            if f.get(key): assets[f[key]] = under(sources_root, f[key])
        if f.get("mathml"): f["mathml"] = mathml(f["mathml"])
    allowed = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".txt", ".pptx", ".docx"}
    if len({rel.casefold() for rel in assets}) != len(assets): raise ValueError("Asset paths collide on Windows")
    for rel, f in assets.items():
        if f.suffix.lower() not in allowed: raise ValueError("Use raster formula/visual assets; unsupported source extension: " + rel)
        if not f.is_file(): raise FileNotFoundError(f)
    stage.mkdir(parents=True, exist_ok=True)
    for src in ASSETS.rglob("*"):
        if src.is_file():
            dest = under(stage, src.relative_to(ASSETS).as_posix()); dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
    for rel, src in assets.items():
        dest = under(stage, "sources/" + rel); dest.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(src, dest)
    atomic_write(stage / "project.js", ("window.LEARNING_PROJECT=" + json.dumps(p, ensure_ascii=False) + ";\n").encode())
    write_json(stage / "project.json", p)
    # Renderer changes invalidate the shell without resetting audiobook speed/position.
    version = fingerprint(p)[:16]
    renderer = hashlib.sha256()
    for src in sorted(x for x in ASSETS.rglob("*") if x.is_file()):
        renderer.update(src.relative_to(ASSETS).as_posix().encode()); renderer.update(src.read_bytes())
    shell_version = version + "-" + renderer.hexdigest()[:12]
    sw = (stage / "sw.js").read_text(encoding="utf-8").replace("__BUILD_VERSION__", shell_version).replace("__PROJECT_ID__", p["project_id"])
    atomic_write(stage / "sw.js", sw.encode())
    webmanifest = {"name": p["title_zh"], "short_name": p["title_zh"][:12], "start_url": "./index.html",
                   "scope": "./", "lang": "zh-CN", "display": "standalone", "theme_color": "#183e45", "background_color": "#f5f3eb"}
    write_json(stage / "app.webmanifest", webmanifest)
    terms = {t["id"]: t for t in p.get("terms", [])}; eps = []
    for e in p.get("episodes", []):
        plan = {"id": e["id"], "title_zh": e["title_zh"], "terms": []}
        for tid in e["term_ids"]:
            t = terms[tid]; plan["terms"].append({**t, "segments": segments(t, p.get("speech"))})
        write_json(stage / "audiobook/scripts" / (e["id"] + ".plan.json"), plan)
        transcript = "\n\n\n".join("\n\n".join(s["text"] for s in t["segments"]) for t in plan["terms"])
        atomic_write(stage / "audiobook/scripts" / (e["id"] + ".txt"), (transcript + "\n").encode())
        eps.append({**e, "term_count": len(e["term_ids"]), "audio": "audio/" + e["id"] + ".mp3", "ready": False,
                    "terms": [{"zh": terms[t]["zh"], "en": terms[t]["en"]} for t in e["term_ids"]]})
    rates = {**RATES, **p.get("speech", {}).get("rates", {})}
    voices = {**VOICES, **p.get("speech", {}).get("voices", {})}
    voice_label = "普通话与美式英语" if voices == VOICES else "中文与英语"
    disclosure = f"{voice_label}合成语音。英文短语原生语速{rates['term_en']}，拼写{rates['spelling']}；中文标准解释后接通俗解释。"
    catalog(stage, {"project_id": p["project_id"], "title_zh": p["title_zh"], "audio_version": version,
                    "voices": voices, "rates": rates, "disclosure": disclosure,
                    "episodes": eps})
    record = {"schema_version": 1, "project_id": p["project_id"], "project_fingerprint": fingerprint(p),
              "input_project_sha256": sha(project_path), "source_assets": {rel: sha(src) for rel, src in assets.items()},
              "counts": {"chapters": len(p["chapters"]), "units": sum(len(c["units"]) for c in p["chapters"]),
                         "formulas": len(p.get("formulas", [])), "visuals": len(p.get("visuals", [])),
                         "terms": len(terms), "episodes": len(eps)}}
    write_json(stage / "build.json", record)
    print(json.dumps(record["counts"], ensure_ascii=False)); return record

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project", required=True); ap.add_argument("--stage", required=True); ap.add_argument("--sources-root", required=True)
    a = ap.parse_args(); build(a.project, a.stage, a.sources_root)
if __name__ == "__main__": main()
