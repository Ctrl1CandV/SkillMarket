"""Zhipu GLM-OCR cloud adapter (`/paas/v4/layout_parsing`)."""

from __future__ import annotations

import json
import time
from pathlib import Path

from .. import config, util
from ..base import DocVisionError, Options, RawBlock, RawDoc, RawPage, block_markdown
from ..detect import inspect_input
from .common import map_block_type, pages_from_markdown


def _key() -> str:
    key = config.remote_keys().get("glm")
    if not key:
        raise DocVisionError(
            "GLM-OCR needs an API key.",
            hint="Set ZHIPU_API_KEY (or GLM_API_KEY) from https://open.bigmodel.cn; do not commit it.",
        )
    return key


def _file_value(source: str, opts: Options) -> str:
    if util.is_url(source):
        return source
    path = Path(source)
    data = path.read_bytes()
    if path.suffix.lower() == ".pdf" and len(data) > 50 * 1024 * 1024:
        raise DocVisionError("GLM-OCR accepts PDFs up to 50 MB.", hint="Split the PDF or use MinerU.")
    if path.suffix.lower() != ".pdf" and len(data) > 10 * 1024 * 1024:
        raise DocVisionError("GLM-OCR accepts images up to 10 MB.", hint="Downscale the image or use MinerU.")
    return util.data_uri(data, util.mime_for(path))


def _download_image(url: str, opts: Options) -> bytes | None:
    try:
        return util.download(url, timeout=min(opts.timeout, 120), max_bytes=40 * 1024 * 1024)
    except Exception:
        return None


def convert(source: str, opts: Options) -> tuple:
    key = _key()
    info = inspect_input(source, opts)
    if info.get("pages") and info["pages"] > 100:
        raise DocVisionError("GLM-OCR accepts up to 100 pages.", hint="Split the PDF or use MinerU.")
    base = (config.load().get("remote", {}).get("glm_base")
            or "https://open.bigmodel.cn/api/paas/v4").rstrip("/")
    payload = {
        "model": "glm-ocr",
        "file": _file_value(source, opts) if not opts.dry_run else "<base64/url>",
        "return_crop_images": False,
        "need_layout_visualization": False,
    }
    if opts.pages and re_single_range(opts.pages):
        start, end = parse_single_range(opts.pages)
        payload["start_page_id"], payload["end_page_id"] = start, end
    if opts.dry_run:
        return None, {"provider": "glm-cloud", "endpoint": f"{base}/layout_parsing",
                      "payload_summary": {k: v for k, v in payload.items() if k != "file"}}
    started = time.monotonic()
    status, body = util.post_json(f"{base}/layout_parsing", payload,
                                  timeout=min(opts.timeout, 900),
                                  headers={"Authorization": key})
    text = body.decode("utf-8", errors="replace")
    try:
        data = json.loads(text)
    except ValueError:
        raise DocVisionError(f"GLM-OCR returned non-JSON (HTTP {status}): {text[:500]}",
                             hint=util.error_hint_for_http(status, text))
    if status >= 400 or data.get("error"):
        err = data.get("error") or {}
        msg = err.get("message") or data.get("message") or text[:400]
        raise DocVisionError(
            f"GLM-OCR error ({err.get('code') or status}): {msg}",
            hint=util.error_hint_for_http(status, text),
            code=str(err.get("code") or status),
        )
    markdown = data.get("md_results") or data.get("markdown") or ""
    layout = data.get("layout_details") or []
    if isinstance(layout, list) and layout and all(isinstance(x, dict) for x in layout):
        layout = [layout]
    pages: list[RawPage] = []
    assets: dict[str, bytes] = {}
    warnings: list[str] = []
    for p_idx, details in enumerate(layout if isinstance(layout, list) else []):
        page_no = p_idx + 1
        if not isinstance(details, list):
            continue
        rp = RawPage(page=page_no)
        for b_idx, item in enumerate(details):
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or "text")
            mapped = map_block_type(label)
            content = item.get("content") or ""
            bbox = util.clamp_bbox(item.get("bbox_2d"))
            if item.get("width") and item.get("height") and bbox:
                # GLM already documents bbox_2d as normalised; keep it.
                rp.width, rp.height = item.get("width"), item.get("height")
            asset = None
            if mapped == "image" and isinstance(content, str) and content.startswith(("http://", "https://")):
                if opts.images:
                    blob = _download_image(content, opts)
                    if blob:
                        asset = f"glm-page-{page_no:04d}-{b_idx + 1}{Path(content).suffix or '.png'}"
                        assets[asset] = blob
                content = ""
            md = content if mapped == "table" else block_markdown(mapped, str(content))
            if asset:
                md = f"![image]({asset})"
            rp.blocks.append(RawBlock(
                type=mapped, markdown=md, text=str(content), page=page_no,
                bbox=bbox, asset=asset, meta={"provider_type": label, "index": item.get("index")},
            ))
        rp.markdown = "\n\n".join(b.markdown for b in rp.blocks if b.markdown)
        pages.append(rp)
    if not pages:
        pages = pages_from_markdown(markdown)
        warnings.append("GLM-OCR returned no layout details; page mapping is approximate.")
    if not markdown:
        markdown = "\n\n".join(p.markdown for p in pages if p.markdown)
    usage = data.get("usage") or {}
    usage.update({"elapsed_seconds": round(time.monotonic() - started, 2),
                  "request_id": data.get("request_id") or data.get("id")})
    doc = RawDoc(markdown=markdown, pages=pages, assets=assets, provider="glm-cloud",
                 model="GLM-OCR (0.9B)", warnings=warnings, usage=usage)
    return doc, {"provider": "glm-cloud", "endpoint": f"{base}/layout_parsing",
                 "request_id": data.get("request_id") or data.get("id")}


def re_single_range(value: str) -> bool:
    import re
    return bool(re.fullmatch(r"\d+-\d+", value.strip())) and "," not in value


def parse_single_range(value: str) -> tuple[int, int]:
    a, b = value.split("-", 1)
    return int(a), int(b)
