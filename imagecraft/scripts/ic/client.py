from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
import uuid

from .common import Error, endpoint


class HTTPFailure(Error):
    def __init__(self, status: int, detail: str):
        self.status = status
        super().__init__(f"ComfyUI HTTP {status}: {detail[:1500]}")


class NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Error("ComfyUI redirected the request; refusing to leave the selected endpoint")


class Client:
    def __init__(self, url: str, timeout=15):
        self.url, self.timeout = endpoint(url), timeout
        # Never send local prompts through environment/system proxies.
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirects())

    def request(self, path, payload=None, *, raw=None, content_type=None, binary=False):
        if not path.startswith("/") or path.startswith("//"):
            raise Error("Invalid API path")
        headers = {"User-Agent": "imagecraft/0.3.0"}
        if payload is not None:
            raw = json.dumps(payload).encode("utf-8")
            content_type = "application/json"
        if content_type:
            headers["Content-Type"] = content_type
        request = urllib.request.Request(self.url + path, data=raw, headers=headers)
        limit = 64 * 1024 * 1024 if binary else 16 * 1024 * 1024
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                data = response.read(limit + 1)
                if len(data) > limit:
                    raise Error("API response exceeds the size limit")
            return data if binary else json.loads(data)
        except urllib.error.HTTPError as exc:
            detail = exc.read(4096).decode("utf-8", errors="replace")
            raise HTTPFailure(exc.code, detail) from None
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise Error(f"ComfyUI connection/response error ({type(exc).__name__}); a POST may already have reached the server") from None

    def upload(self, content: bytes, job_id: str, index: int) -> str:
        boundary = "imagecraft" + uuid.uuid4().hex
        name, subfolder = f"reference-{index}.png", f"imagecraft/{job_id}"
        fields = {"type": "input", "subfolder": subfolder, "overwrite": "false"}
        parts = []
        for key, value in fields.items():
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
        parts += [f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{name}"\r\nContent-Type: image/png\r\n\r\n'.encode(),
                  content, f"\r\n--{boundary}--\r\n".encode()]
        result = self.request("/upload/image", raw=b"".join(parts), content_type=f"multipart/form-data; boundary={boundary}")
        returned_name = result.get("name", "")
        if (result.get("subfolder", "").replace("\\", "/") != subfolder or result.get("type") != "input"
                or not returned_name.endswith(".png") or any(x in returned_name for x in ("/", "\\", ":", ".."))):
            raise Error("Unexpected uploaded-image location; inspect before retrying")
        return f"{subfolder}/{returned_name}"

    def history(self, prompt_id: str):
        uuid.UUID(prompt_id)
        return self.request(f"/history/{prompt_id}").get(prompt_id)

    def view(self, image: dict) -> bytes:
        if image.get("type") != "output":
            raise Error("Only final output images may be retrieved")
        for key in ("filename", "subfolder"):
            value = image.get(key, "")
            if not isinstance(value, str) or value.startswith(("/", "\\")) or ":" in value or ".." in value.replace("\\", "/").split("/"):
                raise Error("Unsafe output location returned by the server")
        query = urllib.parse.urlencode({k: image.get(k, "") for k in ("filename", "subfolder", "type")})
        return self.request("/view?" + query, binary=True)
