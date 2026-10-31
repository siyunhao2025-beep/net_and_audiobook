#!/usr/bin/env python3
"""Offline contract and recovery tests. All generated inputs/targets are temporary."""
from __future__ import annotations
import contextlib, copy, io, json, shutil, sys, tempfile, unittest, zipfile
from pathlib import Path
from unittest import mock
from common import *
from make_demo import make
from build_site import build
from verify import verify
from publish import prepare, apply, rollback
from release_check import scan
from audit_sources import run as audit

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.inputs = self.root / "input"; self.stage = self.root / "stage"
        with contextlib.redirect_stdout(io.StringIO()): self.p = make(self.inputs)

    def build(self):
        with contextlib.redirect_stdout(io.StringIO()): return build(self.inputs / "project.json", self.stage, self.inputs)

    def verify(self):
        with contextlib.redirect_stdout(io.StringIO()): return verify(self.stage)

    def browser_stub(self):
        # A mocked browser report tests the publication contract, never serves as real browser evidence.
        write_json(self.stage / "browser-report.json", {"errors": [], "transports": ["http", "file"], "widths": [1280, 390],
            "checks": [{"case": f"{t}:{w}", "passed": True} for t in ("http", "file") for w in (1280, 390)], "audio_checked": False, "delivery_hashes": delivery_hashes(self.stage)})

    def test_end_to_end_web_and_source_integrity(self):
        before = {f.name: sha(f) for f in self.inputs.iterdir()}
        b = self.build(); self.assertEqual(b["counts"], {"chapters": 2, "units": 2, "formulas": 1, "visuals": 0, "terms": 2, "episodes": 2})
        self.assertFalse(self.verify()["errors"])
        self.assertEqual(before, {f.name: sha(f) for f in self.inputs.iterdir()})
        with self.assertRaises(ValueError): self.build()

    def test_schema_and_spoken_contract(self):
        for mutate in (
            lambda p: p["terms"][0].update(standard_zh="公式 v=1"),
            lambda p: p["terms"][0].update(plain_zh="来自于PPT第1页"),
            lambda p: p["terms"][0].update(standard_zh="Solar wind 是等离子体"),
            lambda p: p["chapters"][0]["units"][0].update(english_role="invented_original"),
            lambda p: p["terms"][0]["source_refs"][0].update(page=999),
            lambda p: p["sources"][0].update(path="../private.pdf"),
            lambda p: p["episodes"][0].update(term_ids=[]),
            lambda p: p["formulas"][0].update(latex="\f rac"),
            lambda p: p["formulas"][0].update(mathml='<math><mi onclick="alert(1)">x</mi></math>'),
        ):
            p = copy.deepcopy(self.p); mutate(p)
            with self.subTest(p=p):
                with self.assertRaises(ValueError): validate_project(p)
        s = segments(self.p["terms"][0]); self.assertEqual([x["kind"] for x in s], list(KINDS))
        self.assertTrue(s[-1]["text"].startswith("通俗地说，")); self.assertEqual(s[1]["rate"], "-30%")
        self.assertEqual(spelling("Solar wind"), "S, O, L, A, R. W, I, N, D.")
        self.assertEqual(plain_cue("通俗的说，通俗地说，太阳"), "通俗地说，太阳")

    def test_reader_update_refreshes_shell_without_resetting_audio(self):
        self.build()
        original_catalog=read_json(self.stage/'audiobook/catalog.json')
        original_sw=(self.stage/'sw.js').read_bytes()
        assets=self.root/'renderer';shutil.copytree(Path(__file__).resolve().parents[1]/'assets/site',assets)
        with (assets/'reading/reader.css').open('a',encoding='utf-8') as stream:stream.write('\n/* new palette */\n')
        second=self.root/'second-stage'
        with mock.patch('build_site.ASSETS',assets),contextlib.redirect_stdout(io.StringIO()):build(self.inputs/'project.json',second,self.inputs)
        self.assertNotEqual(original_sw,(second/'sw.js').read_bytes())
        self.assertEqual(original_catalog['audio_version'],read_json(second/'audiobook/catalog.json')['audio_version'])
        self.assertIn(b'./reading/reader.css',original_sw)

    def test_source_drift_does_not_create_stage(self):
        with (self.inputs / "demo.pdf").open("ab") as f: f.write(b"changed")
        with self.assertRaises(ValueError): self.build()
        self.assertFalse(self.stage.exists())

    def test_output_boundary(self):
        with self.assertRaises(ValueError): build(self.inputs / "project.json", self.inputs / "output", self.inputs)
        self.assertFalse((self.inputs / "output").exists())
        with self.assertRaises(ValueError): audit({"source": self.inputs}, self.inputs / "audit")
        self.assertFalse((self.inputs / "audit").exists())
        for bad in ("../secret", "a/../b", "C:/secret", "a\\b", "https://x", "a//b"):
            with self.subTest(path=bad):
                with self.assertRaises(ValueError): under(self.root, bad)

    def test_formula_allowlist(self):
        ok = '<math xmlns="http://www.w3.org/1998/Math/MathML"><mi>v</mi><mo>=</mo><mn>1</mn></math>'
        self.assertIn("<mi>v</mi>", mathml(ok))
        for bad in ('<math><script>x</script></math>', '<!DOCTYPE math><math/>', '<math href="https://x"/>', '<math><mi xmlns="http://evil.test">x</mi></math>'):
            with self.assertRaises(ValueError): mathml(bad)

    def test_windows_fallback_and_compare_and_swap(self):
        p = self.root / "state.json"; p.write_bytes(b"old"); old = sha(p)
        with mock.patch("common.os.replace", side_effect=PermissionError("sharing violation")), mock.patch("common.time.sleep"):
            atomic_write(p, b"new", expected=old)
        self.assertEqual(p.read_bytes(), b"new"); self.assertFalse(p.with_name(p.name + ".part").exists())
        with self.assertRaises(RuntimeError): atomic_write(p, b"overwrite", expected=old)
        self.assertEqual(p.read_bytes(), b"new")

    @unittest.skipUnless(sys.platform == "win32", "Requires a real Windows sharing handle")
    def test_real_windows_handle_without_share_delete(self):
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]; kernel.CloseHandle.restype = wintypes.BOOL
        p = self.root / "locked-state.json"; p.write_bytes(b"old")
        handle = kernel.CreateFileW(str(p), 0x80000000, 0x1 | 0x2, None, 3, 0x80, None)
        if handle == ctypes.c_void_p(-1).value: raise ctypes.WinError(ctypes.get_last_error())
        try: atomic_write(p, b"new", expected=sha(p))
        finally: kernel.CloseHandle(handle)
        self.assertEqual(p.read_bytes(), b"new")

    def test_qa_detects_asset_and_plan_drift(self):
        self.build(); path = self.stage / "sources/demo.pdf"; path.write_bytes(path.read_bytes() + b"drift")
        self.assertTrue(any("Source" in e for e in self.verify()["errors"]))
        plan = self.stage / "audiobook/scripts/ep-solar-wind.plan.json"; j = read_json(plan); j["terms"][0]["segments"][1]["rate"] = "+10%"; write_json(plan, j)
        self.assertTrue(any("Speech plan changed" in e for e in self.verify()["errors"]))

    def test_publish_backup_cas_resume_and_rollback(self):
        self.build(); self.verify(); self.browser_stub()
        target, journal = self.root / "live", self.root / "journal"; target.mkdir()
        (target / "index.html").write_bytes(b"original-page"); (target / "custom.txt").write_bytes(b"keep-me")
        with contextlib.redirect_stdout(io.StringIO()): prepare(self.stage, target, journal, [self.inputs], web_only=True)
        (target / "index.html").write_bytes(b"concurrent-user-edit")
        with self.assertRaises(RuntimeError): apply(journal)
        self.assertFalse((target / "project.js").exists())
        (target / "index.html").write_bytes(b"original-page")
        # Simulate a partial publication: one destination already contains the exact staged version.
        (target / "app.js").write_bytes((self.stage / "app.js").read_bytes())
        with contextlib.redirect_stdout(io.StringIO()): apply(journal); apply(journal); rollback(journal)
        self.assertEqual((target / "index.html").read_bytes(), b"original-page")
        self.assertEqual((target / "custom.txt").read_bytes(), b"keep-me")
        self.assertFalse((target / "app.js").exists())
        self.assertEqual(read_json(journal / "intent.json")["status"], "rolled_back")

    def test_publish_rejects_missing_or_stale_evidence(self):
        self.build(); self.verify(); self.browser_stub(); (self.stage / "app.js").write_text("changed", encoding="utf-8")
        with self.assertRaises(ValueError): prepare(self.stage, self.root / "live", self.root / "journal", [self.inputs], True)
        self.assertFalse((self.root / "live").exists())

    def test_inventory_reads_every_entry_with_modes(self):
        (self.inputs / "extra.txt").write_text("original notes", encoding="utf-8")
        (self.inputs / "weights.pt").write_bytes(b"not-executable-test-data")
        with zipfile.ZipFile(self.inputs / "sample.zip", "w") as z: z.writestr("note.txt", "original")
        with contextlib.redirect_stdout(io.StringIO()): report = audit({"fixture": self.inputs}, self.root / "audit")
        self.assertFalse(report["errors"]); self.assertEqual(report["files"], 6)
        self.assertIn("model_or_serialized_data_checksum_only", report["inspection_modes"])

    def test_public_export_gate(self):
        public = self.root / "public"; public.mkdir(); (public / "README.md").write_text("# Original templates", encoding="utf-8")
        self.assertFalse(scan(public)["errors"])
        (public / ".env").write_text("PRIVATE=not-a-real-secret", encoding="utf-8")
        (public / "weights.onnx").write_bytes(b"test")
        self.assertGreaterEqual(len(scan(public)["errors"]), 2)
        private_example = "C" + ":\\" + "Users" + "\\" + "Alice" + "\\" + "notes.txt"
        (public / "paths.txt").write_text(private_example, encoding="utf-8")
        self.assertTrue(any(e == ["paths.txt", "private_home"] for e in scan(public)["errors"]))

    def test_readme_image_allowlist_is_explicit_and_narrow(self):
        from PIL import Image, PngImagePlugin
        public = self.root / "public"; images = public / "assets/readme"; images.mkdir(parents=True)
        shutil_source = self.inputs / "speed-source.png"
        good = images / "demo-preview.png"; good.write_bytes(shutil_source.read_bytes())
        self.assertTrue(scan(public)["errors"])
        self.assertFalse(scan(public, allow_readme_images=True)["errors"])
        bad = images / "fake-preview.png"; bad.write_text("not a PNG", encoding="utf-8")
        self.assertTrue(scan(public, allow_readme_images=True)["errors"]); bad.unlink()
        metadata = PngImagePlugin.PngInfo(); metadata.add_text("Comment", "private note")
        with Image.open(good) as im: im.save(images / "metadata-preview.png", pnginfo=metadata)
        self.assertTrue(any(e[0].endswith("metadata-preview.png") for e in scan(public, True)["errors"]))
        (images / "metadata-preview.png").unlink()
        (public / "unreviewed.png").write_bytes(good.read_bytes())
        self.assertTrue(any(e[0] == "unreviewed.png" for e in scan(public, True)["errors"]))

if __name__ == "__main__": unittest.main(verbosity=2)
