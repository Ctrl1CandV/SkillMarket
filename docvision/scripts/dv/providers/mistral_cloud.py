"""Mistral OCR adapter (Document AI / OCR 4.x)."""

from __future__ import annotations

import json
import time
from pathlib import Path

from .. import config, util
from ..base import DocVisionError, Options, RawBlock, RawDoc, RawPage, block_markdown
from ..detect import inspect_input
from .common import map_block_type, pages_from_markdown


def _key() -> str:
    key = config.remote_keys().get("mistral")
    if not key:
        raise DocVisionError(
            "Mistral OCR needs an API key.",
            hint="Set MISTRAL_API_KEY from https://console.mistral.ai; do not commit it.",
        )
    return key


def _document(source: str, opts: Options) -> dict:
    if util.is_url(source):
        if util.suffix_of(source) in util.SUPPORTED_IMAGE_EXT:
            return {"type": "image_url", "image_url": source}
        return {"type": "document_url", "document_url": source}
    path = Path(source)
    if path.stat().st_size > 50 * 1024 * 1024:
        raise DocVisionError("Mistral OCR accepts files up to 50 MB.", hint="Split the file or use MinerU.")
    uri = util.data_uri(path.read_bytes(), util.mime_for(path))
    if path.suffix.lower() in util.SUPPORTED_IMAGE_EXT:
        return {"type": "image_url", "image_url": uri}
    return {"type": "document_url", "document_url": uri}


def _normalise_box(bbox, width, height):
    if not bbox or len(bbox) < 4:
        return None
    try:
        x0, y0, x1, y1 = (float(bbox[i]) for i in range(4))
    except (TypeError, ValueError):
        return None
    if max(x0, y0, x1, y1) > 1.5:
        if width and height:
            return util.normalize_bbox_pixels([x0, y0, x1, y1], width, height)
        # Do not pretend a pixel bbox is normalised when dimensions are absent.
        return None
    return util.clamp_bbox([x0, y0, x1, y1])


def convert(source: str, opts: Options) -> tuple:
    key = _key()
    inspect_input(source, opts)
    base = (config.load().get("remote", {}).get("mistral_base")
            or "https://api.mistral.ai/v1").rstrip("/")
    payload = {
        "model": opts.extra.get("model") or "mistral-ocr-latest",
        "document": _document(source, opts) if not opts.dry_run else {"type": "document_url",
                                                                      "document_url": "<file/url>"},
        "table_format": "html",
        "include_image_base64": True,
        "include_blocks": True,
    }
    if opts.dry_run:
        return None, {"provider": "mistral", "endpoint": f"{base}/ocr",
                      "payload_summary": {"model": payload["model"], "table_format": "html",
                                          "include_blocks": True}}
    started = time.monotonic()
    status, body = util.post_json(f"{base}/ocr", payload, timeout=min(opts.timeout, 900),
                                  headers={"Authorization": "Bearer " + key})
    text = body.decode("utf-8", errors="replace")
    try:
        data = json.loads(text)
    except ValueError:
        raise DocVisionError(f"Mistral returned non-JSON (HTTP {status}): {text[:500]}",
                             hint=util.error_hint_for_http(status, text))
    if status >= 400 or data.get("error") or data.get("message") and not data.get("pages"):
        err = data.get("error") or data
        msg = err.get("message") if isinstance(err, dict) else str(err)
        raise DocVisionError(f"Mistral OCR error (HTTP {status}): {msg or text[:400]}",
                             hint=util.error_hint_for_http(status, text))
    pages: list[RawPage] = []
    assets: dict[str, bytes] = {}
    warnings: list[str] = []
    for p_idx, page in enumerate(data.get("pages") or []):
        if not isinstance(page, dict):
            continue
        page_no = int(page.get("index", p_idx)) + 1
        dims = page.get("dimensions") or {}
        width = dims.get("width") or dims.get("dpi_width") or page.get("width")
        height = dims.get("height") or dims.get("dpi_height") or page.get("height")
        rp = RawPage(page=page_no, width=width, height=height)
        page_md = page.get("markdown") or ""
        # Extract inline images/tables before building content blocks.
        for image in page.get("images") or []:
            if not isinstance(image, dict):
                continue
            name = image.get("id") or f"img-{p_idx}-{len(assets)}"
            raw = image.get("image_base64")
            if raw:
                try:
                    assets[name] = util.b64decode(raw)
                except Exception:
                    continue
        for table in page.get("tables") or []:
            if not isinstance(table, dict):
                continue
            tid = table.get("id") or f"table-{p_idx}-{len(assets)}"
            content = table.get("content") or ""
            if content:
                # Replace the link placeholder with the actual table HTML.
                page_md = page_md.replace(f"[{tid}]({tid})", content)
                page_md = page_md.replace(f"[{tid}]", content)
        blocks = page.get("blocks") or []
        if blocks:
            for b_idx, block in enumerate(blocks):
                if not isinstance(block, dict):
                    continue
                label = str(block.get("type") or block.get("label") or "text")
                mapped = map_block_type(label)
                content = block.get("content") or block.get("text") or ""
                if mapped == "table" and block.get("table_html"):
                    content = block["table_html"]
                bbox = _normalise_box(block.get("bbox"), width, height)
                rp.blocks.append(RawBlock(
                    type=mapped, markdown=block_markdown(mapped, str(content)),
                    text=str(content), page=page_no, bbox=bbox,
                    confidence=block.get("confidence"),
                    meta={"provider_type": label, "index": b_idx},
                ))
        if not rp.blocks:
            rp.blocks.append(RawBlock(type="text", markdown=page_md, text=page_md, page=page_no))
        rp.markdown = page_md.strip() or "\n\n".join(b.markdown for b in rp.blocks)
        pages.append(rp)
    markdown = "\n\n".join(f"<!-- page: {p.page} -->\n\n{p.markdown}".strip()
                           for p in pages if p.markdown).strip()
    if not pages:
        markdown = data.get("markdown") or ""
        pages = pages_from_markdown(markdown)
        warnings.append("Mistral returned no page objects; page mapping is approximate.")
    if not markdown:
        markdown = "\n\n".join(p.markdown for p in pages if p.markdown)
    usage = data.get("usage_info") or {}
    usage["elapsed_seconds"] = round(time.monotonic() - started, 2)
    doc = RawDoc(markdown=markdown, pages=pages, assets=assets, provider="mistral",
                 model=data.get("model") or payload["model"], warnings=warnings, usage=usage)
    return doc, {"provider": "mistral", "model": data.get("model") or payload["model"],
                 "pages": len(pages)}
