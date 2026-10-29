"""Parsing helpers shared by the local and remote adapters."""

from __future__ import annotations

import io
import json
import re
import zipfile
from pathlib import Path
from typing import Any

from .. import util
from ..base import DocVisionError, RawBlock, RawDoc, RawPage, block_markdown


def safe_extract_zip(data: bytes, dest: Path) -> list[str]:
    dest = util.ensure_dir(dest)
    names: list[str] = []
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for info in archive.infolist():
            name = info.filename
            parts = Path(name.replace("\\", "/")).parts
            if name.startswith("/") or ".." in parts or (len(name) > 1 and name[1] == ":"):
                raise DocVisionError(f"Unsafe zip member path: {name}")
            file_type = (info.external_attr >> 16) & 0o170000
            if file_type == 0o120000:
                raise DocVisionError(f"Unsafe zip symlink: {name}")
            archive.extract(info, dest)
            if not info.is_dir():
                names.append(name)
    return names


def zip_members(data: bytes) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for info in archive.infolist():
            name = info.filename.replace("\\", "/")
            parts = Path(name).parts
            if name.startswith("/") or ".." in parts:
                raise DocVisionError(f"Unsafe zip member path: {name}")
            if info.is_dir():
                continue
            out[name] = archive.read(info)
    return out


def pick_member(members: dict[str, bytes], *names: str) -> tuple[str, bytes] | None:
    for name in names:
        for key, value in members.items():
            if key == name or key.endswith("/" + name):
                return key, value
    return None


def assets_from_members(members: dict[str, bytes], prefixes: tuple[str, ...] = ("images/", "imgs/", "assets/")) -> dict[str, bytes]:
    assets: dict[str, bytes] = {}
    for name, data in members.items():
        normalized = name.replace("\\", "/")
        if normalized.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff")):
            if any(normalized.startswith(p) or ("/" + p) in normalized for p in prefixes) or "/images/" in normalized:
                assets[normalized] = data
    return assets


def html_table_text(html: str) -> str:
    return html or ""


def _text_from_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                # MinerU algorithm_body wraps another span list. Recurse into
                # that content rather than emitting Python list/dict literals.
                t = _text_from_content(item.get("content") or item.get("text") or "")
                if item.get("type") == "equation_inline" and t:
                    t = f"${t}$"
                elif item.get("type") == "equation_interline" and t:
                    t = f"$$\n{t}\n$$"
                parts.append(t)
            elif isinstance(item, list):
                parts.append(_text_from_content(item))
            elif item is not None:
                parts.append(str(item))
        return "".join(parts)
    if isinstance(content, dict):
        return _text_from_content(content.get("content") or content.get("text") or "")
    return ""


def blocks_from_docvortex(middle: dict) -> tuple[list[RawPage], list[str]]:
    warnings: list[str] = []
    pages: list[RawPage] = []
    layout = ((middle.get("extensions") or {}).get("docvortex_layout") or {}).get("pages") or []
    dims = {int(p.get("page_idx", i)): (p.get("width_pt"), p.get("height_pt"))
            for i, p in enumerate(layout) if isinstance(p, dict)}
    for p_idx, page in enumerate(middle.get("pages") or []):
        if not isinstance(page, dict):
            continue
        page_no = int(page.get("page_idx", p_idx)) + 1
        width, height = dims.get(page_no - 1, (None, None))
        rp = RawPage(page=page_no, width=width, height=height)
        for b_idx, block in enumerate(page.get("blocks") or []):
            if not isinstance(block, dict):
                continue
            btype = str(block.get("type") or "text")
            content = block.get("content")
            text = _text_from_content(content)
            mapped = map_block_type(btype)
            asset = None
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("image_path"):
                        asset = str(item["image_path"])
                        break
            if btype == "table" and isinstance(content, list):
                # Keep caption/body spans in their source order. Selecting just
                # table_body discards an already-recognized table caption.
                parts = [_text_from_content([item]) for item in content]
                text = "\n\n".join(part for part in parts if part)
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "table_body":
                        asset = asset or item.get("image_path")
            md = block_markdown(mapped, text, level=block.get("level"), asset=asset)
            rp.blocks.append(RawBlock(
                type=mapped, markdown=md, text=text, page=page_no,
                bbox=util.clamp_bbox(block.get("bbox")),
                level=block.get("level"), asset=asset,
                meta={"provider_type": btype, "index": block.get("index", b_idx)},
            ))
        pages.append(rp)
    if not pages:
        warnings.append("MinerU middle JSON contained no pages.")
    return pages, warnings


