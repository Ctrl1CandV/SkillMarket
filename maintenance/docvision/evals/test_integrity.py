"""Offline regressions for completeness, page access and render reuse."""

from __future__ import annotations

import base64
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "docvision" / "scripts"))

from dv import cache, read, util  # noqa: E402
from dv.base import DocVisionError, Options, RawBlock, RawDoc, RawPage  # noqa: E402
from dv.output import write_document  # noqa: E402
from dv.verify import verify_document  # noqa: E402

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "input.pdf"
        self.source.write_bytes(b"offline render fixture")

    def document(self, numbers=(1,), *, total=1, selected=None, empty=False, image=False):
        pages = []
        for number in numbers:
            body = "" if empty else f"Body on original page {number}."
            blocks = [] if empty else [RawBlock(markdown=body, text=body, page=number)]
            if image:
                body = ""
                blocks = [RawBlock(type="image", page=number, asset="diagram.png")]
            pages.append(RawPage(page=number, markdown=body, blocks=blocks))
        raw = RawDoc(markdown="", pages=pages, provider="mineru-local",
                     assets={"diagram.png": PNG} if image else {})
        return write_document(raw, str(self.source), Options(pages=selected),
                              out_root=self.root / "out", info={"pages": total, "sha256": util.sha256_file(self.source)})

    @staticmethod
    def issue_codes(qa):
        return {issue["code"] for issue in qa["issues"]}

    def test_missing_tail_pages_fail_against_source_count(self):
        qa = verify_document(self.document((1,), total=12))
        self.assertEqual(qa["status"], "fail")
        self.assertIn("missing_pages", self.issue_codes(qa))

    def test_selected_wrong_pages_fail(self):
        qa = verify_document(self.document((1,), total=12, selected="3-5"))
        self.assertEqual(qa["status"], "fail")
        self.assertIn("unexpected_pages", self.issue_codes(qa))
        self.assertIn("missing_pages", self.issue_codes(qa))

    def test_reverse_selection_matches_original_page_numbers(self):
        self.assertEqual(verify_document(self.document((10, 11, 12), total=12,
                                                      selected="r3-r1"))["status"], "pass")

    def test_unknown_source_count_is_explicitly_unverified(self):
        qa = verify_document(self.document(total=None))
        self.assertEqual(qa["status"], "warn")
        self.assertIn("source_page_count_unknown", self.issue_codes(qa))

    def test_empty_output_cannot_pass_on_generated_header(self):
        qa = verify_document(self.document(empty=True))
        self.assertEqual(qa["status"], "fail")
        self.assertIn("empty_body", self.issue_codes(qa))

    def test_empty_block_objects_do_not_count_as_body(self):
        docdir = self.document(empty=True)
        content = util.read_json(docdir / "content.json")
        content["pages"][0]["blocks"] = [{"type": "text", "text": "", "markdown": ""}]
        util.write_json(docdir / "content.json", content)
        self.assertEqual(verify_document(docdir)["status"], "fail")

    def test_real_image_only_page_is_not_empty(self):
        qa = verify_document(self.document(image=True))
        self.assertEqual(qa["status"], "pass")
        self.assertNotIn("empty_body", self.issue_codes(qa))

    def test_nonexistent_requested_page_raises_for_text_and_json(self):
        docdir = self.document()
        for kwargs in ({}, {"as_json": True}, {"context": 2}):
            with self.subTest(kwargs=kwargs), self.assertRaises(DocVisionError):
                read.read(docdir, page=3, **kwargs)

    def test_zero_requested_page_does_not_fall_back_to_listing(self):
        with self.assertRaises(DocVisionError):
            read.read(self.document(), page=0)

    def test_render_cache_honors_requested_dpi(self):
        docdir = self.document()
        # The PDF renderer is the external dependency; file reuse stays real.
        with patch.object(util, "render_pdf_page", side_effect=lambda source, index, dpi: str(dpi).encode()):
            low = read.render_page(docdir, 1, dpi=150)
            high = read.render_page(docdir, 1, dpi=400)
            self.assertEqual(high.read_bytes(), b"400")
            self.assertEqual(low.read_bytes(), b"150")
            again = read.render_page(docdir, 1, dpi=400)
            self.assertEqual(again.read_bytes(), b"400")

    def test_render_missing_page_fails_even_if_source_exists(self):
        docdir = self.document()
        with patch.object(util, "render_pdf_page", return_value=PNG):
            with self.assertRaises(DocVisionError):
                read.render_page(docdir, 2)


