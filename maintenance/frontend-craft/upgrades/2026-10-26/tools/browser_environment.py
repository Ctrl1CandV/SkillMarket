"""Read request metadata from the real browser during local evaluation only."""
from http.server import BaseHTTPRequestHandler, HTTPServer
import json


class EnvironmentHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        payload = json.dumps({
            "user_agent": self.headers.get("User-Agent"),
            "accept_language": self.headers.get("Accept-Language"),
            "method": "headers received by local evaluation server",
        }, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 8767), EnvironmentHandler).serve_forever()