def blocks_from_content_list(items: list, width: float | None = None,
                             height: float | None = None) -> tuple[list[RawPage], list[str]]:
    warnings: list[str] = []
    pages: dict[int, RawPage] = {}
    for item in items or []:
        if not isinstance(item, dict):
            continue
        page_no = int(item.get("page_idx", 0)) + 1
        rp = pages.setdefault(page_no, RawPage(page=page_no, width=width, height=height))
        btype = str(item.get("type") or "text")
        mapped = map_block_type(btype)
        text = item.get("text") or item.get("table_body") or item.get("img_path") or ""
        if item.get("text_level"):
            mapped = "heading"
        asset = item.get("img_path")
        md = block_markdown(mapped, text, level=item.get("text_level"), asset=asset)
        rp.blocks.append(RawBlock(
            type=mapped, markdown=md, text=text, page=page_no,
            bbox=util.clamp_bbox(item.get("bbox")), asset=asset,
            level=item.get("text_level"), meta={"provider_type": btype},
        ))
    for rp in pages.values():
        rp.markdown = "\n\n".join(b.markdown for b in rp.blocks if b.markdown)
    if not pages:
        warnings.append("content_list.json contained no blocks.")
    return [pages[k] for k in sorted(pages)], warnings


def map_block_type(value: str) -> str:
    v = (value or "").lower()
    if v in {"paragraph_title", "doc_title", "title", "heading", "section_title"}:
        return "heading"
    if v in {"table", "table_body"}:
        return "table"
    if v in {"equation", "formula", "inline_formula", "interline_formula", "display_formula"}:
        return "formula"
    if v in {"image", "figure", "picture"}:
        return "image"
    if v in {"chart", "figure_chart"}:
        return "chart"
    if v in {"code", "algorithm"}:
        return "code"
    if v in {"list", "list_item"}:
        return "list"
    if v in {"page_number", "number", "header", "footer", "aside_text", "footnote"}:
        return "other"
    return "text"


def split_markdown_pages(markdown: str) -> list[tuple[int, str]]:
    """Split page markers (<!-- page: N -->) into (1-based page, text)."""
    pattern = re.compile(r"<!--\s*page\s*:\s*(\d+)\s*-->", re.I)
    matches = list(pattern.finditer(markdown or ""))
    if not matches:
        return []
    parts = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
        parts.append((int(m.group(1)), markdown[start:end].strip()))
    return parts


def pages_from_markdown(markdown: str, page_count: int | None = None) -> list[RawPage]:
    parts = split_markdown_pages(markdown)
    if parts:
        return [RawPage(page=n, markdown=body,
                        blocks=[RawBlock(type="text", markdown=body, text=body, page=n)])
                for n, body in parts]
    return [RawPage(page=1, markdown=markdown or "",
                    blocks=[RawBlock(type="text", markdown=markdown or "", text=markdown or "", page=1)])]


def page_markdown(page: RawPage) -> str:
    if page.markdown.strip():
        return page.markdown.strip()
    return "\n\n".join(b.markdown for b in page.blocks if b.markdown).strip()


def assemble_markdown(pages: list[RawPage], fallback: str = "") -> str:
    pages = sorted(pages, key=lambda p: p.page)
    if any(p.markdown.strip() for p in pages):
        bodies = []
        for page in pages:
            body = page_markdown(page)
            if body:
                bodies.append(f"<!-- page: {page.page} -->\n\n{body}")
        if bodies:
            return "\n\n".join(bodies).strip()
    return (fallback or "").strip()


