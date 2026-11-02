from http.client import HTTPMessage
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid
from urllib.request import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "imagecraft/scripts"))
from ic import jobs
from ic.client import Client, HTTPFailure, NoRedirects
from ic.common import Error, atomic_json, endpoint, safe_child
from ic.workflow import build, dimensions, open_image, reference_png, validate
from PIL import Image


def object_info():
    result = {}
    for node in build("test", 1024, 1024, 42, "test", ["input.png"]).values():
        result[node["class_type"]] = {"python_module": "nodes", "input": {"required": {k: ["ANY"] for k in node["inputs"]}}}
    return result


class FakeClient(Client):
    posts = 0
    fail_post = False
    busy = False
    history_value: dict | None = None
    image_bytes: bytes | None = None

    def __init__(self, *args, **kwargs):
        pass

    def request(self, path, payload=None, *, raw=None, content_type=None, binary=False):
        if path == "/queue":
            return {"queue_running": [[0, str(uuid.uuid4()), {}, {}]] if self.busy else [], "queue_pending": []}
        if path == "/object_info":
            return object_info()
        if path == "/system_stats":
            return {"system": {"comfyui_version": "mock"}}
        if path.startswith("/history"):
            return {}
        if path == "/prompt":
            FakeClient.posts += 1
            if self.fail_post:
                raise Error("simulated lost receipt")
            assert payload is not None  # Fixture callers must supply the POST body.
            return {"prompt_id": payload["prompt_id"]}
        raise AssertionError(path)

    def history(self, prompt_id):
        return self.history_value

    def view(self, image):
        assert self.image_bytes is not None
        return self.image_bytes


