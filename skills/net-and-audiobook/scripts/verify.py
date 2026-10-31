#!/usr/bin/env python3
"""Verify source integrity, traceability, exact speech plans, audio and downloadable packages."""
from __future__ import annotations
import argparse, io, json, re, subprocess, zipfile
from pathlib import Path
from common import *

def package(stage, c):
    files = {}; playlist = ["#EXTM3U"]
    for ep in c["episodes"]:
        for rel in (ep["audio"], f"scripts/{ep['id']}.txt", f"scripts/{ep['id']}.plan.json"):
            files[rel] = under(stage / "audiobook", rel).read_bytes()
        playlist += [f"#EXTINF:{round(ep['duration_seconds'])},{ep['title_zh']}", ep["audio"]]
    files["PLAYLIST.m3u8"] = ("\n".join(playlist) + "\n").encode("utf-8-sig")
    files["README_PHONE.txt"] = ("这些音频使用合成语音。\n下载 ZIP 并完整解压，用手机音乐或有声书播放器打开 audio 文件夹中的 MP3。\n"
        "建议 1× 播放：英文短语和拼写已在合成时放慢。PLAYLIST.m3u8 可选，播放器是否支持取决于应用。\n"
        "网页离线使用：保存完整网站，或先在支持的浏览器通过本地 HTTP 服务打开。网页缓存不代替 MP3 下载。\n").encode()
    checksums = {rel: hashlib.sha256(data).hexdigest() for rel, data in files.items()}
    files["CHECKSUMS.json"] = json_bytes(checksums)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for rel, data in sorted(files.items()):
            entry = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0)); entry.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(entry, data)
    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as z:
        if z.testzip(): raise ValueError("ZIP CRC failed")
        for rel, digest in checksums.items():
            if hashlib.sha256(z.read(rel)).hexdigest() != digest: raise ValueError("ZIP hash failed")
    downloads = stage / "audiobook/downloads"; downloads.mkdir(parents=True, exist_ok=True)
    atomic_write(downloads / "audiobook.zip", buffer.getvalue())
    external = [line if line.startswith("#") else "../" + line for line in playlist]
    atomic_write(downloads / "audiobook.m3u8", ("\n".join(external) + "\n").encode("utf-8-sig"))
    atomic_write(downloads / "README_PHONE.txt", files["README_PHONE.txt"])
    write_json(downloads / "CHECKSUMS.json", checksums)
    c["bundle_ready"] = True; catalog(stage, c)

