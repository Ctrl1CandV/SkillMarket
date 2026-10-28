"""Google Gemini document adapter (native PDF/image understanding)."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from .. import config, util
from ..base import DocVisionError, Options, RawDoc
from ..detect import inspect_input
from .common import pages_from_markdown

PROMPT = """You are a document transcription engine. Transcribe the entire document to GitHub-Flavored Markdown.
Rules:
- Preserve reading order, headings, lists, footnotes and captions.
- Write formulas as LaTeX: $...$ inline, $$...$$ display. Do not simplify or solve them.
- Write tables as HTML <table>...</table> when they have merged cells; otherwise Markdown tables are fine.
- For figures, charts and diagrams, keep the caption and insert a short factual description in a blockquote. Do not invent numbers.
- Insert exactly one page marker between pages: <!-- page: N --> (1-based).
- Do not add commentary, preamble, or a summary. Output only the document content.
"""


def _key() -> str:
    key = config.remote_keys().get("gemini")
    if not key:
        raise DocVisionError(
            "Gemini needs an API key.",
            hint="Set GEMINI_API_KEY from https://aistudio.google.com/apikey; do not commit it.",
        )
    return key


def _base() -> str:
    return (config.load().get("remote", {}).get("gemini_base")
            or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")


def _resolve_model(key: str, opts: Options) -> str:
    configured = opts.extra.get("model") or config.load().get("remote", {}).get("gemini_model")
    if configured:
        return configured
    env = util.env_value("DOCVISION_GEMINI_MODEL")
    if env:
        return env
    # Choose a currently available Flash model rather than hard-coding a
    # generation that may be retired.  This call is free.
    try:
        status, body = util.get_json(f"{_base()}/models?key={key}", timeout=30)
        data = json.loads(body.decode("utf-8", errors="replace"))
        names = [m.get("name", "").split("/")[-1] for m in data.get("models", [])
                 if "generateContent" in (m.get("supportedGenerationMethods") or [])]
        flash = [n for n in names if "flash" in n and "image" not in n and "lite" not in n]
        if flash:
            return sorted(flash, key=lambda n: (("preview" in n), n))[0]
        if names:
            return names[0]
    except Exception:
        pass
    return "gemini-2.5-flash"


def convert(source: str, opts: Options) -> tuple:
    key = _key()
    info = inspect_input(source, opts)
    model = _resolve_model(key, opts)
    if opts.dry_run:
        return None, {"provider": "gemini", "model": model,
                      "endpoint": f"{_base()}/models/{model}:generateContent"}
    if util.is_url(source):
        raise DocVisionError(
            "Gemini adapter expects a local file; download the URL first.",
            hint="Use Mistral/MinerU for public URLs, or download the file and retry.",
        )
    path = Path(source)
    data = path.read_bytes()
    if len(data) > 18 * 1024 * 1024:
        raise DocVisionError(
            "Inline Gemini requests are limited to about 18 MB.",
            hint="Split the PDF, use Mistral/MinerU, or upload with the Files API outside this skill.",
        )
    mime = util.mime_for(path)
    if path.suffix.lower() not in util.SUPPORTED_IMAGE_EXT and path.suffix.lower() != ".pdf":
        raise DocVisionError(f"Gemini adapter supports PDF/images, not {path.suffix}.")
    payload = {
        "contents": [{"role": "user", "parts": [
            {"text": PROMPT},
            {"inline_data": {"mime_type": mime, "data": util.data_uri(data, mime).split(",", 1)[1]}},
        ]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 65536},
    }
    started = time.monotonic()
    status, body = util.post_json(
        f"{_base()}/models/{model}:generateContent?key={key}",
        payload, timeout=min(opts.timeout, 900),
    )
    text = body.decode("utf-8", errors="replace")
    try:
        result = json.loads(text)
    except ValueError:
        raise DocVisionError(f"Gemini returned non-JSON (HTTP {status}): {text[:500]}",
                             hint=util.error_hint_for_http(status, text))
    if status >= 400 or result.get("error"):
        err = result.get("error") or {}
        raise DocVisionError(
            f"Gemini error ({err.get('status') or status}): {err.get('message') or text[:400]}",
            hint=util.error_hint_for_http(status, text),
        )
    candidates = result.get("candidates") or []
    if not candidates:
        reason = (result.get("promptFeedback") or {}).get("blockReason")
        raise DocVisionError(f"Gemini returned no candidate{f' (blocked: {reason})' if reason else ''}.")
    parts = ((candidates[0].get("content") or {}).get("parts") or [])
    markdown = "".join(p.get("text") or "" for p in parts if isinstance(p, dict)).strip()
    if markdown.startswith("```") and markdown.endswith("```"):
        markdown = re.sub(r"^```[a-zA-Z]*\n?", "", markdown)
        markdown = re.sub(r"\n?```$", "", markdown).strip()
    pages = pages_from_markdown(markdown)
    warnings = []
    if len(pages) == 1 and (info.get("pages") or 0) > 1:
        warnings.append("Gemini did not return page markers; page mapping is approximate.")
    doc = RawDoc(markdown=markdown, pages=pages, provider="gemini", model=model,
                 warnings=warnings, usage=result.get("usageMetadata") or {})
    return doc, {"provider": "gemini", "model": model, "elapsed_seconds": round(time.monotonic() - started, 2)}