class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.info = {"sha256": "same-source", "pages": 3}
        self.opts = Options(provider="auto", pages="1-3", extra={"model": "ocr-v1"})
        self.docdir = self.root / "cached"
        self.docdir.mkdir()
        self.meta = {"source": self.info, "markdown_path": "cached.md",
                     "raw_meta": {"cache_request": self.signature(self.opts)}}
        self.save_meta()
        util.write_json(self.docdir / "qa.json", {"status": "pass"})
        util.write_json(self.docdir / "content.json", {"pages": [{"page": 1}]})
        (self.docdir / "cached.md").write_text("Existing body", encoding="utf-8")

    def signature(self, opts, **kwargs):
        return cache.request_signature(self.info, opts, provider="mineru-local", **kwargs)

    def find(self, opts=None, *, info=None, provider="mineru-local", **kwargs):
        return cache.find_existing(self.root, info or self.info, opts or self.opts,
                                   provider=provider, **kwargs)

    def save_meta(self):
        util.write_json(self.docdir / "meta.json", self.meta)

    def test_matching_request_is_reused(self):
        self.assertEqual(self.find(), self.docdir)

    def test_changes_to_result_options_do_not_reuse(self):
        for name, changed in (("tier", "quality"), ("mode", "ocr"), ("pages", "2-3"),
                              ("lang", "en"), ("device", "cpu"), ("images", False),
                              ("keep_raw", True), ("extra", {"model": "ocr-v2"}),
                              ("extra", {"model": "ocr-v1", "enable_formula": False})):
            with self.subTest(option=name):
                opts = Options(provider="auto", pages="1-3", extra={"model": "ocr-v1"})
                setattr(opts, name, changed)
                self.assertIsNone(self.find(opts))

    def test_resolved_provider_change_does_not_reuse_auto_request(self):
        self.assertIsNone(self.find(provider="paddleocr-local"))

    def test_explicit_resolved_model_change_does_not_reuse(self):
        self.assertIsNone(self.find(model="resolved-model-v2"))

    def test_config_context_change_does_not_reuse(self):
        self.assertIsNone(self.find(context={"backend": "new-runtime"}))

    def test_different_source_sha_does_not_reuse(self):
        self.assertIsNone(self.find(info={"sha256": "other-source", "pages": 3}))

    def test_failed_or_missing_qa_is_not_reused(self):
        util.write_json(self.docdir / "qa.json", {"status": "fail"})
        self.assertIsNone(self.find())
        (self.docdir / "qa.json").unlink()
        self.assertIsNone(self.find())

    def test_unsigned_legacy_metadata_is_not_reused(self):
        self.meta.pop("raw_meta")
        self.save_meta()
        self.assertIsNone(self.find())

    def test_missing_content_is_not_reused(self):
        (self.docdir / "content.json").unlink()
        self.assertIsNone(self.find())

    def test_equivalent_page_ranges_are_compatible(self):
        self.opts.pages = "1,2,3"
        self.assertEqual(self.find(), self.docdir)

    def test_extra_values_are_hashed_in_persisted_request(self):
        opts = Options(extra={"token": "never-persist-this-secret", "model": "ocr-v1"})
        signature = self.signature(opts, context={"url": "https://host/?secret=never-persist-this-secret"})
        self.assertNotIn("never-persist-this-secret", json.dumps(signature))
        self.assertIsNotNone(signature)


if __name__ == "__main__":
    unittest.main(verbosity=2)
