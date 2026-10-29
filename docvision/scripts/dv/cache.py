"""Conservative resume matching for completed conversion requests."""

from __future__ import annotations

import hashlib
import json
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from threading import Lock

from . import __version__, config, util
from .base import DocVisionError, Options


def _digest(value) -> str:
    # Extra options and configuration can contain credentials or signed URLs.
    # Compare all values, but never persist their plaintext in cache metadata.
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def recognition_extra(extra: dict | None) -> dict:
    """Transport receipts and explicit retry intent do not change recognized text."""
    return {key: value for key, value in (extra or {}).items()
            if not key.startswith('_cloud_') and key != 'cloud_new_attempt'}


def provider_context(provider: str, extra: dict | None = None) -> dict:
    """Only effective settings of this provider can invalidate its output.

    Credentials, consent, output directories and unrelated engines are not
    recognition settings. Resolved model roots and runtime identity are.
    Callers hash this context before persisting it.
    """
    cfg = config.load()
    result = {'provider': provider, 'engine_version': None, 'extra': recognition_extra(extra)}
    if provider in {'mineru-local', 'paddleocr-local'}:
        mineru = provider == 'mineru-local'
        engine = config.discover_mineru() if mineru else config.discover_paddle()
        result.update(engine_version=engine.version,
                      engine_fingerprint=engine.extra.get('cache_fingerprint'),
                      exe=engine.exe, python=engine.python,
                      models=str(engine.extra.get('mineru_home' if mineru else 'paddlex_home')
                                 or config.model_home('mineru' if mineru else 'paddlex', cfg)))
        if not mineru:
            result['device'] = engine.extra.get('device')
            result['pipeline'] = config.PADDLE_PIPELINE_VERSION
    elif provider == 'local-vlm':
        vlm = config.effective_vlm_config(extra=extra, cfg=cfg)
        result.update(endpoint=vlm.get('base_url'), model=vlm.get('model'))
    elif provider == 'paddleocr-cloud':
        result['endpoint'] = cfg.get('remote', {}).get('paddle_base') or config.DEFAULT_CONFIG['remote']['paddle_base']
    elif provider == 'text-local':
        try:
            result['engine_version'] = version('pypdf')
        except PackageNotFoundError:
            pass
    return result


class ResumeIndex:
    """One metadata scan per batch; candidates are revalidated before reuse."""

    def __init__(self, out_root: Path):
        self.root = Path(out_root).resolve()
        self._paths: dict[str, set[Path]] = {}
        self._lock = Lock()
        for path in sorted(self.root.glob('*/meta.json')):
            self.add(path.parent)

    def add(self, docdir: Path) -> None:
        path = Path(docdir).resolve() / 'meta.json'
        meta = util.read_json(path, {})
        source = meta.get('source') if isinstance(meta, dict) else None
        sha = source.get('sha256') if isinstance(source, dict) else None
        if sha:
            with self._lock:
                self._paths.setdefault(sha, set()).add(path)

    def candidates(self, sha: str) -> list[Path]:
        with self._lock:
            return sorted(self._paths.get(sha, ()))


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
        "extra_sha256": _digest(recognition_extra(opts.extra)),
        "context_sha256": _digest(context or {}),
    }


def find_existing(out_root: Path, info: dict, opts: Options, *,
                  provider: str | None = None, model: str | None = None,
                  context: dict | None = None, index: ResumeIndex | None = None) -> Path | None:
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
    candidates = (index.candidates(sha) if index is not None and index.root == out_root.resolve()
                  else sorted(out_root.glob("*/meta.json")))
    for meta_file in candidates:
        if (meta_file.parent / '.docvision-write.lock').exists():
            continue
        meta = util.read_json(meta_file, {}) or {}
        if not isinstance(meta, dict) or not isinstance(meta.get("source"), dict):
            continue
        if meta["source"].get("sha256") != sha:
            continue
        # Identical bytes copied to a different path need their own provenance:
        # the old source may have been moved or replaced before a later crop.
        wanted_path, saved_path = info.get('source'), meta['source'].get('path')
        if wanted_path and saved_path and not util.is_url(wanted_path):
            stored = Path(saved_path)
            if not stored.is_absolute():
                stored = meta_file.parent / stored
            if Path(wanted_path).resolve() != stored.resolve():
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
