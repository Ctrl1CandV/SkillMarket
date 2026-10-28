"""Official PaddleOCR asynchronous jobs API, using only the standard library.

Protocol checked 2026-10-28 against PaddleOCR's ``_api_client/_http.py`` and
``_poller.py`` and https://ai.baidu.com/ai-doc/AISTUDIO/fml7mozw5 .
The service quota is an account policy, not an extraction quality guarantee.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from .. import config, util
from ..base import DocVisionError, Options, RawBlock, RawDoc, RawPage, block_markdown
from ..detect import inspect_input
from .common import assemble_markdown, map_block_type

JOBS_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
TOKEN_NAMES = ("DOCVISION_PADDLE_TOKEN", "PADDLEOCR_ACCESS_TOKEN", "PADDLEOCR_API_TOKEN", "AI_STUDIO_TOKEN", "PADDLEAPIKEY")
_IMAGE_LINK = re.compile(r'(!\[[^\]]*\]\()([^\s)]+)(\))|(<img\b[^>]*\bsrc=[\"\'])([^\"\']+)([\"\'])', re.I)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Do not forward document bytes or the API token to a redirect target.
        return None


def _remaining(deadline: float, cap: float = 120) -> float:
    left = deadline - time.monotonic()
    if left <= 0:
        raise DocVisionError("PaddleOCR job timed out.", hint="Reduce the selected pages or raise --timeout; no job was resubmitted.")
    return min(cap, left)


def _api(url: str, token: str, deadline: float, *, payload: dict | None = None,
         body: bytes | None = None, content_type: str | None = None) -> dict:
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        content_type = "application/json"
    req = urllib.request.Request(url, data=body, method="POST" if body is not None else "GET",
                                 headers={"Authorization": "Bearer " + token, "User-Agent": "docvision/0.1"})
    if content_type:
        req.add_header("Content-Type", content_type)
    try:
        with urllib.request.build_opener(_NoRedirect).open(req, timeout=_remaining(deadline)) as response:
            status, raw = response.status, response.read()
    except urllib.error.HTTPError as exc:
        status, raw = exc.code, exc.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        detail = util.redact(str(exc), [token])
        raise DocVisionError(f"PaddleOCR network request failed: {detail}",
                             hint="Check connectivity. The submission is not automatically retried.") from exc
    text = raw.decode("utf-8", errors="replace")
    try:
        result = json.loads(text)
    except ValueError as exc:
        raise DocVisionError(f"PaddleOCR returned non-JSON (HTTP {status}).", code=str(status)) from exc
    if not isinstance(result, dict):
        raise DocVisionError("PaddleOCR response must be a JSON object.")
    if status != 200 or result.get("code") not in (0, None):
        code = result.get("code") or status
        message = util.redact(str(result.get("msg") or result.get("message") or "request rejected")[:600], [token])
        raise DocVisionError(f"PaddleOCR error ({code}): {message}", code=str(code),
                             hint=util.error_hint_for_http(status, message))
    data = result.get("data")
    if not isinstance(data, dict):
        raise DocVisionError("PaddleOCR response is missing its data object.")
    return data


def _selection(info: dict, source: str, opts: Options) -> list[int]:
    """Bound the request before upload and retain original zero-based pages."""
    total = info.get("pages")
    if total is not None and total > 1000:
        raise DocVisionError("PaddleOCR accepts at most 1000 pages per file; split this PDF before upload.")
    if info.get("bytes") and info["bytes"] > 50 * 1024 * 1024:
        raise DocVisionError("PaddleOCR local uploads are limited to 50 MB.", hint="Split the file before uploading.")
    if info.get("is_image"):
        total = 1
    elif not info.get("is_pdf"):
        raise DocVisionError("PaddleOCR cloud accepts PDF or image files here; use a URL with a recognized suffix.")
    spec = opts.pages
    if spec and spec.strip().lower() != "all":
        # Reject excessive ranges before parse_pages could allocate a large list.
        if any(int(n) > 1000 for n in re.findall(r"\d+", spec)):
            raise DocVisionError("PaddleOCR page ranges must stay within the first 1000 source pages.")
        indices = util.parse_pages(spec, total if "r" in spec.lower() else None)
        if not indices or any(i < 0 or (total is not None and i >= total) for i in indices):
            raise DocVisionError("PaddleOCR selected page range is outside the source document.")
        return indices
    if total is None:
        raise DocVisionError("PaddleOCR needs a known page count or an explicit bounded --pages range for PDF URLs.",
                             hint="Choose at most 1000 source pages or download/split the PDF locally to avoid silent truncation.")
    if total < 1:
        raise DocVisionError("PaddleOCR source has no pages.")
    return list(range(total))


def _multipart(path: Path, fields: dict) -> tuple[bytes, str]:
    boundary = "docvision-" + uuid.uuid4().hex
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend([f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n".encode(),
                       str(value).encode("utf-8"), b"\r\n"])
    # Keep user filenames out of MIME headers and avoid Unicode/header escaping.
    name = "docvision-" + util.short_hash(str(path.resolve())) + path.suffix.lower()
    chunks.extend([f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{name}\"\r\nContent-Type: {util.mime_for(path)}\r\n\r\n".encode(),
                   path.read_bytes(), f"\r\n--{boundary}--\r\n".encode()])
    return b"".join(chunks), "multipart/form-data; boundary=" + boundary


def _rewrite(markdown: str, mapping: dict[str, str]) -> str:
    def replace(match: re.Match) -> str:
        if match.group(1):
            return match.group(1) + mapping.get(match.group(2), match.group(2)) + match.group(3)
        return match.group(4) + mapping.get(match.group(5), match.group(5)) + match.group(6)
    return _IMAGE_LINK.sub(replace, markdown or "")


def _page_items(data: bytes) -> list[dict]:
    pages: list[dict] = []
    try:
        for line in data.decode("utf-8-sig").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            items = row["result"]["layoutParsingResults"]
            if not isinstance(items, list) or any(not isinstance(p, dict) for p in items):
                raise TypeError("layoutParsingResults must be an array of page objects")
            pages.extend(items)
    except (ValueError, KeyError, TypeError, UnicodeError) as exc:
        raise DocVisionError("PaddleOCR returned malformed JSONL document results.") from exc
    return pages


def _page_numbers(items: list[dict], expected: list[int]) -> list[int]:
    if len(items) != len(expected):
        raise DocVisionError(f"PaddleOCR returned {len(items)} pages for {len(expected)} requested source pages.",
                             hint="The result may be incomplete; do not cite it as a complete conversion.")
    if any(p.get("prunedResult") is not None and not isinstance(p["prunedResult"], dict) for p in items):
        raise DocVisionError("PaddleOCR returned malformed page layout details.")
    indices = [(p.get("prunedResult") or {}).get("page_index") for p in items]
    if all(i is None for i in indices):
        # The official SDK preserves result order when the layout index is absent.
        return [i + 1 for i in expected]
    if not all(isinstance(i, int) and not isinstance(i, bool) for i in indices):
        raise DocVisionError("PaddleOCR returned missing or invalid page indices.")
    if len(set(indices)) != len(indices):
        raise DocVisionError("PaddleOCR returned duplicate page indices.")
    if set(indices) == set(expected):
        return [i + 1 for i in indices]
    if set(indices) == set(range(len(expected))):
        return [expected[i] + 1 for i in indices]
    raise DocVisionError("PaddleOCR page indices do not match the requested source pages.")


def _parse(data: bytes, expected: list[int], opts: Options, deadline: float) -> tuple[list[RawPage], dict[str, bytes]]:
    items = _page_items(data)
    numbers = _page_numbers(items, expected)
    pages: list[RawPage] = []
    assets: dict[str, bytes] = {}
    for item, page_no in zip(items, numbers):
        pruned = item.get("prunedResult") or {}
        markdown = item.get("markdown")
        if not isinstance(pruned, dict) or not isinstance(markdown, dict) or not isinstance(markdown.get("text"), str):
            raise DocVisionError("PaddleOCR page is missing its Markdown or has malformed layout details.")
        mapping: dict[str, str] = {}
        for kind, resources in (("image", markdown.get("images") or {}), ("output", item.get("outputImages") or {})):
            if not isinstance(resources, dict):
                raise DocVisionError("PaddleOCR page resource map is malformed.")
            for idx, (original, url) in enumerate(resources.items(), 1):
                if not isinstance(url, str) or not util.is_url(url):
                    raise DocVisionError("PaddleOCR returned an invalid resource URL.")
                if not opts.images:
                    mapping[str(original)] = url
                    continue
                suffix = Path(urllib.parse.urlsplit(url).path).suffix.lower()
                suffix = suffix if suffix in util.SUPPORTED_IMAGE_EXT else ".png"
                name = f"paddle-p{page_no:04d}-{kind}-{idx}{suffix}"
                try:
                    assets[name] = util.download(url, timeout=_remaining(deadline), max_bytes=40 * 1024 * 1024)
                except (DocVisionError, TimeoutError, OSError) as exc:
                    raise DocVisionError(f"PaddleOCR image resource could not be saved for source page {page_no}.",
                                         hint="The parse is incomplete; check service result links before retrying.") from exc
                mapping[str(original)] = name
                mapping[url] = name
        width, height = pruned.get("width"), pruned.get("height")
        page = RawPage(page=page_no, width=width, height=height, markdown=_rewrite(markdown["text"], mapping))
        blocks = pruned.get("parsing_res_list") or []
        if not isinstance(blocks, list):
            raise DocVisionError("PaddleOCR page block list is malformed.")
        for block in blocks:
            if not isinstance(block, dict):
                raise DocVisionError("PaddleOCR returned a malformed layout block.")
            label = str(block.get("block_label") or "text")
            kind = map_block_type(label)
            content = str(block.get("block_content") or "")
            md = _rewrite(block_markdown(kind, content) if kind not in {"image", "chart"} else content, mapping)
            asset = None
            if kind in {"image", "chart"}:
                targets = [m.group(2) or m.group(5) for m in _IMAGE_LINK.finditer(md)]
                asset = next((t for t in targets if t in assets), None)
                if not asset and content in mapping and mapping[content] in assets:
                    asset = mapping[content]
                if asset and not md.strip():
                    md = f"![{kind}]({asset})"
            page.blocks.append(RawBlock(type=kind, text=content, markdown=md, page=page_no,
                                        bbox=util.normalize_bbox_pixels(block.get("block_bbox"), width, height),
                                        asset=asset, meta={"provider_type": label}))
        if not page.blocks:
            page.blocks.append(RawBlock(type="text", text=page.markdown, markdown=page.markdown, page=page_no))
        pages.append(page)
    return sorted(pages, key=lambda p: p.page), assets


def convert(source: str, opts: Options) -> tuple:
    info = inspect_input(source, opts)
    expected = _selection(info, source, opts)
    endpoint = (config.load().get("remote", {}).get("paddle_base") or JOBS_URL).rstrip("/")
    parsed = urllib.parse.urlsplit(endpoint)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.query or parsed.fragment:
        raise DocVisionError("remote.paddle_base must be the full PaddleOCR jobs HTTP endpoint without a query.")
    model = str(opts.extra.get("model") or "PaddleOCR-VL-1.6")
    options = {"useDocOrientationClassify": False, "useDocUnwarping": False,
               "useChartRecognition": opts.mode == "chart"}
    payload = {"model": model, "optionalPayload": options}
    if opts.pages and opts.pages.strip().lower() != "all":
        payload["pageRanges"] = ",".join(str(i + 1) for i in expected)
    if opts.dry_run:
        return None, {"provider": "paddleocr-cloud", "endpoint": endpoint, "model": model,
                      "upload": not util.is_url(source), "pages": [i + 1 for i in expected],
                      "payload_summary": payload}
    if not opts.allow_remote:
        raise DocVisionError("PaddleOCR cloud requires --allow-remote before uploading a document.")
    token = util.env_value(*TOKEN_NAMES)
    if not token:
        raise DocVisionError("PaddleOCR cloud needs an AI Studio access token.",
                             hint="Set PADDLEOCR_ACCESS_TOKEN (or DOCVISION_PADDLE_TOKEN); never paste it into a document or commit it.")
    started = time.monotonic()
    deadline = started + opts.timeout
    if util.is_url(source):
        task = _api(endpoint, token, deadline, payload={**payload, "fileUrl": source})
    else:
        fields = {**payload, "optionalPayload": json.dumps(options)}
        body, content_type = _multipart(Path(source), fields)
        task = _api(endpoint, token, deadline, body=body, content_type=content_type)
    job_id = task.get("jobId")
    if not isinstance(job_id, str) or not job_id:
        raise DocVisionError("PaddleOCR did not return a jobId; the request is not automatically resubmitted.")
    poll_url = endpoint + "/" + urllib.parse.quote(job_id, safe="")
    while True:
        item = _api(poll_url, token, deadline)
        state = item.get("state")
        if state == "done":
            break
        if state == "failed":
            message = util.redact(str(item.get("errorMsg") or "no detail"), [token])
            raise DocVisionError(f"PaddleOCR job failed: {message}", code="job_failed")
        if state not in {"pending", "running"}:
            raise DocVisionError(f"PaddleOCR returned an unknown job state: {state!r}.")
        time.sleep(min(2, _remaining(deadline)))
    result = item.get("resultUrl")
    result_url = result.get("jsonUrl") if isinstance(result, dict) else None
    if not isinstance(result_url, str) or not util.is_url(result_url):
        raise DocVisionError("PaddleOCR finished without a JSONL result URL.")
    data = util.download(result_url, timeout=_remaining(deadline), max_bytes=200 * 1024 * 1024)
    pages, assets = _parse(data, expected, opts, deadline)
    elapsed = round(time.monotonic() - started, 3)
    doc = RawDoc(markdown=assemble_markdown(pages), pages=pages, assets=assets,
                 provider="paddleocr-cloud", model=model,
                 usage={"job_id": job_id, "elapsed_seconds": elapsed, "pages_processed": len(pages)})
    if opts.keep_raw:
        doc.raw_files["paddle-result.jsonl"] = data
    return doc, {"provider": "paddleocr-cloud", "model": model, "job_id": job_id,
                 "pages": len(pages), "elapsed_seconds": elapsed}
