#!/usr/bin/env python3
"""Generate original, tiny demo inputs; contains no user materials or prerecorded speech."""
from __future__ import annotations
import argparse
from pathlib import Path
from common import *

def make(out):
    import pymupdf
    out = Path(out).resolve()
    if out.exists() and any(out.iterdir()): raise ValueError("Use a new empty input directory")
    out.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=500)
    page.insert_text((50, 60), "ORIGINAL WORKFLOW DEMO - NOT A RESEARCH PAPER", fontsize=12)
    page.insert_textbox(pymupdf.Rect(50, 90, 545, 260), "Solar wind is a plasma flow expanding from the solar corona into interplanetary space. It contains charged particles.\n\nFor a separate average-speed illustration, d is distance and t is elapsed time; use compatible units.", fontsize=12)
    page.insert_text((50, 310), "v = d / t", fontsize=24)
    page.get_pixmap(matrix=pymupdf.Matrix(2, 2), clip=pymupdf.Rect(40, 275, 250, 330)).save(out / "speed-source.png")
    page = doc.new_page(width=595, height=500)
    page.insert_textbox(pymupdf.Rect(50, 60, 545, 400), "ORIGINAL WORKFLOW DEMO\n\nThe magnetopause is the boundary between the magnetosphere and the surrounding magnetosheath plasma. It is a plasma boundary, not a solid wall. Its position can change as the surrounding environment changes.", fontsize=12)
    doc.save(out / "demo.pdf"); doc.close()
    template = Path(__file__).resolve().parents[1] / "assets/demo-project.json"
    p = read_json(template); p["sources"][0]["sha256"] = sha(out / "demo.pdf"); validate_project(p)
    write_json(out / "project.json", p); print("DEMO_INPUTS_READY", out); return p

def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument("--out", required=True); a = ap.parse_args(); make(a.out)
if __name__ == "__main__": main()
