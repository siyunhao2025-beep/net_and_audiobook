"""Shared, dependency-free contracts for the learning-site toolchain (Python 3.10+)."""
from __future__ import annotations
import hashlib, json, os, re, time, unicodedata
from pathlib import Path, PurePosixPath
import xml.etree.ElementTree as ET

KINDS = ("term_zh", "term_en", "spelling", "standard_zh", "plain_zh")
RATES = dict(zip(KINDS, ("-8%", "-30%", "-20%", "-3%", "-3%")))
GAPS = dict(zip(KINDS, (.60, .85, 1.00, .90, 1.50)))
VOICES = {"zh": "zh-CN-XiaoxiaoNeural", "en": "en-US-JennyNeural"}
ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,79}$")

def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))

def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1048576), b""): h.update(b)
    return h.hexdigest()

def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode()

def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()

def atomic_write(path, data, *, expected=None):
    """Owned stage files only; retain a valid .part on interrupted Windows fallback.

    expected is a compare-and-swap digest; use 'absent' for a new destination.
    The publisher checks/backs up production separately. Never use this to edit sources.
    """
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    def check():
        actual = sha(path) if path.exists() else "absent"
        if expected is not None and actual != expected:
            raise RuntimeError(f"Concurrent change: {path.name}")
    check()
    tmp = path.with_name(path.name + ".part")
    with tmp.open("wb") as f: f.write(data); f.flush(); os.fsync(f.fileno())
    for n in range(5):
        check()
        try: os.replace(tmp, path); return
        except PermissionError:
            if n < 4: time.sleep(.1 * (n + 1))
    # Some Windows preview/read handles allow write, but deny rename/delete.
    # Recheck immediately, write in place, and verify. Caller retains an original backup.
    check()
    with path.open("r+b" if path.exists() else "wb") as f:
        f.seek(0); f.write(data); f.truncate(); f.flush(); os.fsync(f.fileno())
    if path.read_bytes() != data: raise OSError("Write verification failed; .part retained")
    tmp.unlink(missing_ok=True)

def write_json(path, value, **kw): atomic_write(path, json_bytes(value), **kw)

def safe_rel(value):
    if not isinstance(value, str) or not value or "\\" in value or re.search(r"[:?#\x00-\x1f]", value):
        raise ValueError(f"Unsafe relative path: {value!r}")
    p = PurePosixPath(value)
    if p.is_absolute() or any(x in (".", "..") for x in value.split("/")) or "" in value.split("/"):
        raise ValueError(f"Unsafe relative path: {value!r}")
    for part in value.split("/"):
        if part.endswith((" ", ".")) or re.fullmatch(r"(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])", part.split(".")[0], re.I):
            raise ValueError("Path is not portable to Windows: " + value)
    return p.as_posix()

def under(root, relative):
    root = Path(root).resolve(); p = root / safe_rel(relative)
    if not p.resolve().is_relative_to(root): raise ValueError("Path leaves root (possibly a symlink)")
    # Do not follow even an inward symlink; publishing must never mutate its referent.
    if any(q.is_symlink() for q in (p, *p.parents) if q != root and q.is_relative_to(root)):
        raise ValueError("Symlinks are not allowed in build/publication paths")
    return p

def outside(out, roots):
    out = Path(out).resolve()
    for root in roots:
        root = Path(root).resolve()
        if out == root or out.is_relative_to(root): raise ValueError("Output must be outside every input root")
    return out

def words(text):
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.findall(r"[A-Za-z]+", normalized)

def spelling(text): return ". ".join(", ".join(w.upper()) for w in words(text)) + "."

def plain_cue(text):
    return "通俗地说，" + re.sub(r"^(?:通俗[地的]说[，,。：:]?\s*)+", "", text).strip()

def segments(term, speech=None):
    speech = speech or {}; rates = {**RATES, **speech.get("rates", {})}
    voices = {**VOICES, **speech.get("voices", {})}
    texts = {"term_zh": term["zh"], "term_en": term["en"], "spelling": spelling(term.get("spell_as", term["en"])),
             "standard_zh": term["standard_zh"], "plain_zh": plain_cue(term["plain_zh"])}
    return [{"kind": k, "text": texts[k], "rate": rates[k],
             "voice": voices["en" if k in ("term_en", "spelling") else "zh"],
             "gap_after": GAPS[k]} for k in KINDS]

