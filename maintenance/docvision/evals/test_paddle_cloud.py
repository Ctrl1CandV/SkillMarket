"""Paddle official asynchronous HTTP contract; local fixtures, no OCR account."""

from __future__ import annotations

import base64
import importlib
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "docvision" / "scripts"))
from dv.base import DocVisionError, Options

TOKEN_NAMES = ("DOCVISION_PADDLE_TOKEN", "PADDLEOCR_API_TOKEN", "AI_STUDIO_TOKEN", "PADDLEOCR_ACCESS_TOKEN")
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")


class PaddleCloudParsingTests(unittest.TestCase):
    def test_recognized_footnote_and_chart_are_retained_once_in_markdown_and_page_read(self):
        from dv import read
        from dv.base import RawDoc
        from dv.output import write_document
        from dv.providers import paddle_cloud
        from dv.providers.common import assemble_markdown

        note = r'FootnoteMarker: $q \cdot k = \sum_{i=1}^{d_k} q_i k_i$.'
        chart = '| ChartMarker | 1.5 |'
        for already_present in (False, True):
            with self.subTest(already_present=already_present), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                source = root / 'fixture.png'
                source.write_bytes(PNG)
                markdown = '# Main body'
                if already_present:
                    markdown += '\n\n' + note.replace(' ', '  ') + '\n\n' + chart
                payload = {'result': {'layoutParsingResults': [{
                    'markdown': {'text': markdown},
                    'prunedResult': {'width': 100, 'height': 100, 'parsing_res_list': [
                        {'block_label': 'footnote', 'block_content': note},
                        {'block_label': 'chart', 'block_content': chart},
                    ]},
                }]}}
                opts = Options(provider='paddleocr-cloud', images=False)
                with patch.object(paddle_cloud.util, 'download', side_effect=AssertionError('offline fixture')):
                    pages, assets = paddle_cloud._parse(json.dumps(payload).encode(), [0], opts,
                                                        time.monotonic() + 5)
                raw = RawDoc(markdown=assemble_markdown(pages), pages=pages, assets=assets,
                             provider='paddleocr-cloud')
                out = write_document(raw, str(source), opts, out_root=root / 'out', info={'pages': 1})
                main = (out / f'{out.name}.md').read_text(encoding='utf-8')
                page = json.loads(read.read(out, page=1, as_json=True))['pages'][0]['markdown']
                for body in (main, page):
                    self.assertEqual(body.count('FootnoteMarker'), 1)
                    self.assertEqual(body.count('ChartMarker'), 1)
                    self.assertIn(''.join(note.split()), ''.join(body.split()))
                self.assertEqual(pages[0].blocks[0].text, note)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send(self, status, value, mime="application/json"):
        body = value if isinstance(value, bytes) else json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        self.server.calls.append(("POST", self.path, dict(self.headers), body))
        self.send(self.server.submit_status, self.server.submit_body)

    def do_GET(self):
        self.server.calls.append(("GET", self.path, dict(self.headers), b""))
        if self.path.endswith("/job-1"):
            state = self.server.states.pop(0) if len(self.server.states) > 1 else self.server.states[0]
            data = {"jobId": "job-1", "state": state, "errorMsg": "bad PDF",
                    "resultUrl": {"jsonUrl": self.server.base + "/result.jsonl"}}
            self.send(200, {"code": 0, "data": data})
        elif self.path == "/result.jsonl":
            body = self.server.jsonl
            if body is None:
                body = b"\n".join(json.dumps({"result": {"layoutParsingResults": [p]}}).encode()
                                  for p in self.server.pages)
            self.send(200, body, "application/jsonl")
        elif self.path.startswith("/asset"):
            self.send(self.server.asset_status, PNG, "image/png")
        else:
            self.send(404, {"msg": "not found"})


class PaddleCloudTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.server.base = f"http://127.0.0.1:{cls.server.server_port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.module = importlib.import_module("dv.providers.paddle_cloud")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="paddle-contract-")
        self.addCleanup(self.tmp.cleanup)
        self.image = Path(self.tmp.name) / "中文截图.png"
        self.image.write_bytes(PNG)
        env = {k: v for k, v in os.environ.items() if k not in TOKEN_NAMES}
        env["PADDLEOCR_ACCESS_TOKEN"] = "fixture-token"
        env["DOCVISION_CONFIG"] = str(Path(self.tmp.name) / "config.json")
        self.env = patch.dict(os.environ, env, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.cfg = patch.object(self.module.config, "load", return_value={
            "remote": {"paddle_base": self.server.base + "/api/v2/ocr/jobs", "consent": "remote"}})
        self.cfg.start()
        self.addCleanup(self.cfg.stop)
        self.server.calls = []
        self.server.submit_status = 200
        self.server.submit_body = {"code": 0, "data": {"jobId": "job-1"}}
        self.server.states = ["done"]
        self.server.asset_status = 200
        self.server.jsonl = None
        self.server.pages = [self.page(0)]

    def page(self, index):
        return {"markdown": {"text": "# Example\n\n![figure](images/a.png)",
                             "images": {"images/a.png": self.server.base + f"/asset-{index}.png"}},
                "prunedResult": {"page_index": index, "width": 1000, "height": 2000,
                                 "parsing_res_list": [
                                     {"block_label": "formula", "block_content": "E=mc^2",
                                      "block_bbox": [100, 200, 900, 400]},
                                     {"block_label": "image", "block_content": "<img src=\"images/a.png\">",
                                      "block_bbox": [100, 500, 900, 1000]}]}}

    def opts(self, **kwargs):
        return Options(provider="paddleocr-cloud", allow_remote=True, timeout=2, **kwargs)

    def test_url_contract_page_mapping_and_collision_free_assets(self):
        self.server.pages = [self.page(0), self.page(1)]
        doc, meta = self.module.convert("https://example.org/paper.pdf", self.opts(pages="2,4", mode="chart", keep_raw=True))
        self.assertEqual([p.page for p in doc.pages], [2, 4])
        self.assertEqual(doc.pages[0].blocks[0].bbox, [0.1, 0.1, 0.9, 0.2])
        self.assertEqual(doc.pages[0].blocks[0].type, "formula")
        self.assertIn("E=mc^2", doc.pages[0].blocks[0].markdown)
        self.assertEqual(len(doc.assets), 2)
        self.assertNotEqual(doc.pages[0].blocks[1].asset, doc.pages[1].blocks[1].asset)
        for page in doc.pages:
            self.assertNotIn("images/a.png", page.markdown)
            self.assertIn(page.blocks[1].asset, page.markdown)
        self.assertEqual(meta["job_id"], "job-1")
        self.assertTrue(doc.raw_files)
        post = self.server.calls[0]
        body = json.loads(post[3])
        self.assertEqual(body["fileUrl"], "https://example.org/paper.pdf")
        self.assertEqual(body["pageRanges"], "2,4")
        self.assertEqual(body["model"], "PaddleOCR-VL-1.6")
        self.assertTrue(body["optionalPayload"]["useChartRecognition"])
        for method, path, headers, _ in self.server.calls:
            if path.startswith("/api/v2/"):
                self.assertEqual(headers.get("Authorization"), "Bearer fixture-token")
            else:
                self.assertNotIn("Authorization", headers)

    def test_local_multipart_and_model_override(self):
        doc, _ = self.module.convert(str(self.image), self.opts(extra={"model": "PaddleOCR-VL-1.5"}))
        self.assertEqual(doc.provider, "paddleocr-cloud")
        _, _, headers, raw = self.server.calls[0]
        message = BytesParser(policy=policy.default).parsebytes(
            ("Content-Type: " + headers["Content-Type"] + "\r\nMIME-Version: 1.0\r\n\r\n").encode() + raw)
        fields = {p.get_param("name", header="content-disposition"): p for p in message.iter_parts()}
        self.assertEqual(fields["file"].get_payload(decode=True), PNG)
        self.assertEqual(fields["model"].get_content().strip(), "PaddleOCR-VL-1.5")
        self.assertFalse(json.loads(fields["optionalPayload"].get_content())["useDocUnwarping"])

    def test_cropped_formula_and_table_use_specialist_prompt(self):
        for task in ('formula', 'table'):
            with self.subTest(task=task):
                _, plan = self.module.convert(str(self.image), self.opts(dry_run=True,
                    extra={'refine_task': task, 'refine_is_region': True}))
                options = plan['payload_summary']['optionalPayload']
                self.assertFalse(options['useLayoutDetection'])
                self.assertEqual(options['promptLabel'], task)
                self.assertTrue(options['formatBlockContent'])
                self.assertTrue(options['showFormulaNumber'])

    def test_whole_page_formula_review_preserves_layout_detection(self):
        _, plan = self.module.convert(str(self.image), self.opts(dry_run=True,
            extra={'refine_task': 'formula', 'refine_is_region': False}))
        options = plan['payload_summary']['optionalPayload']
        self.assertNotEqual(options.get('useLayoutDetection'), False)
        self.assertTrue(options['showFormulaNumber'])

    def test_original_page_indices_are_preserved(self):
        self.server.pages = [self.page(1), self.page(3)]
        doc, _ = self.module.convert("https://example.org/a.pdf", self.opts(pages="2,4"))
        self.assertEqual([p.page for p in doc.pages], [2, 4])

    def test_dry_run_needs_no_key_or_network(self):
        for name in TOKEN_NAMES:
            os.environ.pop(name, None)
        doc, meta = self.module.convert(str(self.image), self.opts(dry_run=True))
        self.assertIsNone(doc)
        self.assertEqual(meta["provider"], "paddleocr-cloud")
        self.assertEqual(self.server.calls, [])

    def test_all_token_aliases(self):
        # Preserve OS/OpenSSL environment needed by Windows Python runtimes;
        # isolate credentials, not the operating system itself.
        environment = {key: value for key, value in os.environ.items() if key not in TOKEN_NAMES}
        for name in TOKEN_NAMES:
            with self.subTest(name=name), patch.dict(os.environ, {**environment, name: "fixture-token"}, clear=True):
                doc, _ = self.module.convert(str(self.image), self.opts(extra={'cloud_new_attempt': True}))
                self.assertEqual(len(doc.pages), 1)

    def test_missing_token_fails_before_submission(self):
        for name in TOKEN_NAMES:
            os.environ.pop(name, None)
        with self.assertRaisesRegex(DocVisionError, "token"):
            self.module.convert(str(self.image), self.opts())
        self.assertEqual(self.server.calls, [])

    def test_remote_permission_is_required(self):
        with self.assertRaisesRegex(DocVisionError, "allow-remote"):
            self.module.convert(str(self.image), Options())
        self.assertEqual(self.server.calls, [])

    def test_unknown_length_pdf_url_requires_bounded_pages(self):
        with self.assertRaisesRegex(DocVisionError, "page"):
            self.module.convert("https://example.org/book.pdf", self.opts())
        self.assertEqual(self.server.calls, [])

    def test_page_limit_is_enforced_before_submission(self):
        for pages in ("1-1001", "1001"):
            with self.subTest(pages=pages), self.assertRaisesRegex(DocVisionError, "1000"):
                self.module.convert("https://example.org/book.pdf", self.opts(pages=pages))
        with patch.object(self.module, "inspect_input", return_value={"is_pdf": True, "is_image": False,
                          "pages": 1001, "bytes": 100, "suffix": ".pdf"}):
            with self.assertRaisesRegex(DocVisionError, "1000"):
                self.module.convert(str(self.image), self.opts())
        self.assertEqual(self.server.calls, [])

    def test_mismatched_page_count_fails(self):
        with self.assertRaisesRegex(DocVisionError, "page"):
            self.module.convert("https://example.org/a.pdf", self.opts(pages="2,4"))

    def test_http_and_business_errors_are_not_resubmitted(self):
        for status, payload in ((401, {"code": 403, "msg": "bad token fixture-token"}),
                                (200, {"code": 12001, "msg": "daily quota"})):
            self.server.calls = []
            self.server.submit_status = status
            self.server.submit_body = payload
            with self.subTest(status=status), self.assertRaises(DocVisionError) as caught:
                self.module.convert(str(self.image), self.opts(extra={'cloud_new_attempt': True}))
            self.assertNotIn("fixture-token", str(caught.exception))
            self.assertEqual(len(self.server.calls), 1)

    def test_failed_job_is_not_resubmitted(self):
        self.server.states = ["failed"]
        with self.assertRaisesRegex(DocVisionError, "bad PDF"):
            self.module.convert(str(self.image), self.opts())
        self.assertEqual(sum(c[0] == "POST" for c in self.server.calls), 1)

    def test_pending_job_has_bounded_timeout(self):
        self.server.states = ["pending"]
        opts = self.opts()
        opts.timeout = 1
        with self.assertRaisesRegex(DocVisionError, "timed out"):
            self.module.convert(str(self.image), opts)
        self.assertEqual(sum(c[0] == "POST" for c in self.server.calls), 1)

    def test_loopback_job_is_resumed_after_poll_disconnect_without_second_post(self):
        from dv import cloud_jobs
        original_api = self.module._api
        def interrupted(url, token, deadline, **kwargs):
            if kwargs.get('body') is not None or kwargs.get('payload') is not None:
                return original_api(url, token, deadline, **kwargs)
            raise TimeoutError('fixture disconnected after job receipt')
        opts = self.opts(keep_raw=True)
        opts.output = Path(self.tmp.name) / 'recovered'
        with patch.object(self.module, '_api', side_effect=interrupted):
            with self.assertRaises(DocVisionError):
                self.module.convert(str(self.image), opts)
        task_id = opts.extra['_cloud_task_id']
        self.assertEqual(cloud_jobs.load(task_id)['job_id'], 'job-1')
        result = self.module.resume_job(task_id, allow_remote=True, timeout=5)
        self.assertEqual(result['state'], 'done')
        self.assertTrue((Path(result['output_dir']) / 'raw' / 'paddle-result.jsonl').is_file())
        self.assertEqual(sum(c[0] == 'POST' for c in self.server.calls), 1)

    def test_malformed_jsonl_fails(self):
        self.server.jsonl = b'{"result":'
        with self.assertRaisesRegex(DocVisionError, "JSONL"):
            self.module.convert(str(self.image), self.opts())

    def test_missing_image_resource_fails_explicitly(self):
        self.server.asset_status = 404
        with self.assertRaisesRegex(DocVisionError, "resource"):
            self.module.convert(str(self.image), self.opts())

    def test_malformed_layout_details_raise_actionable_error(self):
        self.server.pages[0]["prunedResult"] = "invalid layout"
        with self.assertRaisesRegex(DocVisionError, "layout"):
            self.module.convert(str(self.image), self.opts())

    def test_duplicate_source_pages_are_rejected(self):
        self.server.pages = [self.page(0), self.page(0)]
        with self.assertRaisesRegex(DocVisionError, "duplicate"):
            self.module.convert("https://example.org/a.pdf", self.opts(pages="2,4"))

    def test_images_disabled_keep_explicit_remote_links(self):
        doc, _ = self.module.convert(str(self.image), self.opts(images=False))
        self.assertEqual(doc.assets, {})
        self.assertIn(self.server.base + "/asset-0.png", doc.markdown)
        self.assertFalse(any(c[1].startswith("/asset") for c in self.server.calls))

    def test_reordered_original_indices_map_by_identity(self):
        self.server.pages = [self.page(3), self.page(1)]
        doc, _ = self.module.convert("https://example.org/a.pdf", self.opts(pages="2,4"))
        self.assertEqual([p.page for p in doc.pages], [2, 4])
        self.assertIn("paddle-p0002", doc.pages[0].markdown)

    def test_written_document_contains_only_resolvable_local_image_links(self):
        from dv.output import write_document
        from dv.verify import verify_document
        opts = self.opts(keep_raw=True)
        doc, meta = self.module.convert(str(self.image), opts)
        out = write_document(doc, str(self.image), opts, out_root=Path(self.tmp.name) / "out",
                             raw_meta=meta, info={"pages": 1})
        content = json.loads((out / "content.json").read_text(encoding="utf-8"))
        page = content["pages"][0]
        self.assertIn("assets/paddle-p0001-image-1.png", page["markdown"])
        self.assertEqual(page["blocks"][1]["asset"], "assets/paddle-p0001-image-1.png")
        self.assertTrue((out / page["blocks"][1]["asset"]).is_file())
        self.assertTrue((out / "raw" / "paddle-result.jsonl").is_file())
        self.assertNotEqual(verify_document(out)["status"], "fail")

    def test_oversized_upload_is_rejected_without_reading_or_network(self):
        info = {"is_image": True, "pages": None, "bytes": 51 * 1024 * 1024, "suffix": ".png"}
        with patch.object(self.module, "inspect_input", return_value=info):
            with self.assertRaisesRegex(DocVisionError, "50 MB"):
                self.module.convert(str(self.image), self.opts())
        self.assertEqual(self.server.calls, [])


if __name__ == "__main__":
    unittest.main()
