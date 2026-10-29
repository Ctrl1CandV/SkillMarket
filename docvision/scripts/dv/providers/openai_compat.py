"""OpenAI-compatible vision adapter, including Ollama and local vLLM."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from .. import config, focus, util
from ..base import DocVisionError, Options, RawDoc, RawPage, RawBlock
from ..detect import inspect_input

SYSTEM = "You are a precise document OCR and layout engine. Return only the requested Markdown."
PROMPT = """Transcribe page {page} of {total} to GitHub-Flavored Markdown.
Preserve headings, lists, captions and reading order. Use LaTeX for formulas ($...$ or $$...$$).
Use HTML tables when cells are merged. Describe charts and figures briefly in a blockquote; never invent numbers.
Do not add commentary, preamble or a summary. Output only the page content."""


def _endpoint(base_url: str) -> str:
    base = (base_url or "").rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return base + "/chat/completions"


def _key(env_name: str | None = None) -> str | None:
    if env_name:
        value = util.env_value(env_name)
        if value:
            return value
    return util.env_value("DOCVISION_OPENAI_API_KEY", "OPENAI_API_KEY")


def _content_text(message) -> str:
    content = message.get("content") if isinstance(message, dict) else ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(str(p.get("text") or "") for p in content if isinstance(p, dict))
    return str(content or "")


def _strip_fence(text: str) -> str:
    text = (text or "").strip()
    if text.startswith("```") and text.endswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()


def _page_images(source: str, opts: Options) -> list[tuple[int, bytes, str]]:
    if util.is_url(source):
        raise DocVisionError("OpenAI-compatible adapter expects a local file; download the URL first.")
    path = Path(source)
    suffix = path.suffix.lower()
    if suffix in util.SUPPORTED_IMAGE_EXT:
        return [(1, path.read_bytes(), util.mime_for(path))]
    if suffix != ".pdf":
        raise DocVisionError(f"OpenAI-compatible adapter supports PDF/images, not {suffix}.")
    total = util.pdf_page_count(path)
    indices = util.parse_pages(opts.pages, total)
    if indices is None:
        indices = list(range(total or 0))
    out = []
    for idx in indices:
        out.append((idx + 1, util.render_pdf_page(path, idx), "image/png"))
    return out


def convert(source: str, opts: Options) -> tuple:
    """Local-only OpenAI-compatible vision (Ollama, vLLM on this machine)."""
    vcfg = config.effective_vlm_config(opts.extra)
    base_url, model = vcfg["base_url"], vcfg["model"]
    key = _key(vcfg.get("api_key_env") or "DOCVISION_VLM_API_KEY")
    provider = "local-vlm"
    if not base_url:
        raise DocVisionError("No OpenAI-compatible base URL is configured.",
                             hint="Set DOCVISION_OPENAI_BASE_URL or configure engines.vlm.base_url.")
    if not model:
        raise DocVisionError("No vision model is configured.",
                             hint="Set DOCVISION_OPENAI_MODEL or configure engines.vlm.model.")
    util.validate_local_http_url(base_url)
    info = inspect_input(source, opts)
    if opts.dry_run:
        return None, {"provider": provider, "endpoint": _endpoint(base_url), "model": model,
                      "local": True}
    images = _page_images(source, opts)
    if not images:
        raise DocVisionError("No pages were selected.")
    started = time.monotonic()
    pages: list[RawPage] = []
    for page_no, blob, mime in images:
        uri = util.data_uri(blob, mime)
        payload = {
            "model": model,
            "temperature": 0,
            "max_tokens": int(opts.extra.get("max_tokens") or 8192),
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": [
                    {"type": "text", "text": focus.prompt(opts.extra['refine_task'], opts.extra.get('refine_context', ''),
                                                         opts.extra.get('question', '')) if opts.extra.get('refine_task')
                     else PROMPT.format(page=page_no, total=len(images))},
                    {"type": "image_url", "image_url": {"url": uri}},
                ]},
            ],
        }
        headers = {}
        if key:
            headers["Authorization"] = "Bearer " + key
        status, body = util.post_local_json(_endpoint(base_url), payload,
                                           timeout=min(opts.timeout, 600), headers=headers)
        text = body.decode("utf-8", errors="replace")
        try:
            data = json.loads(text)
        except ValueError:
            raise DocVisionError(f"{provider} returned non-JSON (HTTP {status}): {text[:400]}",
                                 hint=util.error_hint_for_http(status, text))
        if status >= 400 or data.get("error"):
            err = data.get("error") or {}
            raise DocVisionError(
                f"{provider} error (HTTP {status}): {err.get('message') if isinstance(err, dict) else err or text[:300]}",
                hint=util.error_hint_for_http(status, text),
            )
        choices = data.get("choices") or []
        if choices and choices[0].get('finish_reason') not in (None, 'stop'):
            raise DocVisionError(f"{provider} did not complete the response ({choices[0].get('finish_reason')}); result was not accepted.")
        page_md = _strip_fence(_content_text(choices[0].get("message") if choices else {}))
        pages.append(RawPage(page=page_no, markdown=page_md, blocks=[
            RawBlock(type="text", markdown=page_md, text=page_md, page=page_no)
        ]))
    markdown = "\n\n".join(f"<!-- page: {p.page} -->\n\n{p.markdown}".strip()
                           for p in pages if p.markdown)
    warnings = []
    if info.get("pages") and len(pages) < info["pages"]:
        warnings.append(f"Only {len(pages)} of {info['pages']} pages were transcribed.")
    doc = RawDoc(markdown=markdown, pages=pages, provider=provider, model=model,
                 warnings=warnings, usage={"elapsed_seconds": round(time.monotonic() - started, 2)})
    return doc, {"provider": provider, "model": model, "endpoint": _endpoint(base_url),
                 "pages": len(pages), "local": True}
