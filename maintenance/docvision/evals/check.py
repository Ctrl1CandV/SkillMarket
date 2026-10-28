#!/usr/bin/env python3
"""Deterministic adapter/output checks that do not call real OCR services.

Run from the repository root:
    python maintenance/docvision/evals/check.py
"""

from __future__ import annotations

import base64
import json
import os
import sys
import io
import tempfile
import threading
import unittest
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "docvision" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from dv import config, util  # noqa: E402
from dv.base import Options  # noqa: E402
from dv.output import write_document  # noqa: E402
from dv.providers import run as run_provider  # noqa: E402
from dv.providers import mineru_cloud  # noqa: E402
from dv.verify import verify_document  # noqa: E402

PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/v1/models"):
            self._send(200, {"data": [{"id": "mock-vl"}]})
        elif self.path.startswith("/api/v4/extract-results/batch/"):
            self._send(200, {"code": 0, "data": {"extract_result": [{
                "data_id": getattr(self.server, "last_data_id", ""),
                "state": "done",
                "full_zip_url": f"http://127.0.0.1:{self.server.server_address[1]}/result.zip",
            }]}})
        elif self.path == "/result.zip":
            body = self.server.zip_bytes
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self._send(404, {"error": "not found"})

    def do_PUT(self):
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        self.send_response(200)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except ValueError:
            payload = {}
        if self.path.endswith("/file-urls/batch"):
            files = payload.get("files") or [{}]
            self.server.last_data_id = files[0].get("data_id", "")
            port = self.server.server_address[1]
            self._send(200, {"code": 0, "data": {"batch_id": "b1",
                                                 "file_urls": [f"http://127.0.0.1:{port}/upload"]}})
        elif self.path.endswith("/layout_parsing"):
            self._send(200, {
                "id": "req-mock",
                "model": "glm-ocr",
                "md_results": "# Mock GLM\n\nFormula $E=mc^2$.\n\n<table><tr><td>a</td><td>b</td></tr></table>",
                "layout_details": [[
                    {"index": 1, "label": "text", "bbox_2d": [0.1, 0.1, 0.9, 0.2],
                     "content": "Mock GLM", "width": 1000, "height": 1400},
                    {"index": 2, "label": "formula", "bbox_2d": [0.1, 0.3, 0.9, 0.4],
                     "content": "E=mc^2", "width": 1000, "height": 1400},
                ]],
                "usage": {"total_tokens": 12},
            })
        elif self.path.endswith("/ocr"):
            self._send(200, {
                "model": "mistral-ocr-latest",
                "pages": [{
                    "index": 0,
                    "markdown": "# Mock Mistral\n\n![img-0.png](img-0.png)\n\n[table-0.html](table-0.html)",
                    "dimensions": {"width": 1000, "height": 1400},
                    "images": [{"id": "img-0.png", "image_base64": base64.b64encode(PNG_1PX).decode()}],
                    "tables": [{"id": "table-0.html", "content": "<table><tr><td>x</td><td>y</td></tr></table>"}],
                    "blocks": [
                        {"type": "text", "content": "Mock Mistral", "bbox": [100, 100, 900, 200]},
                        {"type": "table", "content": "<table><tr><td>x</td><td>y</td></tr></table>",
                         "bbox": [100, 300, 900, 500]},
                    ],
                }],
                "usage_info": {"pages_processed": 1},
            })
        elif self.path.endswith("/chat/completions"):
            self._send(200, {"choices": [{"message": {"content": "Mock VLM page text with $a+b$."}}]})
        elif ":generateContent" in self.path:
            self._send(200, {
                "candidates": [{"content": {"parts": [{"text": "<!-- page: 1 -->\n# Mock Gemini\n\nText and $x^2$."}]}}],
                "usageMetadata": {"totalTokenCount": 20},
            })
        else:
            self._send(404, {"error": "not found", "path": self.path})


class ProviderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.tmp = Path(tempfile.mkdtemp(prefix="docvision-eval-"))
        cls.source = cls.tmp / "sample.png"
        cls.source.write_bytes(PNG_1PX)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("markdown.md", "# Mock Standard\n\nText and $x^2$.\n")
            z.writestr("middle_json.json", json.dumps({
                "schema": "docvortex.middle", "schema_version": "2.0",
                "metadata": {"document": {"page_count": 1}},
                "extensions": {"docvortex_layout": {"pages": [
                    {"page_idx": 0, "width_pt": 595, "height_pt": 842}]}},
                "pages": [{"page_idx": 0, "blocks": [
                    {"type": "paragraph_title", "index": 0, "bbox": [0.1, 0.1, 0.9, 0.2],
                     "content": [{"type": "text", "content": "Mock Standard"}], "level": 2}]}],
            }))
        cls.server.zip_bytes = buf.getvalue()
        cls.cfg_path = cls.tmp / "config.json"
        os.environ["DOCVISION_CONFIG"] = str(cls.cfg_path)
        cfg = config.load()
        base = f"http://127.0.0.1:{cls.port}"
        cfg["remote"]["glm_base"] = base
        cfg["remote"]["mistral_base"] = base + "/v1"
        cfg["remote"]["gemini_base"] = base + "/v1beta"
        cfg["remote"]["gemini_model"] = "mock-flash"
        cfg["engines"]["vlm"]["base_url"] = base + "/v1"
        cfg["engines"]["vlm"]["model"] = "mock-vl"
        config.save(cfg)
        os.environ["ZHIPU_API_KEY"] = "test-glm"
        os.environ["MISTRAL_API_KEY"] = "test-mistral"
        os.environ["GEMINI_API_KEY"] = "test-gemini"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def opts(self, provider: str) -> Options:
        return Options(provider=provider, allow_remote=True, lang="ch", timeout=60)

    def test_glm_remote_parse(self):
        doc, meta = run_provider("glm-cloud", str(self.source), self.opts("glm-cloud"))
        self.assertEqual(doc.provider, "glm-cloud")
        self.assertEqual(len(doc.pages), 1)
        self.assertEqual(doc.pages[0].blocks[0].type, "text")
        self.assertEqual(doc.pages[0].blocks[1].type, "formula")
        self.assertIn("E=mc^2", doc.pages[0].blocks[1].markdown)
        out = write_document(doc, str(self.source), self.opts("glm-cloud"), out_root=self.tmp / "out-glm", info={"pages": 1})
        self.assertTrue((out / "content.json").is_file())
        self.assertEqual(verify_document(out)["status"], "pass")

    def test_mistral_remote_parse(self):
        doc, meta = run_provider("mistral", str(self.source), self.opts("mistral"))
        self.assertEqual(len(doc.pages), 1)
        self.assertIn("img-0.png", doc.assets)
        self.assertIn("<table>", doc.pages[0].markdown)
        self.assertTrue(any("x" in b.markdown for b in doc.pages[0].blocks))
        out = write_document(doc, str(self.source), self.opts("mistral"), out_root=self.tmp / "out-mistral", info={"pages": 1})
        self.assertTrue((out / "assets" / "img-0.png").is_file())
        self.assertEqual(verify_document(out)["status"], "pass")

    def test_gemini_remote_parse(self):
        doc, meta = run_provider("gemini", str(self.source), self.opts("gemini"))
        self.assertEqual(len(doc.pages), 1)
        self.assertIn("Mock Gemini", doc.markdown)
        out = write_document(doc, str(self.source), self.opts("gemini"), out_root=self.tmp / "out-gemini", info={"pages": 1})
        self.assertEqual(verify_document(out)["status"], "pass")

    def test_mineru_standard_parse(self):
        old_base = mineru_cloud.STANDARD_BASE
        mineru_cloud.STANDARD_BASE = f"http://127.0.0.1:{self.port}/api/v4"
        os.environ["MINERU_TOKEN"] = "test-mineru"
        try:
            doc, meta = run_provider("mineru-cloud", str(self.source), self.opts("mineru-cloud"))
        finally:
            mineru_cloud.STANDARD_BASE = old_base
            os.environ.pop("MINERU_TOKEN", None)
        self.assertEqual(doc.provider, "mineru-cloud")
        self.assertEqual(len(doc.pages), 1)
        self.assertEqual(doc.pages[0].blocks[0].type, "heading")
        out = write_document(doc, str(self.source), self.opts("mineru-cloud"), out_root=self.tmp / "out-standard", info={"pages": 1})
        self.assertEqual(verify_document(out)["status"], "pass")

    def test_local_vlm_parse(self):
        doc, meta = run_provider("local-vlm", str(self.source), self.opts("local-vlm"))
        self.assertEqual(doc.provider, "local-vlm")
        self.assertIn("Mock VLM", doc.markdown)
        out = write_document(doc, str(self.source), self.opts("local-vlm"), out_root=self.tmp / "out-vlm", info={"pages": 1})
        self.assertEqual(verify_document(out)["status"], "pass")


if __name__ == "__main__":
    unittest.main(verbosity=2)
