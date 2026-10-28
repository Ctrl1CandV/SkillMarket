"""Deterministic checks for a converted document.

These checks catch broken output (missing body, unresolved images, truncated
pages).  They do not judge OCR accuracy or visual fidelity; that requires
looking at the rendered page and, when possible, the source.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from . import util
from .base import DocVisionError


IMG_RE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
HTML_IMG_RE = re.compile(r"<img[^>]+src=[\"']([^\"']+)[\"']", re.I)
PAGE_RE = re.compile(r"<!--\s*page\s*:\s*(\d+)\s*-->", re.I)
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _has_body(markdown: str, docdir: Path) -> bool:
    """Ignore generated metadata/markers but retain real image-only content."""
    body = COMMENT_RE.sub("", str(markdown or ""))
    refs = IMG_RE.findall(body) + HTML_IMG_RE.findall(body)
    for ref in refs:
        if ref.startswith(("http://", "https://", "data:")):
            return True
        if _has_asset(docdir, ref):
            return True
    body = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", body)
    body = re.sub(r"<[^>]*>", "", body)
    return bool(body.strip(" \t\r\n#*_`~|$-"))


def _has_asset(docdir: Path, ref: str) -> bool:
    target = (docdir / ref).resolve()
    try:
        target.relative_to(docdir.resolve())
        return target.is_file() and target.stat().st_size > 0
    except (ValueError, OSError):
        return False


def _page_has_body(page: dict, docdir: Path) -> bool:
    if _has_body(page.get("markdown") or "", docdir):
        return True
    for block in page.get("blocks") or []:
        if (_has_body(block.get("markdown") or block.get("text") or "", docdir)
                or (block.get("asset") and _has_asset(docdir, block["asset"]))):
            return True
    return False


def verify_document(docdir: Path, *, source: str | None = None) -> dict:
    docdir = Path(docdir)
    meta = util.read_json(docdir / "meta.json", {}) or {}
    content = util.read_json(docdir / "content.json", {}) or {}
    md_name = meta.get("markdown_path")
    md_path = docdir / (md_name or f"{docdir.name}.md")
    markdown = _read(md_path)
    issues: list[dict] = []

    def add(severity: str, code: str, message: str) -> None:
        issues.append({"severity": severity, "code": code, "message": message})

    pages = content.get("pages") or []
    if not markdown.strip():
        add("fail", "empty_markdown", "The main Markdown file is missing or empty.")
    if not pages:
        add("fail", "no_pages", "content.json contains no pages.")
    else:
        blank = [p.get("page") for p in pages if not _page_has_body(p, docdir)]
        if blank:
            add("warn", "blank_pages", f"Pages without body or image assets: {blank[:20]}")
    if not _has_body(markdown, docdir) and not any(_page_has_body(p, docdir) for p in pages):
        add("fail", "empty_body", "The result has no document body or usable image assets; metadata does not count as content.")

    page_numbers = [p.get("page") for p in pages if type(p.get("page")) is int and p["page"] > 0]
    if len(page_numbers) != len(pages):
        add("fail", "invalid_page_numbers", "Every result page must have a positive integer page number.")
    selected = (meta.get("options") or {}).get("pages")
    total = (meta.get("source") or {}).get("pages")
    if type(total) is not int or total < 1:
        total = None
        add("warn", "source_page_count_unknown", "The source page count is unknown; full-document completeness cannot be verified.")
    expected = None
    try:
        indices = util.parse_pages(selected, total)
        if indices is not None:
            expected = {index + 1 for index in indices}
        elif total is not None:
            expected = set(range(1, total + 1))
    except DocVisionError as exc:
        # Reverse page ranges need a known count; forward selections can still
        # be checked even when full-document completeness is unknown.
        add("warn" if total is None else "fail", "page_selection_unverified", str(exc))
    if expected is not None:
        actual = set(page_numbers)
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        if missing:
            add("fail", "missing_pages", f"Expected original pages are missing: {missing[:20]}")
        if unexpected:
            add("fail", "unexpected_pages", f"Result contains unrequested or out-of-range pages: {unexpected[:20]}")
    if page_numbers:
        duplicates = sorted({n for n in page_numbers if page_numbers.count(n) > 1})
        if duplicates:
            add("fail", "duplicate_pages", f"Duplicate page numbers in content.json: {duplicates}")
    markers = [int(x) for x in PAGE_RE.findall(markdown)]
    if markers and page_numbers:
        missing_markers = [n for n in page_numbers if n not in markers]
        if missing_markers:
            add("warn", "page_markers_incomplete",
                f"Markdown page markers do not cover pages {missing_markers[:10]}.")

    # Unresolved local image references are the most common broken-output bug.
    refs = [m for m in IMG_RE.findall(markdown) + HTML_IMG_RE.findall(markdown)
            if not m.startswith(("http://", "https://", "data:"))]
    missing_refs = []
    for ref in refs:
        target = (docdir / ref).resolve()
        try:
            target.relative_to(docdir.resolve())
        except ValueError:
            missing_refs.append(ref)
            continue
        if not target.is_file():
            missing_refs.append(ref)
    if missing_refs:
        severity = "fail" if len(missing_refs) > max(2, len(refs) // 2) else "warn"
        add(severity, "missing_assets",
            f"{len(missing_refs)} image reference(s) do not resolve: {missing_refs[:8]}")

    # Structural balance checks are intentionally conservative.
    tables_open = len(re.findall(r"<table\b", markdown, re.I))
    tables_close = len(re.findall(r"</table\s*>", markdown, re.I))
    if tables_open != tables_close:
        add("warn", "table_unbalanced",
            f"HTML table tags are unbalanced ({tables_open} open, {tables_close} close).")
    dollars = len(re.findall(r"(?<!\\)\$", markdown))
    if dollars % 2:
        add("warn", "formula_delimiter", "An odd number of unescaped `$` characters was found.")
    replacements = markdown.count("\ufffd")
    if replacements and replacements / max(1, len(markdown)) > 0.01:
        add("warn", "replacement_chars",
            f"{replacements} replacement characters (U+FFFD) suggest a decoding or OCR failure.")

    # Repeated pages often mean a stale cache or a failed page loop.
    seen: dict[str, int] = {}
    for page in pages:
        body = " ".join(str(b.get("text") or "") for b in page.get("blocks") or [])
        if len(body.strip()) < 80:
            continue
        h = hashlib.sha1(body.encode("utf-8", "replace")).hexdigest()
        if h in seen:
            add("warn", "duplicate_page_text",
                f"Pages {seen[h]} and {page.get('page')} have identical text.")
        else:
            seen[h] = page.get("page")

    blocking = [i for i in issues if i["severity"] == "fail"]
    status = "fail" if blocking else ("warn" if issues else "pass")
    total_chars = sum(int(p.get("markdown_chars") or 0) for p in pages)
    return {
        "schema": "docvision.qa/1",
        "checked_at": util.now_iso(),
        "source": source or (meta.get("source") or {}).get("path"),
        "provider": meta.get("provider"),
        "status": status,
        "pages": len(pages),
        "markdown_chars": len(markdown),
        "page_chars": total_chars,
        "image_refs": len(refs),
        "missing_image_refs": missing_refs,
        "page_markers": len(markers),
        "issues": issues,
        "note": "Passing these checks does not prove OCR accuracy; inspect page images for formulas, tables and charts.",
    }
