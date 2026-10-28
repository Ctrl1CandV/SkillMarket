"""MinerU cloud adapters: Standard API (zip) and Agent API (Markdown)."""

from __future__ import annotations

import json
import time
from pathlib import Path

from .. import config, util
from ..base import DocVisionError, Options, RawDoc
from ..detect import inspect_input
from .common import pages_from_markdown, raw_from_mineru_zip

STANDARD_BASE = "https://mineru.net/api/v4"
AGENT_BASE = "https://mineru.net/api/v1/agent"


def _token() -> str:
    token = config.remote_keys().get("mineru")
    if not token:
        raise DocVisionError(
            "MinerU Standard API needs a token.",
            hint="Create one at https://mineru.net/apiManage/token and set MINERU_TOKEN (do not commit it).",
        )
    return token


def _api(method: str, url: str, payload=None, *, token: str | None = None,
         timeout: int = 120) -> dict:
    headers = {}
    if token:
        headers["Authorization"] = "Bearer " + token
    status, body = (util.post_json(url, payload, timeout=timeout, headers=headers)
                    if method == "POST" else
                    util.get_json(url, timeout=timeout, headers=headers))
    text = body.decode("utf-8", errors="replace")
    try:
        data = json.loads(text)
    except ValueError:
        raise DocVisionError(f"MinerU returned non-JSON (HTTP {status}): {text[:500]}",
                             hint=util.error_hint_for_http(status, text))
    if status >= 400 or data.get("code") not in (0, None):
        code = data.get("code")
        msg = data.get("msg") or data.get("message") or text[:400]
        if code in ("A0202", "A0211") or status in (401, 403):
            raise DocVisionError(
                f"MinerU authentication failed ({code or status}): {msg}",
                hint="Refresh MINERU_TOKEN at https://mineru.net/apiManage/token.",
                code=str(code or status),
            )
        if code in (-60018, -60019) or "quota" in str(msg).lower():
            raise DocVisionError(
                f"MinerU quota/priority limit reached ({code}): {msg}",
                hint="Wait for the daily reset or reduce pages; do not retry the same batch immediately.",
                code=str(code),
            )
        raise DocVisionError(f"MinerU error ({code or status}): {msg}",
                             hint=util.error_hint_for_http(status, text), code=str(code or status))
    return data.get("data") if isinstance(data.get("data"), dict) else data


def _poll(url: str, token: str, *, deadline: float, interval: float = 2.0,
          extract=None) -> dict:
    """Poll a MinerU task/batch until done; `extract` maps response -> item."""
    while True:
        data = _api("GET", url, token=token, timeout=60)
        item = extract(data) if extract else data
        state = (item or {}).get("state")
        if state == "done":
            return item or {}
        if state in {"failed", "canceled"}:
            raise DocVisionError(
                f"MinerU parse ended as {state}: {(item or {}).get('err_msg') or 'no detail'}",
                hint="Check the file format/limits, or retry with another provider.",
            )
        if time.monotonic() > deadline:
            raise DocVisionError(
                "MinerU parse timed out.",
                hint="Raise --timeout, reduce --pages, or use a smaller file.",
            )
        time.sleep(interval)


def _payload(opts: Options, info: dict) -> dict:
    payload = {
        "model_version": opts.extra.get("model_version") or "vlm",
        "is_ocr": bool(opts.mode == "ocr" or info.get("needs_ocr")
                       or opts.mode in {"quality"}),
        "enable_formula": opts.mode != "text",
        "enable_table": opts.mode != "text",
        "language": opts.lang or "ch",
    }
    if opts.pages:
        payload["page_ranges"] = opts.pages
    if opts.extra.get("extra_formats"):
        payload["extra_formats"] = list(opts.extra["extra_formats"])
    return payload


def _download_zip(url: str, opts: Options) -> RawDoc:
    data = util.download(url, timeout=min(opts.timeout, 600), max_bytes=1024 * 1024 * 1024)
    return raw_from_mineru_zip(data, provider="mineru-cloud", model="MinerU 4 cloud")



def _match_batch_item(data: dict, data_id: str, name: str) -> dict:
    items = data.get("extract_result") or []
    for item in items:
        if item.get("data_id") == data_id or item.get("file_name") == name:
            return item
    # Some API responses omit data_id for a single-file batch; a lone item is
    # unambiguous, but a multi-file batch must never use another file's state.
    if len(items) == 1:
        return items[0]
    return {"state": "pending"}

