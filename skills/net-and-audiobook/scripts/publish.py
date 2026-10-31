#!/usr/bin/env python3
"""Prepare a reviewable publication, then apply with backups and compare-and-swap checks."""
from __future__ import annotations
import argparse, shutil, time
from pathlib import Path
from common import *

def sealed(stage, web_only=False):
    qa = read_json(stage / "qa-report.json"); browser = read_json(stage / "browser-report.json")
    hashes = delivery_hashes(stage)
    if qa.get("errors") or qa.get("delivery_hashes") != hashes: raise ValueError("Structural QA missing, failed or stale")
    if browser.get("errors") or browser.get("delivery_hashes") != hashes: raise ValueError("Browser QA missing, failed or stale")
    if browser.get("transports") != ["http", "file"] or browser.get("widths") != [1280, 390]:
        raise ValueError("Require desktop/mobile and HTTP/file browser checks")
    if {x.get("case") for x in browser.get("checks", []) if x.get("passed") is True} != {f"{t}:{w}" for t in ("http", "file") for w in (1280, 390)}:
        raise ValueError("Browser matrix is incomplete")
    p = read_json(stage / "project.json")
    if p.get("episodes") and not web_only and (not qa.get("audio_checked") or not browser.get("audio_checked")):
        raise ValueError("Complete audio QA required; use --web-only only for an explicitly requested web-only release")
    return hashes

def prepare(stage, target, journal, source_roots=(), web_only=False):
    stage, target, journal = (Path(x).resolve() for x in (stage, target, journal))
    if stage == target or stage.is_relative_to(target) or target.is_relative_to(stage): raise ValueError("Stage and target must be separate")
    outside(target, source_roots); outside(journal, [stage, target, *source_roots])
    if journal.exists() and any(journal.iterdir()): raise ValueError("Use a new empty journal")
    hashes = sealed(stage, web_only); journal.mkdir(parents=True, exist_ok=True)
    original = {}
    for rel in hashes:
        dst = under(target, rel)
        if dst.exists() and not dst.is_file(): raise ValueError("Destination is not a file: " + rel)
        original[rel] = sha(dst) if dst.exists() else "absent"
        if dst.exists():
            backup = under(journal, "backup/" + rel); backup.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(dst, backup)
            if sha(backup) != original[rel]: raise RuntimeError("Source changed while backing up: " + rel)
    intent = {"schema_version": 1, "status": "prepared", "stage": str(stage), "target": str(target),
              "created_at": time.time(), "new": hashes, "original": original, "completed": [], "web_only": web_only}
    write_json(journal / "intent.json", intent)
    print(json.dumps({"status": "prepared", "files": len(hashes), "backed_up": sum(x != "absent" for x in original.values())})); return intent

def apply(journal):
    journal = Path(journal).resolve(); intent = read_json(journal / "intent.json")
    stage, target = Path(intent["stage"]), Path(intent["target"])
    if intent["status"] == "rolled_back": raise ValueError("This release was rolled back; prepare a fresh journal")
    if sealed(stage, intent.get("web_only", False)) != intent["new"]: raise ValueError("Staged release changed")
    # Validate the entire target before any mutation. A previous partial run may contain new files.
    for rel, digest in intent["new"].items():
        dst = under(target, rel); current = sha(dst) if dst.exists() else "absent"
        if current not in (digest, intent["original"][rel]): raise RuntimeError("Concurrent/unrecognized target change: " + rel)
    intent["status"] = "publishing"; write_json(journal / "intent.json", intent)
    for rel, digest in intent["new"].items():
        dst = under(target, rel)
        if dst.exists() and sha(dst) == digest: continue
        intent["writing"] = rel; write_json(journal / "intent.json", intent)
        atomic_write(dst, under(stage, rel).read_bytes(), expected=intent["original"][rel])
        if sha(dst) != digest: raise OSError("Published checksum failed: " + rel)
        intent["completed"] = sorted(set(intent["completed"]) | {rel}); write_json(journal / "intent.json", intent)
    intent.pop("writing", None); intent["status"] = "published"; write_json(journal / "intent.json", intent)
    print("PUBLISHED", len(intent["new"]), "verified files"); return intent

def rollback(journal):
    journal = Path(journal).resolve(); intent = read_json(journal / "intent.json"); target = Path(intent["target"])
    for rel, digest in intent["new"].items():
        dst = under(target, rel); current = sha(dst) if dst.exists() else "absent"
        if current not in (digest, intent["original"][rel]): raise RuntimeError("Concurrent change blocks rollback: " + rel)
        if intent["original"][rel] != "absent" and sha(under(journal, "backup/" + rel)) != intent["original"][rel]:
            raise ValueError("Backup checksum mismatch: " + rel)
    intent["status"] = "rolling_back"; write_json(journal / "intent.json", intent)
    for rel, digest in intent["new"].items():
        dst = under(target, rel)
        if not dst.exists() or sha(dst) == intent["original"][rel]: continue
        if intent["original"][rel] == "absent": dst.unlink()
        else: atomic_write(dst, under(journal, "backup/" + rel).read_bytes(), expected=digest)
    intent["status"] = "rolled_back"; write_json(journal / "intent.json", intent); print("ROLLED_BACK; backups retained")

def main():
    ap = argparse.ArgumentParser(description=__doc__); sub = ap.add_subparsers(dest="action", required=True)
    first = sub.add_parser("prepare"); first.add_argument("--stage", required=True); first.add_argument("--target", required=True); first.add_argument("--journal", required=True); first.add_argument("--source-root", action="append", required=True); first.add_argument("--web-only", action="store_true")
    for verb in ("apply", "rollback"): sub.add_parser(verb).add_argument("--journal", required=True)
    a = ap.parse_args()
    if a.action == "prepare": prepare(a.stage, a.target, a.journal, a.source_root, a.web_only)
    elif a.action == "apply": apply(a.journal)
    else: rollback(a.journal)
if __name__ == "__main__": main()
