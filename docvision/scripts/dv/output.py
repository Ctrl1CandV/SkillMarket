"""Write the stable on-disk contract shared by every provider."""

from __future__ import annotations

import hashlib
import os
import re
import time
from contextlib import contextmanager
from pathlib import Path

from . import util
from .base import DocVisionError, Options, RawDoc, RawPage
from .detect import describe_route
from .providers.common import assemble_markdown, page_markdown, remap_assets, remap_links


def _source_identity(source: str) -> str:
    if util.is_url(source):
        return source
    return os.path.normcase(str(Path(source).expanduser().resolve()))


def _same_source(docdir: Path, source: str) -> bool:
    meta = util.read_json(docdir / "meta.json", {})
    saved = meta.get("source") if isinstance(meta, dict) else None
    path = saved.get("path") if isinstance(saved, dict) else None
    return (isinstance(path, str) and bool(path)
            and _source_identity(path) == _source_identity(source))


@contextmanager
def _exclusive_write_lock(lock: Path, message: str):
    try:
        handle = lock.open("x", encoding="utf-8")
    except FileExistsError as exc:
        raise DocVisionError(
            message,
            hint=f"Wait for it to finish. If the writer stopped, remove its stale lock: {lock}") from exc
    try:
        with handle:
            yield
    finally:
        lock.unlink()


@contextmanager
def _force_write_lock(out_root: Path, source: str, *, force: bool):
    if not force:
        yield
        return
    key = hashlib.sha256(_source_identity(source).encode("utf-8")).hexdigest()
    lock = out_root / f".docvision-force-{key}.lock"
    with _exclusive_write_lock(lock, f"A forced conversion of this source is already in progress: {source}"):
        yield


def document_dir(out_root: Path, source: str, *, force: bool = False) -> Path:
    """Reserve a directory before returning it to a writer."""
    out_root = util.ensure_dir(out_root)
    slug = util.safe_slug(source)
    if force:
        # Older suffixes may hash a relative path or another spelling of the
        # same source. Inspect provenance rather than assuming a suffix owns it.
        for candidate in sorted(out_root.iterdir(), key=lambda p: (p.name != slug, p.name)):
            if ((candidate.name == slug or candidate.name.startswith(f"{slug}-"))
                    and _same_source(candidate, source)):
                return candidate
    suffix = f"{slug}-{util.short_hash(source, 8)}"
    n = 0
    while True:
        name = slug if n == 0 else suffix if n == 1 else f"{suffix}-{n}"
        candidate = out_root / name
        try:
            candidate.mkdir()
            return candidate
        except FileExistsError:
            if force and _same_source(candidate, source):
                return candidate
        # Another writer may claim any suffix too; mkdir is the authority at
        # every step rather than an earlier, racy existence check.
        n += 1


def _asset_lookup(mapping: dict[str, str], name: str | None) -> str | None:
    if not name:
        return None
    clean = name.replace("\\", "/").lstrip("./")
    if clean in mapping:
        return "assets/" + mapping[clean]
    base = Path(clean).name
    for old, new in mapping.items():
        if Path(old).name == base:
            return "assets/" + new
    return None


def _header(source: str, raw: RawDoc, route: dict, pages: int) -> str:
    name = Path(source).name if not util.is_url(source) else source
    return (
        "<!-- docvision\n"
        f"source: {name}\n"
        f"provider: {raw.provider or route.get('provider', '')}\n"
        f"model: {raw.model or ''}\n"
        f"privacy: {route.get('privacy', 'unknown')}\n"
        f"pages: {pages}\n"
        "-->\n"
    )


def write_document(raw: RawDoc, source: str, opts: Options, *, out_root: Path,
                   route: dict | None = None, elapsed: float | None = None,
                   info: dict | None = None, raw_meta: dict | None = None) -> Path:
    out_root = util.ensure_dir(out_root)
    with _force_write_lock(out_root, source, force=opts.force):
        docdir = document_dir(out_root, source, force=opts.force)
        with _exclusive_write_lock(docdir / ".docvision-write.lock",
                                   f"A conversion is already in progress for this document: {docdir}"):
            return _write_document(raw, source, opts, docdir=docdir, route=route,
                                   elapsed=elapsed, info=info, raw_meta=raw_meta)