class Runtime(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.cfg = {"url": "http://127.0.0.1:8188", "models_root": str(self.root / "models")}
        self.request = jobs.prepare_request("An orange teapot", 256, 256, 42, "general", [])
        FakeClient.posts, FakeClient.fail_post, FakeClient.busy = 0, False, False
        FakeClient.history_value = FakeClient.image_bytes = None
        self.addCleanup(patch.stopall)
        patch("ic.jobs.Client", FakeClient).start()
        patch("ic.jobs.inventory", return_value={"files": [{"status": "verified", "role": "test", "sha256": "a" * 64, "bytes": 1, "path": "fake"}]}).start()

    def test_endpoint_guard(self):
        for bad in ("https://example.org", "http://192.168.1.1:8188", "http://0.0.0.0:8188", "http://localhost@evil.test", "http://127.0.0.1/path", "http://127.0.0.1?x=1", "file:///tmp", "http://127.0.0.1:99999", "http://127.0.0.1:0"):
            with self.subTest(bad=bad), self.assertRaises(Error):
                endpoint(bad)
        self.assertEqual(endpoint("http://localhost:8189/"), "http://127.0.0.1:8189")
        self.assertEqual(endpoint("http://[::1]:8188"), "http://[::1]:8188")

    def test_redirect_refused(self):
        with io.BytesIO() as stream, self.assertRaises(Error):
            NoRedirects().redirect_request(Request("http://127.0.0.1:8188"), stream, 302, "", HTTPMessage(), "https://outside.test")

    def test_graph_reference_and_bounds(self):
        graph = build("keep product shape, change color", 1024, 1024, 42, "test", ["a.png", "b.png"])
        validate(graph, object_info())
        self.assertEqual(graph["8"]["inputs"]["positive"], ["26", 0])
        self.assertEqual(graph["8"]["inputs"]["negative"], ["27", 0])
        for size in ((4096, 4096), (1023, 1024), (1024, None), (1536, 1536)):
            with self.assertRaises(Error):
                dimensions(*size)
        with self.assertRaises(Error):
            build("", 1024, 1024, 42, "test")
        with self.assertRaises(Error):
            build("test", 1024, 1024, -1, "test")

    def test_custom_node_override_refused(self):
        info = object_info()
        info["UNETLoader"]["python_module"] = "custom_nodes.untrusted"
        with self.assertRaises(Error):
            validate(build("test", 1024, 1024, 42, "test"), info)

    def test_unavailable_model_refused(self):
        info = object_info()
        info["UNETLoader"]["input"]["required"]["unet_name"] = [["other-model.safetensors"]]
        with self.assertRaises(Error):
            validate(build("test", 1024, 1024, 42, "test"), info)

    def test_same_job_posts_only_once(self):
        first = jobs.submit(self.cfg, self.root, self.request)
        second = jobs.submit(self.cfg, self.root, self.request)
        self.assertEqual(first["prompt_id"], second["prompt_id"])
        self.assertEqual(FakeClient.posts, 1)

    def test_ambiguous_post_durable_and_no_resubmit(self):
        FakeClient.fail_post = True
        with self.assertRaises(Error):
            jobs.submit(self.cfg, self.root, self.request)
        self.assertEqual(jobs.load_job(self.root)["state"], "submitting")
        FakeClient.fail_post = False
        again = jobs.submit(self.cfg, self.root, self.request)
        self.assertEqual(FakeClient.posts, 1)
        result, code = jobs.wait(self.cfg, self.root, again, 0)
        self.assertEqual((result["state"], code), ("unknown", 3))

    def test_http_408_is_ambiguous_not_rejected(self):
        original = FakeClient.request
        def timeout(client, path, payload=None):
            if path == "/prompt":
                raise HTTPFailure(408, "timed out")
            return original(client, path, payload)
        with patch.object(FakeClient, "request", timeout), self.assertRaises(HTTPFailure):
            jobs.submit(self.cfg, self.root, self.request)
        self.assertEqual(jobs.load_job(self.root)["state"], "submitting")

    def test_bad_wait_rejected_before_configuration_or_submit(self):
        from ic.cli import main
        for value in ("-1", "nan", "inf"):
            with patch("ic.cli.config") as cfg, patch("sys.stdout", new=io.StringIO()):
                code = main(["generate", "--prompt", "test", "--output", str(self.root / "job"), "--wait", value])
                self.assertEqual(code, 2)
                cfg.assert_not_called()
        self.assertEqual(FakeClient.posts, 0)

    def test_pillow_bomb_has_structured_error(self):
        path = self.root / "large.png"
        Image.new("RGB", (256, 256)).save(path)
        with patch.object(Image, "MAX_IMAGE_PIXELS", 10), self.assertRaisesRegex(Error, "pixel safety"):
            open_image(path)

    def test_transparency_is_composited_and_tiny_aspect_preserved(self):
        path = self.root / "transparent.png"
        Image.new("RGBA", (32, 64), (255, 0, 0, 0)).save(path)
        self.assertEqual(open_image(path).getpixel((0, 0)), (255, 255, 255))
        self.assertEqual(dimensions(reference=path), (256, 512))

    def test_new_payload_existing_job_refused(self):
        jobs.submit(self.cfg, self.root, self.request)
        other = {**self.request, "prompt": "different"}
        with self.assertRaises(Error):
            jobs.submit(self.cfg, self.root, other)
        self.assertEqual(FakeClient.posts, 1)

    def test_busy_queue_not_submitted(self):
        FakeClient.busy = True
        with self.assertRaises(Error):
            jobs.submit(self.cfg, self.root, self.request)
        self.assertEqual(FakeClient.posts, 0)
        self.assertEqual(jobs.load_job(self.root)["state"], "prepared")

    def test_existing_output_not_overwritten(self):
        (self.root / "other.txt").write_text("keep")
        with self.assertRaises(Error):
            jobs.submit(self.cfg, self.root, self.request)
        self.assertEqual((self.root / "other.txt").read_text(), "keep")

    def test_error_history_and_lost_history(self):
        job = jobs.submit(self.cfg, self.root, self.request)
        FakeClient.history_value = {"status": {"status_str": "error", "completed": False}}
        self.assertEqual(jobs.observe(FakeClient(), job)[0], "failed")
        FakeClient.history_value = None
        self.assertEqual(jobs.observe(FakeClient(), job)[0], "unknown")

    def test_fetch_verifies_strips_metadata_and_detects_tamper(self):
        from PIL.PngImagePlugin import PngInfo
        job = jobs.submit(self.cfg, self.root, self.request)
        image = Image.new("RGB", (256, 256), "blue")
        raw, metadata = io.BytesIO(), PngInfo()
        metadata.add_text("prompt", "private prompt")
        image.save(raw, format="PNG", pnginfo=metadata)
        FakeClient.image_bytes = raw.getvalue()
        history = {"outputs": {"13": {"images": [{"filename": "a.png", "subfolder": "", "type": "output"}]}},
                   "status": {"messages": [["execution_start", {"timestamp": 1000}], ["execution_success", {"timestamp": 2500}]]}}
        jobs.fetch(FakeClient(), self.root, job, history)
        self.assertEqual(job["server_execution_seconds"], 1.5)
        self.assertEqual(job["visual_review"]["status"], "required")
        with Image.open(self.root / "image.png") as check:
            self.assertEqual(check.info, {})
        jobs.verify_artifacts(self.root, job)
        (self.root / "image.png").write_bytes(b"tampered")
        with self.assertRaises(Error):
            jobs.verify_artifacts(self.root, job)

    def test_wrong_size_preview_and_escape_rejected(self):
        job = jobs.submit(self.cfg, self.root, self.request)
        with self.assertRaises(Error):
            jobs.fetch(FakeClient(), self.root, job, {"outputs": {"12": {"images": [{}]}}})
        raw = io.BytesIO()
        Image.new("RGB", (512, 512)).save(raw, format="PNG")
        FakeClient.image_bytes = raw.getvalue()
        with self.assertRaises(Error):
            jobs.fetch(FakeClient(), self.root, job, {"outputs": {"13": {"images": [{}]}}})
        with self.assertRaises(Error):
            safe_child(self.root, "../escape")
        with self.assertRaises(Error):
            Client(self.cfg["url"]).view({"filename": "../x.png", "type": "output"})
        with self.assertRaises(Error):
            Client(self.cfg["url"]).view({"filename": "x.png", "type": "temp"})

    def test_reference_is_sanitized_and_downscaled(self):
        from PIL.PngImagePlugin import PngInfo
        source = self.root / "source.png"
        metadata = PngInfo()
        metadata.add_text("private", "secret")
        Image.new("RGB", (2048, 1024), "green").save(source, pnginfo=metadata)
        raw = reference_png(source)
        image = Image.open(io.BytesIO(raw))
        self.assertLess(image.width * image.height, 1_100_000)
        self.assertEqual(image.info, {})
        self.assertEqual(dimensions(reference=source), (1440, 720))


if __name__ == "__main__":
    unittest.main()