def convert_standard(source: str, opts: Options) -> tuple:
    info = inspect_input(source, opts)
    token = _token()
    payload = _payload(opts, info)
    deadline = time.monotonic() + opts.timeout
    data_id = util.data_id_for(source)
    if opts.dry_run:
        return None, {"provider": "mineru-cloud", "endpoint": STANDARD_BASE,
                      "payload": payload, "data_id": data_id, "upload": not util.is_url(source)}
    if util.is_url(source):
        task = _api("POST", f"{STANDARD_BASE}/extract/task", {**payload, "url": source,
                                                             "data_id": data_id},
                    token=token)
        task_id = task["task_id"]
        item = _poll(f"{STANDARD_BASE}/extract/task/{task_id}", token, deadline=deadline)
        if not item.get("full_zip_url"):
            raise DocVisionError("MinerU task finished without a result archive.")
        doc = _download_zip(item["full_zip_url"], opts)
        return doc, {"provider": "mineru-cloud", "task_id": task_id, "mode": "url"}

    path = Path(source)
    name = f"docvision-{util.short_hash(str(path.resolve()), 10)}{path.suffix.lower()}"
    entry = {"name": name, "data_id": data_id}
    if "is_ocr" in payload:
        entry["is_ocr"] = payload["is_ocr"]
    if "page_ranges" in payload:
        entry["page_ranges"] = payload["page_ranges"]
    batch_payload = {k: v for k, v in payload.items() if k not in {"is_ocr", "page_ranges"}}
    batch = _api("POST", f"{STANDARD_BASE}/file-urls/batch",
                 {**batch_payload, "files": [entry]}, token=token)
    batch_id = batch.get("batch_id")
    urls = batch.get("file_urls") or []
    if not batch_id or not urls:
        raise DocVisionError("MinerU did not return a batch upload URL.")
    util.put_file_unsigned(urls[0], path, timeout=min(opts.timeout, 600))
    item = _poll(
        f"{STANDARD_BASE}/extract-results/batch/{batch_id}", token, deadline=deadline,
        extract=lambda data: _match_batch_item(data, data_id, name),
    )
    if not item.get("full_zip_url"):
        raise DocVisionError("MinerU batch finished without a result archive.")
    doc = _download_zip(item["full_zip_url"], opts)
    return doc, {"provider": "mineru-cloud", "batch_id": batch_id, "mode": "upload"}


def convert_agent(source: str, opts: Options) -> tuple:
    """Token-free lightweight API; Markdown only, no images/bboxes."""
    info = inspect_input(source, opts)
    if info.get("pages") and info["pages"] > 20:
        raise DocVisionError("MinerU Agent API accepts at most 20 pages; use the Standard API or a local engine.")
    if info.get("bytes") and info["bytes"] > 10 * 1024 * 1024:
        raise DocVisionError("MinerU Agent API accepts at most 10 MB; use the Standard API or a local engine.")
    payload = {
        "language": opts.lang or "ch",
        "enable_table": opts.mode != "text",
        "enable_formula": opts.mode != "text",
        "is_ocr": bool(info.get("needs_ocr") or opts.mode == "ocr"),
    }
    if opts.pages:
        # Agent accepts only a single page or one contiguous range.
        if "," in opts.pages:
            raise DocVisionError(
                "MinerU Agent cannot handle comma-separated page ranges.",
                hint="Use one range (e.g. 2-6), the Standard API, or a local engine.",
            )
        payload["page_range"] = opts.pages
    if opts.dry_run:
        return None, {"provider": "mineru-agent", "endpoint": AGENT_BASE, "payload": payload}
    deadline = time.monotonic() + opts.timeout
    if util.is_url(source):
        task = _api("POST", f"{AGENT_BASE}/parse/url", {**payload, "url": source}, timeout=60)
        task_id = task["task_id"]
    else:
        path = Path(source)
        task = _api("POST", f"{AGENT_BASE}/parse/file",
                    {**payload, "file_name": path.name}, timeout=60)
        task_id = task["task_id"]
        util.put_file_unsigned(task["file_url"], path, timeout=min(opts.timeout, 300))
    item = _poll(f"{AGENT_BASE}/parse/{task_id}", "", deadline=deadline,
                 interval=3.0, extract=lambda d: d)
    md_url = item.get("markdown_url") if isinstance(item, dict) else None
    if not md_url:
        raise DocVisionError("MinerU Agent finished without a Markdown URL.")
    md = util.download(md_url, timeout=120).decode("utf-8", errors="replace")
    doc = RawDoc(markdown=md, pages=pages_from_markdown(md), provider="mineru-agent",
                 model="MinerU Agent (pipeline)", warnings=[
                     "Agent API returns Markdown only: no images, bboxes, or page structure.",
                     "Agent is a preview/lightweight path; use Standard or local MinerU for formulas, tables and figures.",
                 ], usage={"task_id": task_id})
    return doc, {"provider": "mineru-agent", "task_id": task_id}


def probe_token(token: str | None = None) -> dict:
    token = token or config.remote_keys().get("mineru")
    if not token:
        return {"ok": False, "detail": "MINERU_TOKEN not set"}
    try:
        status, body = util.get_json(
            f"{STANDARD_BASE}/extract/task/00000000-0000-0000-0000-000000000000",
            timeout=20, headers={"Authorization": "Bearer " + token})
        text = body.decode("utf-8", errors="replace")
        if status in (401, 403) or "A0202" in text or "A0211" in text:
            return {"ok": False, "detail": "token rejected (401/A0202)"}
        # A valid token gets a business error such as -60012 (task not found).
        return {"ok": True, "detail": f"accepted (HTTP {status}; no task/quota consumed)"}
    except DocVisionError as exc:
        return {"ok": False, "detail": str(exc)}