def _write_document(raw: RawDoc, source: str, opts: Options, *, docdir: Path,
                    route: dict | None = None, elapsed: float | None = None,
                    info: dict | None = None, raw_meta: dict | None = None) -> Path:
    route = route or describe_route(raw.provider)
    if not raw.provider:
        raw.provider = route.get("provider", "")
    assets_dir = util.ensure_dir(docdir / "assets")

    markdown, assets, mapping = remap_assets(raw.markdown, raw.assets)
    for name, data in assets.items():
        util.atomic_write(assets_dir / name, data)

    pages = sorted(raw.pages or [], key=lambda p: p.page)
    if not pages:
        pages = [RawPage(page=1, markdown=markdown)]
    # Rewrite block-level asset links and keep page bodies in the contract.
    for page in pages:
        page.markdown = remap_links(page.markdown, mapping)
        for block in page.blocks:
            block.markdown = remap_links(block.markdown, mapping)
            if block.asset:
                block.asset = _asset_lookup(mapping, block.asset)
                if block.asset:
                    if block.type == "image" and not block.markdown:
                        block.markdown = f"![image]({block.asset})"
                    elif block.type == "chart" and not block.markdown:
                        block.markdown = f"![chart]({block.asset})"
        if not page.markdown.strip():
            page.markdown = "\n\n".join(b.markdown for b in page.blocks if b.markdown)

    if not markdown.strip():
        markdown = assemble_markdown(pages)
    if not markdown.strip():
        raw.warnings.append("Provider returned no Markdown; the document may be empty or unreadable.")
    slug = docdir.name
    md_path = docdir / f"{slug}.md"
    header = _header(source, raw, route, len(pages))
    util.atomic_write(md_path, header + "\n" + markdown.strip() + "\n")

    content = {
        "schema": "docvision.content/1",
        "source": {
            "name": Path(source).name if not util.is_url(source) else source,
            "path": (source if util.is_url(source) else str(Path(source).resolve())),
            "sha256": (info or {}).get("sha256"),
            "bytes": (info or {}).get("bytes"),
            "pages": (info or {}).get("pages"),
        },
        "provider": raw.provider,
        "model": raw.model,
        "privacy": route.get("privacy"),
        "pages": [],
        "assets": {},
        "warnings": list(raw.warnings),
    }
    asset_pages: dict[str, dict] = {}
    for page in pages:
        out_page = {"page": page.page, "width": page.width, "height": page.height,
                    "markdown": page.markdown, "blocks": []}
        for idx, block in enumerate(page.blocks):
            block_id = f"p{page.page}-b{idx}"
            item = {
                "id": block_id,
                "type": block.type,
                "markdown": block.markdown,
                "text": block.text,
                "bbox": block.bbox,
                "bbox_space": "normalized" if block.bbox else None,
                "level": block.level,
                "asset": block.asset,
                "confidence": block.confidence,
                "meta": block.meta,
            }
            out_page["blocks"].append(item)
            if block.asset:
                name = block.asset.split("/", 1)[-1]
                asset_pages[name] = {"page": page.page, "type": block.type, "block": block_id}
        out_page["markdown_chars"] = len(page_markdown(page))
        content["pages"].append(out_page)
    content["assets"] = {name: asset_pages.get(name, {"page": None, "type": "image"})
                         for name in assets}
    util.write_json(docdir / "content.json", content)

    meta = {
        "schema": "docvision.meta/1",
        "generated_at": util.now_iso(),
        "elapsed_seconds": round(elapsed, 2) if elapsed is not None else None,
        "source": content["source"],
        "route": route,
        "provider": raw.provider,
        "model": raw.model,
        "pages": len(pages),
        "assets": len(assets),
        "markdown_path": md_path.name,
        "content_path": "content.json",
        "options": {
            "tier": opts.tier,
            "mode": opts.mode,
            "pages": opts.pages,
            "lang": opts.lang,
            "provider": opts.provider,
            "device": opts.device,
        },
        "warnings": list(raw.warnings),
        "usage": raw.usage,
        "raw_meta": raw_meta or {},
    }
    util.write_json(docdir / "meta.json", meta)
    if opts.keep_raw and raw.raw_files:
        raw_dir = util.ensure_dir(docdir / "raw")
        for name, data in raw.raw_files.items():
            safe = Path(name.replace("\\", "/")).name
            util.atomic_write(raw_dir / safe, data)

    # Verification is deterministic and cheap; it must never invent a pass.
    from .verify import verify_document
    qa = verify_document(docdir, source=source)
    util.write_json(docdir / "qa.json", qa)
    return docdir
