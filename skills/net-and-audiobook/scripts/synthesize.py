#!/usr/bin/env python3
"""Native Mandarin/US-English glossary synthesis with hashed cache and safe pause/resume."""
from __future__ import annotations
import argparse, asyncio, contextlib, os, re, subprocess, time
from pathlib import Path
from common import *

SR = 24000
ENGINE = "native-glossary-1"

class Paused(Exception): pass

def check_pause(stage):
    if (stage / "_work/PAUSED_BY_USER.json").exists(): raise Paused("Paused by user")

def ffprobe(path):
    return read_probe(path)["format"]

def read_probe(path):
    import json
    return json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)], text=True, encoding="utf-8"))

def decode(path):
    import numpy as np
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ar", str(SR), "-ac", "1", "-f", "f32le", "pipe:1"], capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype="<f4").copy()

def trim(raw, boundaries):
    import numpy as np
    audible = np.flatnonzero(np.abs(raw) > 10 ** (-58 / 20))
    if not len(audible): raise ValueError("Silent synthesis")
    start = max(0, int(audible[0]) - round(.12 * SR)); end = min(len(raw), int(audible[-1]) + round(.22 * SR) + 1)
    if boundaries:
        first = min(b["offset"] for b in boundaries) / 1e7
        last = max(b["offset"] + b["duration"] for b in boundaries) / 1e7
        if last > len(raw) / SR + .15: raise ValueError("Incomplete raw utterance")
        start = min(start, max(0, round((first - .12) * SR)))
        end = max(end, min(len(raw), round((last + .22) * SR)))
    return raw[start:end], start / SR

class Renderer:
    def __init__(self, stage, cache, jobs, proxy):
        self.stage, self.cache, self.proxy = stage, cache, proxy
        self.semaphore = asyncio.Semaphore(jobs); self.inflight = {}
        cache.mkdir(parents=True, exist_ok=True)

    async def raw(self, text, voice, rate):
        payload = {"text": text, "voice": voice, "rate": rate, "pitch": "+0Hz", "boundary": "WordBoundary", "engine": ENGINE}
        key = fingerprint(payload)
        if key not in self.inflight: self.inflight[key] = asyncio.create_task(self.fetch(key, payload))
        return await self.inflight[key]

    async def fetch(self, key, payload):
        import edge_tts
        p, j = self.cache / (key + ".mp3"), self.cache / (key + ".json")
        if p.exists() and j.exists():
            meta = read_json(j)
            if meta.get("sha256") == sha(p) and meta.get("request") == payload: return p, meta
        async with self.semaphore:
            check_pause(self.stage)
            for attempt in range(4):
                try:
                    check_pause(self.stage)
                    request = edge_tts.Communicate(payload["text"], voice=payload["voice"], rate=payload["rate"],
                        pitch="+0Hz", boundary="WordBoundary", proxy=self.proxy, connect_timeout=15, receive_timeout=40)
                    chunks, boundaries = [], []
                    async for c in request.stream():
                        if c["type"] == "audio": chunks.append(c["data"])
                        elif c["type"] == "WordBoundary": boundaries.append(c)
                    data = b"".join(chunks)
                    if len(data) < 600 or not boundaries: raise ValueError("Missing audio/word boundaries")
                    atomic_write(p, data)
                    meta = {"request": payload, "sha256": sha(p), "cache_key": key, "word_boundaries": boundaries}
                    write_json(j, meta); return p, meta
                except Paused: raise
                except Exception:
                    if attempt == 3: raise
                    await asyncio.sleep(1.5 * (attempt + 1))

    async def segment(self, seg):
        import numpy as np
        spoken = seg["text"]
        if seg["kind"] == "term_en": spoken = re.sub(r"[-–—]", " ", spoken).strip().rstrip(".") + "."
        elif seg["kind"] != "spelling" and not re.search(r"[。！？]$", spoken): spoken += "。"
        path, meta = await self.raw(spoken, seg["voice"], seg["rate"])
        raw = await asyncio.to_thread(decode, path); x, cut = trim(raw, meta["word_boundaries"])
        if not np.isfinite(x).all() or np.max(np.abs(x)) < .005: raise ValueError("Invalid/inaudible segment")
        row = {**seg, "spoken_text": spoken, "native_synthesis": True, "time_stretch": False,
               "cache_key": meta["cache_key"], "raw_sha256": meta["sha256"], "raw_duration_seconds": len(raw) / SR,
               "trimmed_head_seconds": cut, "duration_seconds": len(x) / SR, "word_boundaries": meta["word_boundaries"]}
        if seg["kind"] == "spelling":
            expected = "".join(words(seg["text"])).upper()
            observed = [re.sub(r"[^A-Za-z]", "", b["text"]).upper() for b in meta["word_boundaries"]]
            if "".join(observed) != expected or not all(len(x) == 1 for x in observed):
                raise ValueError("Spelling boundaries omit/merge letters")
            row.update(letters=expected, spelling_as_single_native_utterance=True)
        if seg["kind"] in ("standard_zh", "plain_zh"):
            row["chinese_chars_per_second"] = len(re.findall(r"[\u3400-\u9fff]", seg["text"])) / max(.01, len(x) / SR)
        peak = float(np.max(np.abs(x)))
        if peak > .96: x *= .96 / peak
        return x, row