def normalize_asset_name(name: str) -> str:
    name = name.replace("\\", "/")
    for prefix in ("images/", "imgs/", "assets/"):
        if name.startswith(prefix):
            name = name[len(prefix):]
    return Path(name).name


def remap_links(markdown: str, mapping: dict[str, str]) -> str:
    """Rewrite local image links using an old-name -> new-name mapping."""
    def repl_md(match: re.Match) -> str:
        target = match.group(2)
        if target.startswith(("http://", "https://", "data:")):
            return match.group(0)
        clean = target.lstrip("./")
        new = mapping.get(clean) or mapping.get(Path(clean).name)
        return f"{match.group(1)}assets/{new}{match.group(3)}" if new else match.group(0)

    def repl_html(match: re.Match) -> str:
        target = match.group(2)
        if target.startswith(("http://", "https://", "data:")):
            return match.group(0)
        clean = target.lstrip("./")
        new = mapping.get(clean) or mapping.get(Path(clean).name)
        return f"{match.group(1)}assets/{new}{match.group(3)}" if new else match.group(0)

    md = re.sub(r"(!\[[^\]]*\]\()([^)\s]+)(\))", repl_md, markdown or "")
    return re.sub(r"(<img[^>]+src=[\"'])([^\"']+)([\"'])", repl_html, md, flags=re.I)


def remap_assets(markdown: str, assets: dict[str, bytes]) -> tuple[str, dict[str, bytes], dict[str, str]]:
    """Copy provider images into a flat assets/ namespace and rewrite links."""
    mapping: dict[str, str] = {}
    out_assets: dict[str, bytes] = {}
    for original, data in assets.items():
        new_name = normalize_asset_name(original)
        if new_name in out_assets and out_assets[new_name] != data:
            stem = Path(new_name).stem
            suffix = Path(new_name).suffix
            new_name = f"{stem}-{util.short_hash(original, 6)}{suffix}"
        out_assets[new_name] = data
        mapping[original] = new_name
        mapping[original.replace("\\", "/")] = new_name
    return remap_links(markdown, mapping), out_assets, mapping


def raw_from_mineru_zip(data: bytes, *, provider: str, model: str = "") -> RawDoc:
    members = zip_members(data)
    md_pair = pick_member(members, "markdown.md", "full.md", "document.md")
    middle_pair = pick_member(members, "middle_json.json", "layout.json")
    content_pair = pick_member(members, "content_list.json", "content_list_v2.json")
    warnings: list[str] = []
    pages: list[RawPage] = []
    if middle_pair:
        try:
            middle = json.loads(middle_pair[1].decode("utf-8", errors="replace"))
            if middle.get("schema") == "docvortex.middle" or "pages" in middle:
                pages, w = blocks_from_docvortex(middle)
            else:
                pages, w = [], ["Unrecognised middle_json schema; using Markdown only."]
            warnings.extend(w)
        except Exception as exc:
            warnings.append(f"Could not parse middle JSON: {exc}")
    if not pages and content_pair:
        try:
            content = json.loads(content_pair[1].decode("utf-8", errors="replace"))
            items = content.get("content") if isinstance(content, dict) else content
            pages, w = blocks_from_content_list(items if isinstance(items, list) else [])
            warnings.extend(w)
        except Exception as exc:
            warnings.append(f"Could not parse content_list JSON: {exc}")
    markdown = md_pair[1].decode("utf-8", errors="replace") if md_pair else ""
    if not pages:
        pages = pages_from_markdown(markdown)
        if md_pair:
            warnings.append("No page structure was available; page mapping is only approximate.")
    if not markdown:
        markdown = assemble_markdown(pages)
    assets = assets_from_members(members)
    raw_files = {name: value for name, value in members.items()
                 if name.endswith(".json") or name.endswith(".md")}
    return RawDoc(markdown=markdown, pages=pages, assets=assets, provider=provider,
                  model=model, warnings=warnings, raw_files=raw_files)
