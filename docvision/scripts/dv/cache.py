"""Conservative resume matching for completed conversion requests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import __version__, util
from .base import DocVisionError, Options


def _digest(value) -> str:
    # Extra options and configuration can contain credentials or signed URLs.
    # Compare all values, but never persist their plaintext in cache metadata.
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def request_signature(info: dict, opts: Options, *, provider: str | None = None,
                      model: str | None = None, context: dict | None = None) -> dict:
    """Return the identity to save in ``raw_meta['cache_request']``.

    Pass the selected provider, and any resolved model/configuration that can
    alter output. ``context`` is hashed so callers may include full configuration
    without placing credentials in the resulting metadata. Old unsigned output
    is deliberately incompatible. Operational flags such as timeout and worker
    count do not alter a successful document and are omitted.
    """
    total = info.get("pages")
    if type(total) is not int or total < 1:
        total = None
    indices = util.parse_pages(opts.pages, total)
    pages = indices if indices is not None else (list(range(total)) if total is not None else "all")
    return {
        "schema": "docvision.request/1",
        "docvision_version": __version__,
        "source_sha256": info.get("sha256"),
        "source_pages": total,
        "provider": provider or opts.provider,
        "model": model if model is not None else (opts.extra.get("model") or ""),
        "options": {"tier": opts.tier, "mode": opts.mode, "pages": pages,
                    "lang": opts.lang, "device": opts.device, "images": opts.images,
                    "keep_raw": opts.keep_raw},
        "extra_sha256": _digest(opts.extra),
        "context_sha256": _digest(context or {}),
    }


def find_existing(out_root: Path, info: dict, opts: Options, *,
                  provider: str | None = None, model: str | None = None,
                  context: dict | None = None) -> Path | None:
    """Find an intact result with the same source and effective request.

    A missing signature or QA report is insufficient evidence for reuse. Warn
    results may be reused, while failed results must be rerun. For auto routing,
    callers must supply the selected provider rather than the literal ``auto``.
    """
    out_root = Path(out_root)
    sha = info.get("sha256")
    if not sha or not out_root.is_dir() or (provider or opts.provider) == "auto":
        return None
    try:
        wanted = request_signature(info, opts, provider=provider, model=model, context=context)
    except DocVisionError:
        return None
    for meta_file in sorted(out_root.glob("*/meta.json")):
        meta = util.read_json(meta_file, {}) or {}
        if not isinstance(meta, dict) or not isinstance(meta.get("source"), dict):
            continue
        if meta["source"].get("sha256") != sha:
            continue
        raw_meta = meta.get("raw_meta") or {}
        if not isinstance(raw_meta, dict) or raw_meta.get("cache_request") != wanted:
            continue
        docdir = meta_file.parent
        qa = util.read_json(docdir / "qa.json", {}) or {}
        if not isinstance(qa, dict) or qa.get("status") not in {"pass", "warn"}:
            continue
        if not (docdir / "content.json").is_file():
            continue
        name = meta.get("markdown_path")
        if not isinstance(name, str) or not name:
            continue
        markdown = (docdir / name).resolve()
        try:
            markdown.relative_to(docdir.resolve())
        except ValueError:
            continue
        if markdown.is_file():
            return docdir
    return None
