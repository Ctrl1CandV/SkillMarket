#!/usr/bin/env python3
"""Deterministic adapter/output checks that never call a real OCR service.

Run from the repository root:
    python maintenance/docvision/evals/check.py
"""

from __future__ import annotations

import base64
import io
import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "docvision" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from dv import config, util  # noqa: E402
from dv.base import Options  # noqa: E402
from dv.output import write_document  # noqa: E402
from dv.providers import paddle_cloud  # noqa: E402
from dv.providers import run as run_provider  # noqa: E402
from dv.verify import verify_document  # noqa: E402

PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class Handler(BaseHTTPRequestHandler):
    """Minimal PaddleOCR job API: submit, poll once, download JSONL."""

    def log_message(self, *args):
        pass

    def _send(self, code: int, payload, mime: str = "application/json"):
        body = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        if self.path == "/v1/chat/completions":
            self.server.vlm_requests.append(json.loads(body))
            self._send(200, {"choices": [{"finish_reason": "stop", "message": {
                "content": "Mock VLM page text with $a+b$."}}]})
            return
        self._send(200, {"code": 0, "data": {"jobId": "job-check"}})

    def do_GET(self):
        if self.path.endswith("/job-check"):
            self._send(200, {"code": 0, "data": {
                "jobId": "job-check", "state": "done",
                "resultUrl": {"jsonUrl": f"http://127.0.0.1:{self.server.server_port}/result.jsonl"}}})
        elif self.path == "/result.jsonl":
            self._send(200, self.server.jsonl, "application/jsonl")
        else:
            self._send(404, {"msg": "not found"})


class CheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="docvision-eval-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.tmp = Path(cls.temp.name)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.server.vlm_requests = []
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"
        cls.server.jsonl = b"\n".join(json.dumps({"result": {"layoutParsingResults": [
            {"markdown": {"text": "# Mock Paddle\n\nFormula $E=mc^2$.\n\n<table><tr><td>a</td><td>b</td></tr></table>",
                         "images": {}, "isStart": True, "isEnd": True},
             "prunedResult": {"width": 1000, "height": 1400, "parsing_res_list": [
                 {"block_label": "doc_title", "block_content": "Mock Paddle", "block_bbox": [100, 100, 900, 200]},
                 {"block_label": "formula", "block_content": "E=mc^2", "block_bbox": [100, 300, 900, 400]},
                 {"block_label": "table", "block_content": "<table><tr><td>a</td><td>b</td></tr></table>",
                  "block_bbox": [100, 500, 900, 700]},
             ]}}]}}).encode() for _ in range(1))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.source = cls.tmp / "sample.png"
        cls.source.write_bytes(PNG_1PX)
        os.environ["DOCVISION_CONFIG"] = str(cls.tmp / "config.json")
        os.environ["DOCVISION_CREDENTIALS"] = str(cls.tmp / "credentials.env")
        cfg = config.load()
        cfg["remote"]["consent"] = "remote"
        cfg["remote"]["paddle_base"] = cls.base + "/api/v2/ocr/jobs"
        cfg["engines"]["vlm"]["base_url"] = cls.base + "/v1"
        cfg["engines"]["vlm"]["model"] = "mock-vl"
        config.save(cfg)
        os.environ["PADDLEOCR_ACCESS_TOKEN"] = "fixture-token"
        cls.env_patch = patch.dict(os.environ, {"PADDLEOCR_ACCESS_TOKEN": "fixture-token"})
        cls.env_patch.start()
        cls.cfg_patch = patch.object(paddle_cloud, "config", config)
        cls.cfg_patch.start()

    @classmethod
    def tearDownClass(cls):
        cls.cfg_patch.stop()
        cls.env_patch.stop()
        cls.server.shutdown()
        cls.server.server_close()

    def opts(self, provider: str) -> Options:
        return Options(provider=provider, allow_remote=True, lang="ch", timeout=60)

    def test_cloud_contract_parses_to_output(self):
        doc, meta = run_provider("paddleocr-cloud", str(self.source), self.opts("paddleocr-cloud"))
        self.assertEqual(doc.provider, "paddleocr-cloud")
        self.assertEqual(len(doc.pages), 1)
        kinds = [b.type for b in doc.pages[0].blocks]
        self.assertIn("heading", kinds)
        self.assertIn("formula", kinds)
        self.assertIn("table", kinds)
        out = write_document(doc, str(self.source), self.opts("paddleocr-cloud"),
                             out_root=self.tmp / "out-cloud", info={"pages": 1})
        self.assertTrue((out / "content.json").is_file())
        self.assertEqual(verify_document(out)["status"], "pass")

    def test_remote_requires_explicit_upload_flag(self):
        from dv.base import DocVisionError
        from dv import cli
        with patch.object(config, "remote_consent", return_value="remote"):
            with self.assertRaises(DocVisionError) as error:
                cli._guard_remote("paddleocr-cloud", False)
        self.assertIn("not authorized", str(error.exception))

    def test_local_vlm_loopback_response_parses_to_output(self):
        opts = Options(provider="local-vlm", timeout=60,
                       extra={"base_url": self.base + "/v1", "model": "mock-vl"})
        with patch.dict(os.environ, {"DOCVISION_VLM_API_KEY": "fixture-local-key"}):
            doc, meta = run_provider("local-vlm", str(self.source), opts)
        self.assertEqual(doc.provider, "local-vlm")
        self.assertEqual(doc.model, "mock-vl")
        self.assertIn("Mock VLM", doc.markdown)
        self.assertIs(meta["local"], True)
        request = self.server.vlm_requests[-1]
        self.assertEqual(request["model"], "mock-vl")
        image = request["messages"][1]["content"][1]["image_url"]["url"]
        self.assertEqual(image, "data:image/png;base64," + base64.b64encode(PNG_1PX).decode())
        out = write_document(doc, str(self.source), opts,
                             out_root=self.tmp / "out-vlm", info={"pages": 1})
        self.assertEqual(verify_document(out)["status"], "pass")

    def test_local_only_consent_blocks_remote(self):
        from dv.base import DocVisionError
        from dv import cli
        with patch.object(config, "remote_consent", return_value="local-only"):
            with self.assertRaises(DocVisionError) as error:
                cli._guard_remote("paddleocr-cloud", True)
        self.assertIn("declined", str(error.exception))

    def test_credentials_are_not_written_into_config(self):
        from dv import credentials
        credentials.save_credentials({"PADDLEOCR_ACCESS_TOKEN": "fixture-token"})
        text = (self.tmp / "config.json").read_text(encoding="utf-8")
        self.assertNotIn("fixture-token", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
