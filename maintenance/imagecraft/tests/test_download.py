import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "imagecraft" / "scripts"))
import download_models as models


class Response(io.BytesIO):
    def __init__(self, content, status=200, headers=None):
        super().__init__(content)
        self.status, self.headers = status, headers or {}


class Opener:
    def __init__(self, response):
        self.response = response
        self.requests = []

    def open(self, request, **kwargs):
        self.requests.append(request)
        return self.response


class Downloads(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.addCleanup(self.temp.cleanup)
        self.data = b"a small, fake model"
        self.item = {"destination": "vae/test.safetensors", "repo": "Comfy-Org/Flux-2-Klein-4B",
                     "revision": "a" * 40, "source": "test.safetensors", "bytes": len(self.data),
                     "sha256": hashlib.sha256(self.data).hexdigest()}

    def partial(self, content):
        target = models.destination(self.root, self.item)
        target.parent.mkdir(parents=True)
        target.with_name(target.name + ".imagecraft.part").write_bytes(content)
        identity = {k: self.item[k] for k in ("repo", "revision", "source", "bytes", "sha256")}
        target.with_name(target.name + ".imagecraft.part.json").write_text(json.dumps(identity))
        return target

    def test_new_and_reuse(self):
        opener = Opener(Response(self.data))
        self.assertEqual(models.download_one(self.root, self.item, opener=opener)["status"], "downloaded_verified")
        self.assertEqual(models.download_one(self.root, self.item, opener=opener)["status"], "verified_existing")
        self.assertEqual(len(opener.requests), 1)

    def test_resume(self):
        target = self.partial(self.data[:4])
        response = Response(self.data[4:], 206, {"Content-Range": f"bytes 4-{len(self.data)-1}/{len(self.data)}"})
        models.download_one(self.root, self.item, opener=Opener(response))
        self.assertEqual(target.read_bytes(), self.data)

    def test_range_ignored_restarts_not_appends(self):
        target = self.partial(self.data[:4])
        models.download_one(self.root, self.item, opener=Opener(Response(self.data)))
        self.assertEqual(target.read_bytes(), self.data)

    def test_wrong_range(self):
        self.partial(self.data[:4])
        with self.assertRaises(models.ModelError):
            models.download_one(self.root, self.item, opener=Opener(Response(self.data[4:], 206, {"Content-Range": "bytes 0-5/6"})))

    def test_hash_mismatch_not_installed(self):
        with self.assertRaises(models.ModelError):
            models.download_one(self.root, self.item, opener=Opener(Response(b"x" * len(self.data))))
        self.assertFalse(models.destination(self.root, self.item).exists())

    def test_existing_conflict_untouched(self):
        target = models.destination(self.root, self.item)
        target.parent.mkdir(parents=True)
        target.write_bytes(b"do not overwrite")
        with self.assertRaises(models.ModelError):
            models.download_one(self.root, self.item)
        self.assertEqual(target.read_bytes(), b"do not overwrite")

    def test_escape_rejected(self):
        self.item["destination"] = "../elsewhere.safetensors"
        with self.assertRaises(models.ModelError):
            models.destination(self.root, self.item)

    def test_manifest(self):
        manifest = models.load_manifest()
        self.assertEqual(len(manifest["files"]), 3)
        self.assertEqual(sum(x["bytes"] for x in manifest["files"]), 12451817860)

    def test_parallel_ranges_and_full_hash(self):
        owner = self
        class RangeOpener:
            def open(self, request, **kwargs):
                start, end = map(int, request.get_header("Range").removeprefix("bytes=").split("-"))
                return Response(owner.data[start:end + 1], 206, {"Content-Range": f"bytes {start}-{end}/{len(owner.data)}"})
        result = models.download_parallel(self.root, self.item, 2, opener_factory=RangeOpener, segment_bytes=4)
        self.assertEqual(result["status"], "downloaded_verified")
        self.assertEqual(models.destination(self.root, self.item).read_bytes(), self.data)
        self.assertFalse(list((self.root / ".imagecraft-segments").rglob("*.bin")))

    def test_parallel_rejects_ignored_range(self):
        with self.assertRaises(models.ModelError):
            models.download_parallel(self.root, self.item, 2, opener_factory=lambda: Opener(Response(self.data)), segment_bytes=4)
        self.assertFalse(models.destination(self.root, self.item).exists())

    def test_parallel_rejects_bad_final_hash(self):
        owner = self
        class BadOpener:
            def open(self, request, **kwargs):
                start, end = map(int, request.get_header("Range").removeprefix("bytes=").split("-"))
                return Response(b"x" * (end - start + 1), 206, {"Content-Range": f"bytes {start}-{end}/{len(owner.data)}"})
        with self.assertRaises(models.ModelError):
            models.download_parallel(self.root, self.item, 2, opener_factory=BadOpener, segment_bytes=4)
        self.assertFalse(models.destination(self.root, self.item).exists())

    def test_atomic_publication_does_not_replace_existing_file(self):
        source, target = self.root / "source", self.root / "target"
        source.write_bytes(b"new")
        target.write_bytes(b"keep")
        with self.assertRaises(OSError):
            models.publish_no_clobber(source, target)
        self.assertEqual(target.read_bytes(), b"keep")
        self.assertEqual(source.read_bytes(), b"new")

    def test_hub_failure_does_not_print_signed_url(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        def fail(**kwargs):
            raise RuntimeError("secret signed CDN URL should not escape")
        self.item["role"] = "vae"
        with patch.dict(sys.modules, {"huggingface_hub": SimpleNamespace(hf_hub_download=fail)}):
            with self.assertRaises(models.ModelError) as error:
                models.download_with_hub(self.root, self.item)
        self.assertNotIn("secret", str(error.exception))
        self.assertIn("RuntimeError", str(error.exception))

    def test_lock_released(self):
        with models.file_lock(self.root / "lock"):
            pass
        with models.file_lock(self.root / "lock"):
            pass


if __name__ == "__main__":
    unittest.main()