MATH_TAGS = set("math mrow mi mn mo mtext mspace mfrac msqrt mroot msub msup msubsup munder mover munderover mfenced mtable mtr mtd mstyle mpadded mphantom menclose semantics annotation".split())
MATH_ATTRS = set("display mathvariant stretchy fence separator accent accentunder lspace rspace columnalign rowalign columnspacing rowspacing width height depth notation open close separators linethickness encoding".split())

def mathml(text):
    if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", text): raise ValueError("Control character in formula")
    if "<!" in text or "<?" in text: raise ValueError("Declarations/entities are not allowed in MathML")
    root = ET.fromstring(text)
    if root.tag.rsplit("}", 1)[-1] != "math": raise ValueError("Expected MathML math root")
    for node in root.iter():
        if node.tag.startswith("{") and not node.tag.startswith("{http://www.w3.org/1998/Math/MathML}"):
            raise ValueError("Foreign namespace in MathML")
        tag = node.tag.rsplit("}", 1)[-1]
        if tag not in MATH_TAGS: raise ValueError("Disallowed MathML element: " + tag)
        if set(node.attrib) - MATH_ATTRS: raise ValueError("Disallowed MathML attribute")
        if any(re.search(r"url\s*\(|javascript:|data:", v, re.I) for v in node.attrib.values()):
            raise ValueError("Active content in MathML")
        node.tag = tag
    root.set("xmlns", "http://www.w3.org/1998/Math/MathML")
    return ET.tostring(root, encoding="unicode")

