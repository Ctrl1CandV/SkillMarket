"""Subscription backend regression tests use only a local stdio fixture."""
from contextlib import redirect_stdout
import io
from importlib import import_module
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import zlib

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/"imagecraft/scripts"))
cloud = import_module("cloud_codex")
Error = import_module("ic.common").Error
decode = import_module("ic.png").decode


def chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)


def png(body=b"\0\xff\0\0", width=1, height=1):
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"tEXt", b"prompt\0private") + chunk(b"IDAT", zlib.compress(body)) + chunk(b"IEND", b"")


class CloudTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prompt = self.root/"prompt.txt"
        self.prompt.write_text("One neutral ceramic mug, a synthetic test image.", encoding="utf-8")
        self.log = self.root/"rpc.jsonl"
        self.env = patch.dict(os.environ, {"IMAGECRAFT_FAKE_LOG": str(self.log), "CODEX_HOME": str(self.root/"codex")})
        self.env.start()
        self.command = [sys.executable, "-B", str(Path(__file__).with_name("fake_codex.py"))]
        self.count = 0

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def generate(self, mode="inline", extras=()):
        self.count += 1
        output = self.root/f"job-{self.count}"
        with patch.dict(os.environ, {"IMAGECRAFT_FAKE_SCENARIO": mode}), redirect_stdout(io.StringIO()) as printed:
            code = cloud.main(["generate", "--prompt-file", str(self.prompt), "--output", str(output), "--approve-cloud", "--wait", "10", *extras], command=self.command)
        text = printed.getvalue()
        self.assertNotIn("private@example", text)
        self.assertNotIn("sk-private", text)
        return code, output, json.loads((output/"job.json").read_text())

    def methods(self):
        return [json.loads(line)["method"] for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def test_inline_decoded_and_metadata_stripped(self):
        code, root, job = self.generate()
        self.assertEqual(code, 0)
        self.assertEqual(job["state"], "downloaded")
        self.assertEqual(job["artifact"]["width"], 16)
        self.assertNotIn(b"private", (root/"image.png").read_bytes())
        self.assertNotIn("email", job["account"])
        self.assertEqual(job["retrieval"]["visual_review"], "required")
        self.assertEqual(self.methods().count("exec"), 1)
        self.assertEqual(job["cleanup"], "exited_after_stdin_close")
        self.assertEqual(job["exec_cleanup"], "exited_after_stdin_close")

    def test_official_saved_path_and_directory_fallback(self):
        for mode, source in (("saved", "native_saved_path"), ("fallback", "native_generated_images_directory")):
            with self.subTest(mode=mode):
                code, _, job = self.generate(mode)
                self.assertEqual(code, 0)
                self.assertEqual(job["artifact"]["source"], source)

    def test_api_key_and_capability_and_quota_refuse_without_submit(self):
        for mode in ("api", "api-account", "no-capability", "no-included", "non-object"):
            with self.subTest(mode=mode):
                code, _, job = self.generate(mode)
                self.assertNotEqual(code, 0)
                self.assertEqual(job["submission"]["attempts"], 0)
        self.assertNotIn("exec", self.methods())

    def test_preview_and_unsafe_paths_are_not_images(self):
        for mode in ("preview", "unsafe-path"):
            with self.subTest(mode=mode):
                code, root, job = self.generate(mode)
                self.assertEqual(code, 2)
                self.assertEqual(job["state"], "no_verified_image")
                self.assertFalse((root/"image.png").exists())

    def test_lost_receipt_resume_never_resubmits(self):
        code, root, job = self.generate("lost")
        self.assertEqual(code, 3)
        self.assertEqual(job["state"], "unknown")
        self.assertEqual(job["submission"]["attempts"], 1)
        with redirect_stdout(io.StringIO()):
            code = cloud.main(["resume", "--job", str(root), "--wait", "0"], command=self.command)
        self.assertEqual(code, 0)
        self.assertEqual(self.methods().count("exec"), 1)
        self.assertNotIn("turn/start", self.methods())
        self.assertTrue((root/"image.png").is_file())

    def test_lost_before_thread_id_stays_unknown_without_retry(self):
        code, root, job = self.generate("lost-early")
        self.assertEqual(code, 3)
        self.assertEqual(job["submission"]["attempts"], 1)
        self.assertNotIn("thread_id", job)
        before = list(self.methods())
        with redirect_stdout(io.StringIO()):
            self.assertEqual(cloud.main(["resume", "--job", str(root)], command=self.command), 2)
        self.assertEqual(self.methods(), before)
        self.assertEqual(self.methods().count("exec"), 1)

    def test_capacity_failure_is_recovered_without_another_submission(self):
        code, root, job = self.generate("capacity")
        self.assertEqual(code, 3)
        self.assertEqual(job["submission"]["attempts"], 1)
        self.assertGreaterEqual(job["exec_seconds"], 0)
        with patch.dict(os.environ, {"IMAGECRAFT_FAKE_SCENARIO": "capacity"}), redirect_stdout(io.StringIO()):
            self.assertEqual(cloud.main(["resume", "--job", str(root), "--wait", "0"], command=self.command), 2)
        job = json.loads((root/"job.json").read_text())
        self.assertEqual(job["state"], "no_verified_image")
        self.assertEqual(job["generation"]["failure_code"], "server_overloaded")
        self.assertNotIn("private upstream", json.dumps(job))
        self.assertEqual(self.methods().count("exec"), 1)
        self.assertNotIn("turn/start", self.methods())

    def test_quota_failure_after_image_preserves_success(self):
        code, _, job = self.generate("quota-after")
        self.assertEqual(code, 0)
        self.assertEqual(job["quota"]["after"]["state"], "unavailable")
        self.assertNotIn("secret", json.dumps(job))

    def test_unexpected_tools_and_multiple_items_flag_policy(self):
        for mode in ("approval", "two-images"):
            with self.subTest(mode=mode):
                code, _, job = self.generate(mode)
                self.assertEqual(code, 2)
                self.assertEqual(job["state"], "policy_violation")
                self.assertIn("turn/interrupt", self.methods())

    def test_existing_output_no_overwrite_no_second_turn(self):
        _, root, _ = self.generate()
        before = list(self.methods())
        with redirect_stdout(io.StringIO()):
            code = cloud.main(["generate", "--prompt-file", str(self.prompt), "--output", str(root), "--approve-cloud"], command=self.command)
        self.assertEqual(code, 2)
        self.assertEqual(self.methods(), before)

    def test_reference_is_explicit_and_sanitized(self):
        reference = self.root/"reference.png"
        reference.write_bytes(png())
        code, root, job = self.generate(extras=["--reference", str(reference)])
        self.assertEqual(code, 0)
        self.assertNotIn(b"private", (root/"reference-1.png").read_bytes())
        self.assertNotEqual(job["references"][0]["sha256"], job["references"][0]["source_sha256"])
        turns = [json.loads(line) for line in self.log.read_text().splitlines() if json.loads(line)["method"] == "exec"]
        self.assertEqual(turns[0]["input_types"], ["text", "localImage"])

    def test_no_approval_no_output(self):
        root = self.root/"unapproved"
        with redirect_stdout(io.StringIO()):
            code = cloud.main(["generate", "--prompt-file", str(self.prompt), "--output", str(root)], command=self.command)
        self.assertEqual(code, 2)
        self.assertFalse(root.exists())
        self.assertNotIn("exec", self.methods())

    def test_status_is_offline_when_verified_and_detects_tampering(self):
        _, root, _ = self.generate()
        before = list(self.methods())
        with redirect_stdout(io.StringIO()):
            code = cloud.main(["status", "--job", str(root)], command=self.command)
        self.assertEqual(code, 0)
        self.assertEqual(self.methods(), before)
        (root/"image.png").write_bytes(b"changed")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(cloud.main(["status", "--job", str(root)], command=self.command), 2)


class PNGTests(unittest.TestCase):
    def test_unfilters_all_modes(self):
        # One RGB pixel per row; previous RGB=(10,20,30), desired=(15,25,35).
        first = b"\0\x0a\x14\x1e"
        modes = ((0, bytes([15,25,35])), (1, bytes([15,25,35])), (2, bytes([5,5,5])),
                 (3, bytes([10,15,20])), (4, bytes([5,5,5])))
        for mode, encoded in modes:
            with self.subTest(mode=mode):
                stripped, w, h = decode(png(first+bytes([mode])+encoded, height=2))
                self.assertEqual((w, h), (1, 2))
                self.assertNotIn(b"private", stripped)

    def test_unknown_ancillary_metadata_is_not_uploaded(self):
        original = png()
        ancillary = chunk(b"paTH", b"private source path")
        original = original[:33] + ancillary + original[33:]
        cleaned, w, h = decode(original)
        self.assertEqual((w, h), (1, 1))
        self.assertNotIn(b"private source path", cleaned)
        self.assertNotIn(b"paTH", cleaned)

    def test_palette_transparency_and_invalid_indices(self):
        header = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 3, 0, 0, 0))
        palette = chunk(b"PLTE", b"\xff\0\0")
        transparency = chunk(b"tRNS", b"\x80")
        prefix = b"\x89PNG\r\n\x1a\n" + header + palette + transparency
        valid = prefix + chunk(b"IDAT", zlib.compress(b"\0\0")) + chunk(b"IEND", b"")
        self.assertEqual(decode(valid), (valid, 1, 1))
        invalid = prefix + chunk(b"IDAT", zlib.compress(b"\0\1")) + chunk(b"IEND", b"")
        with self.assertRaisesRegex(Error, "palette index"):
            decode(invalid)

    def test_bad_crc_truncation_filters_and_size(self):
        invalid_crc = bytearray(png())
        invalid_crc[30] ^= 1
        for raw in (bytes(invalid_crc), png()[:-3], png(body=b"\x05\xff\0\0"), png(body=b"\0\xff"), png(width=24000001), b"preview", png()+b"trailing"):
            with self.subTest(raw_length=len(raw)):
                with self.assertRaises(Error):
                    decode(raw)


if __name__ == "__main__":
    unittest.main()
