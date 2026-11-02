import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch
import urllib.parse
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "imagecraft/scripts"))
from ic.client import Client
from ic.common import Error


class Handler(BaseHTTPRequestHandler):
    last_body = b""
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "https://example.invalid/private")
            self.end_headers()
            return
        content = json.dumps({"system": {"comfyui_version": "fixture"}}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self):
        Handler.last_body = self.rfile.read(int(self.headers["Content-Length"]))
        content = json.dumps({"prompt_id": json.loads(Handler.last_body)["prompt_id"]}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def test_real_loopback_bypasses_proxy(self):
        with patch.dict("os.environ", {"HTTP_PROXY": "http://127.0.0.1:1", "HTTPS_PROXY": "http://127.0.0.1:1", "NO_PROXY": ""}):
            self.assertIn("system", Client(self.url).request("/system_stats"))

    def test_redirect_is_not_followed(self):
        with self.assertRaises(Error):
            Client(self.url).request("/redirect")

    def test_post_preserves_client_uuid_and_unicode(self):
        prompt_id = str(uuid.uuid4())
        result = Client(self.url).request("/prompt", {"prompt_id": prompt_id, "prompt": "蓝色茶壶"})
        self.assertEqual(result["prompt_id"], prompt_id)
        self.assertEqual(json.loads(Handler.last_body)["prompt"], "蓝色茶壶")


if __name__ == "__main__":
    unittest.main()