async def run(stage, cache, jobs, proxy, sample=False):
    import numpy as np, soundfile as sf
    p = validate_project(read_json(stage / "project.json")); b = read_json(stage / "build.json")
    if fingerprint(p) != b["project_fingerprint"]: raise ValueError("Stage project changed; build a new stage")
    c = read_json(stage / "audiobook/catalog.json"); check_pause(stage)
    if c.get("audio_version") != fingerprint(p)[:16] or c.get("project_id") != p["project_id"]:
        raise ValueError("Catalog version/project changed")
    if len(c["episodes"]) != len(p["episodes"]) or any(any(e.get(k) != src.get(k) for k in ("id", "title_zh", "title_en", "term_ids", "chapter_ids")) for e, src in zip(c["episodes"], p["episodes"])):
        raise ValueError("Catalog episode mapping changed")
    r = Renderer(stage, cache, jobs, proxy)
    report_path = stage / "_work/synthesis.json"
    report = read_json(report_path) if report_path.exists() else {"engine": ENGINE, "episodes": {}}
    terms = {t["id"]: t for t in p["terms"]}
    for e in c["episodes"][:1] if sample else c["episodes"]:
        check_pause(stage); plan = read_json(stage / "audiobook/scripts" / (e["id"] + ".plan.json"))
        expected = [{**terms[t], "segments": segments(terms[t], p.get("speech"))} for t in e["term_ids"]]
        if plan["terms"] != expected: raise ValueError("Plan changed; rebuild from reviewed project data")
        plan_fp = fingerprint({"plan": plan, "engine": ENGINE})
        dest = stage / "audiobook" / e["audio"]
        previous = report["episodes"].get(e["id"], {})
        if not sample and previous.get("plan_fingerprint") == plan_fp and dest.exists() and sha(dest) == previous.get("sha256"):
            e.update(previous["catalog_fields"]); catalog(stage, c); print("RESUME_SKIP", e["id"], flush=True); continue
        selected = plan["terms"][:1] if sample else plan["terms"]
        flat = [(t, s) for t in selected for s in t["segments"]]
        print("START", e["id"], len(selected), "terms", flush=True)
        rendered = await asyncio.gather(*(r.segment(s) for _, s in flat), return_exceptions=True)
        # Finish already active requests into the cache, then stop before assembling an episode.
        check_pause(stage)
        for item in rendered:
            if isinstance(item, BaseException): raise item
        parts, rows, cursor = [], [], 0
        for i, ((term, seg), (x, row)) in enumerate(zip(flat, rendered)):
            row.update(term_id=term["id"], start_seconds=cursor / SR)
            parts.append(x); cursor += len(x); gap = 0 if i == len(flat) - 1 else seg["gap_after"]
            row["gap_after"] = gap
            if gap: z = np.zeros(round(gap * SR), dtype=np.float32); parts.append(z); cursor += len(z)
            rows.append(row)
        work = stage / "_work"; work.mkdir(exist_ok=True)
        wav = work / (e["id"] + ".wav"); sf.write(wav, np.concatenate(parts), SR, subtype="PCM_16")
        if sample: dest = stage / "audiobook/samples/native-demo.mp3"
        dest.parent.mkdir(parents=True, exist_ok=True); part = dest.with_suffix(".pending.mp3")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-af", "loudnorm=I=-18:TP=-2:LRA=7", "-ar", "48000", "-ac", "1", "-b:a", "128k", "-metadata", "title=" + e["title_zh"], str(part)], check=True)
        check_pause(stage); atomic_write(dest, part.read_bytes()); part.unlink(); wav.unlink()
        duration = float(ffprobe(dest)["duration"])
        fields = {"sha256": sha(dest), "file_size": dest.stat().st_size, "duration_seconds": round(duration, 3), "ready": True}
        if sample:
            write_json(stage / "audiobook/samples/native-demo.json", {"terms": [t["id"] for t in selected], "segments": rows, **fields, "listening": "not_performed"})
            print("SAMPLE_READY", str(dest), flush=True); return
        e.update(fields)
        write_json(stage / "audiobook/segment_metrics" / (e["id"] + ".json"), rows)
        report["episodes"][e["id"]] = {"plan_fingerprint": plan_fp, "sha256": fields["sha256"], "catalog_fields": fields}
        write_json(report_path, report); catalog(stage, c)
        write_json(stage / "_work/pipeline.json", {"status": "running", "last_completed": e["id"], "updated_at": time.time()})
        print("DONE", e["id"], duration, flush=True)