def verify(stage, audio=False, make_package=False):
    stage = Path(stage).resolve(); p = validate_project(read_json(stage / "project.json")); b = read_json(stage / "build.json")
    errors, warnings = [], []
    def check(yes, message):
        if not yes: errors.append(message)
    check(fingerprint(p) == b["project_fingerprint"], "Stage project fingerprint changed")
    js = (stage / "project.js").read_text(encoding="utf-8")
    check(js == "window.LEARNING_PROJECT=" + json.dumps(p, ensure_ascii=False) + ";\n", "project.js does not match reviewed data")
    for rel, digest in b["source_assets"].items():
        f = under(stage, "sources/" + rel); check(f.is_file() and sha(f) == digest, "Source asset changed: " + rel)
    for s in p["sources"]:
        f = under(stage, "sources/" + s["path"]); check(f.is_file() and sha(f) == s["sha256"], "Source SHA mismatch: " + s["id"])
        if f.suffix.lower() == ".pdf":
            import pymupdf
            with pymupdf.open(f) as doc: check(len(doc) == s["pages"], "Source PDF page count mismatch: " + s["id"])
    c = read_json(stage / "audiobook/catalog.json")
    check(c["project_id"] == p["project_id"], "Catalog project mismatch")
    check(c.get("audio_version") == fingerprint(p)[:16], "Catalog version mismatch")
    expected_episodes = {e["id"]: e for e in p["episodes"]}
    check((stage / "audiobook/catalog.js").read_text(encoding="utf-8") == "window.AUDIOBOOK_CATALOG=" + json.dumps(c, ensure_ascii=False, allow_nan=False) + ";\n", "Catalog JS/JSON differ")
    terms = {t["id"]: t for t in p["terms"]}; total_segments = 0; audio_stats = []
    check([e["id"] for e in c["episodes"]] == [e["id"] for e in p["episodes"]], "Episode order differs")
    for ep in c["episodes"]:
        source_episode = expected_episodes.get(ep["id"], {})
        check(all(ep.get(k) == source_episode.get(k) for k in ("id", "title_zh", "title_en", "term_ids", "chapter_ids")), "Catalog episode mapping differs: " + ep["id"])
        check(ep["term_count"] == len(source_episode.get("term_ids", [])), "Catalog term count differs: " + ep["id"])
        plan = read_json(under(stage, f"audiobook/scripts/{ep['id']}.plan.json"))
        expected_terms = [{**terms[t], "segments": segments(terms[t], p.get("speech"))} for t in ep["term_ids"]]
        check(plan["terms"] == expected_terms, "Speech plan changed: " + ep["id"])
        transcript = "\n\n\n".join("\n\n".join(s["text"] for s in t["segments"]) for t in expected_terms) + "\n"
        check(under(stage, f"audiobook/scripts/{ep['id']}.txt").read_text(encoding="utf-8") == transcript, "Transcript differs: " + ep["id"])
        if not audio: continue
        path = under(stage / "audiobook", ep["audio"])
        if not ep.get("ready") or not path.is_file(): errors.append("Missing completed audio: " + ep["id"]); continue
        check(sha(path) == ep.get("sha256"), "MP3 checksum mismatch: " + ep["id"])
        import numpy as np
        from synthesize import decode, read_probe
        info = read_probe(path); duration = float(info["format"]["duration"]); stream = info["streams"][0]
        check(stream.get("codec_name") == "mp3" and int(stream.get("sample_rate", 0)) == 48000 and stream.get("channels") == 1, "MP3 format mismatch: " + ep["id"])
        check(abs(duration - ep["duration_seconds"]) < .1, "Catalog duration mismatch: " + ep["id"])
        x = decode(path); clipping = float(np.mean(np.abs(x) >= .999)); peak = float(np.max(np.abs(x)))
        check(np.isfinite(x).all() and clipping < .0001 and .005 < peak < 1.01, "Silent/clipped/nonfinite audio: " + ep["id"])
        rows = read_json(under(stage, f"audiobook/segment_metrics/{ep['id']}.json")); expected = [(t, s) for t in expected_terms for s in t["segments"]]
        check(len(rows) == len(expected), "Segment count mismatch: " + ep["id"]); total_segments += len(rows)
        cursor = 0
        for i, (row, (term, seg)) in enumerate(zip(rows, expected)):
            label = f"{ep['id']}:{term['id']}:{seg['kind']}"
            check(all(row.get(k) == seg[k] for k in ("kind", "text", "rate", "voice")), "Speech request differs: " + label)
            check(row.get("term_id") == term["id"] and row.get("native_synthesis") is True and row.get("time_stretch") is False, "Wrong term/engine: " + label)
            gap = 0 if i == len(expected) - 1 else seg["gap_after"]
            check(abs(row["start_seconds"] - cursor) < .01 and row["gap_after"] == gap, "Segment boundary/gap mismatch: " + label)
            cursor += row["duration_seconds"] + gap
            last = max((b["offset"] + b["duration"] for b in row.get("word_boundaries", [])), default=0) / 1e7
            check(last > 0 and last - row["trimmed_head_seconds"] <= row["duration_seconds"] + .15, "Truncated boundary: " + label)
            if seg["kind"] == "spelling":
                letters = "".join(words(seg["text"])).upper()
                observed = [re.sub(r"[^A-Za-z]", "", b["text"]).upper() for b in row["word_boundaries"]]
                check(row.get("letters") == letters and "".join(observed) == letters and all(len(b) == 1 for b in observed), "Incomplete spelling: " + label)
            if seg["kind"] in ("standard_zh", "plain_zh") and not 2 <= row.get("chinese_chars_per_second", 0) <= 7:
                warnings.append("Review Chinese pacing: " + label)
        check(abs(cursor - duration) < .2, "Episode/segment duration mismatch: " + ep["id"])
        audio_stats.append({"id": ep["id"], "duration_seconds": duration, "peak": peak, "clipping_fraction": clipping})
    if make_package:
        if not audio or errors: raise ValueError("Packaging requires complete passing --audio verification")
        package(stage, c)
    if c.get("bundle_ready"):
        with zipfile.ZipFile(stage / "audiobook/downloads/audiobook.zip") as z:
            check(z.testzip() is None, "ZIP CRC error")
            checks = json.loads(z.read("CHECKSUMS.json"))
            for rel, digest in checks.items(): check(hashlib.sha256(z.read(rel)).hexdigest() == digest, "ZIP payload differs: " + rel)
    report = {"schema_version": 1, "project_id": p["project_id"], "project_fingerprint": fingerprint(p),
              "audio_checked": audio, "errors": errors, "warnings": warnings, "counts": b["counts"], "segments": total_segments,
              "audio": audio_stats, "listening": "not_performed_by_automated_verification",
              "limitations": ["Checksums, decode and boundaries do not certify pronunciation or naturalness.", "Source interpretation and formula equivalence require human/agent source comparison."],
              "delivery_hashes": delivery_hashes(stage)}
    write_json(stage / "qa-report.json", report)
    print(json.dumps({"errors": errors, "warnings": warnings, "counts": b["counts"], "audio_checked": audio}, ensure_ascii=False)); return report

def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument("--stage", required=True); ap.add_argument("--audio", action="store_true"); ap.add_argument("--package", action="store_true"); a = ap.parse_args()
    raise SystemExit(1 if verify(a.stage, a.audio, a.package)["errors"] else 0)
if __name__ == "__main__": main()