def validate_project(p):
    if p.get("schema_version") != 1: raise ValueError("Unsupported project schema_version")
    if not ID.fullmatch(p.get("project_id", "")): raise ValueError("Invalid project_id")
    if not p.get("title_zh"): raise ValueError("Missing title_zh")
    sources = {s["id"]: s for s in p.get("sources", [])}
    if len(sources) != len(p.get("sources", [])): raise ValueError("Duplicate source ID")
    for s in sources.values():
        if not ID.fullmatch(s["id"]): raise ValueError("Invalid source ID")
        safe_rel(s["path"])
        if not re.fullmatch(r"[a-f0-9]{64}", s.get("sha256", "")): raise ValueError("Missing source SHA256")
        if not isinstance(s.get("pages"), int) or s["pages"] < 1: raise ValueError("Invalid source page count")
    def refs(item):
        if not item.get("source_refs"): raise ValueError("Missing source_refs: " + item.get("id", "question"))
        for r in item["source_refs"]:
            s = sources.get(r.get("source_id")); page = r.get("page")
            if not s or not isinstance(page, int) or not 1 <= page <= s["pages"]: raise ValueError("Invalid source reference")
    all_ids = set()
    def identifier(item):
        i = item.get("id", "")
        if not ID.fullmatch(i) or i in all_ids: raise ValueError("Invalid or duplicate ID: " + i)
        all_ids.add(i)
    if not p.get("chapters"): raise ValueError("At least one chapter is required")
    unit_ids = set(); chapter_ids = set()
    for ch in p["chapters"]:
        identifier(ch); chapter_ids.add(ch["id"])
        if not ch.get("title_zh") or not ch.get("units"): raise ValueError("Empty chapter")
        for u in ch["units"]:
            identifier(u); refs(u); unit_ids.add(u["id"])
            if not all(u.get(k) for k in ("title_zh", "plain_zh", "standard_zh", "plain_en", "standard_en")): raise ValueError("Incomplete bilingual learning unit")
            if u.get("english") and u.get("english_role") not in ("source", "translation", "explanation"):
                raise ValueError("English needs source/translation/explanation role")
        if not 2 <= len(ch.get("questions", [])) <= 3: raise ValueError("Each chapter needs 2–3 questions")
        for q in ch["questions"]:
            refs(q)
            if not all(q.get(k) for k in ("zh", "en", "answer_zh", "answer_en")): raise ValueError("Incomplete bilingual question")
    for f in p.get("formulas", []):
        identifier(f); refs(f)
        if re.search(r"[\x00-\x1f]", f.get("latex", "")): raise ValueError("Escaped control character in LaTeX")
        if not f.get("source_image"): raise ValueError("Formula needs a source crop for comparison")
        safe_rel(f["source_image"])
        if f.get("mathml"): mathml(f["mathml"])
        elif not f.get("display_image"): raise ValueError("Formula needs MathML or a verified display image")
        if f.get("display_image"): safe_rel(f["display_image"])
        if f.get("verified") is not True: raise ValueError("Formula must be visually source-verified")
    for v in p.get("visuals", []):
        identifier(v); refs(v); safe_rel(v["path"])
        if not all(v.get(k) for k in ("caption_zh", "caption_en", "read_zh", "watch_zh")):
            raise ValueError("Visual needs bilingual caption, reading guide and caveat")
    term_ids = set()
    for t in p.get("terms", []):
        identifier(t); refs(t); term_ids.add(t["id"])
        if not all(t.get(k) for k in ("zh", "en", "standard_zh", "plain_zh")): raise ValueError("Incomplete term")
        if not words(t.get("spell_as", t["en"])): raise ValueError("No English spelling letters")
        if t.get("spell_as") and not re.fullmatch(r"[A-Za-z\s.'’()/-]+", t["spell_as"]):
            raise ValueError("spell_as must explicitly express symbols/numbers as English words")
        if re.search(r"[^A-Za-z\s.'’()/-]", t["en"]) and not t.get("spell_as"):
            raise ValueError("Non-letter term needs explicit spell_as (e.g. digits, Greek symbols)")
        for seg in segments(t, p.get("speech")):
            text = seg["text"]; kind = seg["kind"]
            if re.search(r"PPT|中文是|英文是|来自于|第\s*[\d一二三四五六七八九十]+\s*页|[=<>∂∇Σ√$\\]", text, re.I):
                raise ValueError("Forbidden spoken formula/label/source reference: " + t["id"])
            if kind in ("standard_zh", "plain_zh") and re.search(r"[A-Za-z]", text):
                raise ValueError("Audio explanations must be Chinese only: " + t["id"])
    covered = []
    for e in p.get("episodes", []):
        identifier(e)
        if not e.get("term_ids") or not e.get("title_zh"): raise ValueError("Empty episode")
        if any(i not in term_ids for i in e["term_ids"]): raise ValueError("Unknown episode term")
        if any(i not in chapter_ids for i in e.get("chapter_ids", [])): raise ValueError("Unknown episode chapter")
        if len(set(e["term_ids"])) != len(e["term_ids"]): raise ValueError("Duplicate term within episode")
        covered += e["term_ids"]
    if set(covered) != term_ids: raise ValueError("Episodes must cover all glossary terms")
    fids = {x["id"] for x in p.get("formulas", [])}; vids = {x["id"] for x in p.get("visuals", [])}
    for ch in p["chapters"]:
        for u in ch["units"]:
            if set(u.get("formula_ids", [])) - fids or set(u.get("visual_ids", [])) - vids:
                raise ValueError("Unknown unit formula/visual")
    timer = p.get("ui", {}).get("timer", {})
    for key in ("focus_minutes", "break_minutes"):
        if key in timer and (not isinstance(timer[key], (int, float)) or not 0 < timer[key] <= 120):
            raise ValueError("Invalid timer duration")
    speech = p.get("speech", {})
    if set(speech.get("rates", {})) - set(KINDS) or set(speech.get("voices", {})) - set(VOICES):
        raise ValueError("Unknown speech setting")
    for value in speech.get("rates", {}).values():
        if not re.fullmatch(r"[+-]\d{1,2}%", value): raise ValueError("Invalid native speech rate")
    return p

def catalog(stage, value):
    write_json(Path(stage) / "audiobook/catalog.json", value)
    atomic_write(Path(stage) / "audiobook/catalog.js", ("window.AUDIOBOOK_CATALOG=" +
                  json.dumps(value, ensure_ascii=False, allow_nan=False) + ";\n").encode())

def delivery_hashes(stage):
    stage = Path(stage).resolve(); result = {}
    for f in sorted(stage.rglob("*")):
        rel = f.relative_to(stage).as_posix()
        if rel.split("/")[0] == "_work" or rel in ("qa-report.json", "browser-report.json"): continue
        if f.is_symlink(): raise ValueError("Symlink in delivery")
        if f.is_file():
            if f.name.endswith((".part", ".pending.mp3", ".tmp")): raise ValueError("Unfinished file in delivery: " + rel)
            result[rel] = sha(f)
    return result