def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument("action", choices=("build", "sample", "pause", "resume", "status")); ap.add_argument("--stage", required=True)
    ap.add_argument("--cache"); ap.add_argument("--proxy", default=None); ap.add_argument("--jobs", type=int, default=4); a = ap.parse_args()
    if not 1 <= a.jobs <= 6: ap.error("--jobs must be 1..6")
    stage = Path(a.stage).resolve()
    if not (stage / "build.json").is_file(): ap.error("Not an owned build stage")
    work = stage / "_work"; work.mkdir(exist_ok=True); marker = work / "PAUSED_BY_USER.json"
    if a.action == "pause": write_json(marker, {"requested_at": time.time()}); print("PAUSE_REQUESTED; current requests finish into cache"); return
    if a.action == "status":
        print(json.dumps({"paused": marker.exists(), "pipeline": read_json(work / "pipeline.json") if (work / "pipeline.json").exists() else None})); return
    if a.action == "resume": marker.unlink(missing_ok=True)
    lock = work / "build.lock"
    try: fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    except FileExistsError: ap.error("A build owns this stage. Verify its PID/command before removing a stale _work/build.lock.")
    with os.fdopen(fd, "w") as f: json.dump({"pid": os.getpid(), "started_at": time.time()}, f)
    try:
        asyncio.run(run(stage, Path(a.cache).resolve() if a.cache else work / "tts_cache", a.jobs, a.proxy, a.action == "sample"))
        write_json(work / "pipeline.json", {"status": "sample_ready" if a.action == "sample" else "synthesis_complete", "updated_at": time.time()})
    except Paused:
        write_json(work / "pipeline.json", {"status": "paused", "updated_at": time.time()}); print("PAUSED_SAFE", flush=True)
    except Exception as e:
        write_json(work / "pipeline.json", {"status": "failed", "error_type": type(e).__name__, "updated_at": time.time()}); raise
    finally: lock.unlink(missing_ok=True)
if __name__ == "__main__": main()
