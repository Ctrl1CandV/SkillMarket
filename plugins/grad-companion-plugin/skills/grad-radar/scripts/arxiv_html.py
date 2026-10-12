# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx"]
# ///
"""Extract and slice full-text arXiv HTML by section (reading funnel, stage 2: summarization).

Fetch https://arxiv.org/html/<id> (LaTeXML output) and slice by section anchors (S2 / S2.SS1).
For focused reading, fetch only relevant sections. For a full survey, follow the original outline, then check required figures and tables separately.

A page is usable HTML only if it contains LaTeXML structure (ltx_ classes and S anchors),
not merely an HTTP 200 response. If HTML is unavailable, return NO_HTML; PDFs are handled by an external parser, not this script.

Network routes: environment proxy (handled by httpx) > Windows system proxy (read explicitly because httpx ignores the registry) > direct connection;
retry another route only after a connection-layer failure; keep using the route after receiving an HTTP response (lessons from arxiv_fetch).

HTML is cached in .grad/cache/arxiv/ (TTL 7 days; deletion affects speed, not correctness).

Output contract: with --json, stdout prints one JSON object: {"ok": true, "data": {...}} or {"ok": false, ...}.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

BACKOFF_SECONDS = (3, 6, 12)
SKIP_TAGS = {"script", "style", "svg", "head", "nav"}
CACHE_TTL_DAYS = 7.0

if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


def die(error: str, detail: str, **extra) -> None:
    print(json.dumps({"ok": False, "error": error, "detail": detail, **extra}, ensure_ascii=False))
    sys.exit(1)


class LatexmlReader(HTMLParser):
    """Parse LaTeXML HTML into a section tree; each section has {id, kind, level, title, blocks[]}."""

    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
    LINE_TAGS = {"br", "li", "p", "pre", "tr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.doc_title = ""
        self.sections: list[dict] = []
        self.stack: list[dict] = []
        self.dom_depth = 0
        self.skip = 0
        self.suppress = 0
        self.math_depth = 0
        self.capture = None
        self.buf: list[str] = []
        self.title_parts: list[str] = []
        self.heading_parts: list[str] = []
        self.structured_depth = 0
        self.structured_kind = ""
        self.structured_buf: list[str] = []
        self.structured_resume: str | None = None
        self.table_depth = 0
        self.cell: list[str] | None = None
        self.cell_colspan = 1
        self.cell_rowspan = 1
        self.row: dict[int, str] | None = None
        self.row_col = 0
        self.rowspans: dict[int, tuple[int, str]] = {}
        self.table_rows: list[list[str]] | None = None

    def target(self) -> dict | None:
        for sec in reversed(self.stack):
            if sec["recorded"]:
                return sec
        return None

    def emit(self, text: str, prefix: str = "") -> None:
        sec = self.target()
        if sec is not None and text.strip():
            sec["blocks"].append((prefix + text).strip())

    def flush_para(self) -> None:
        if self.capture in ("para", "caption"):
            text = " ".join("".join(self.buf).split())
            if text:
                self.emit(text, "Caption: " if self.capture == "caption" else "")
            self.buf = []
            self.capture = None

    @staticmethod
    def _span(value: str | None) -> int:
        try:
            return max(1, int(value or "1"))
        except ValueError:
            return 1

    def _start_structured(self, kind: str) -> None:
        self.structured_resume = self.capture if self.capture in ("para", "caption") else None
        self.flush_para()
        self.structured_depth = 1
        self.structured_kind = kind
        self.structured_buf = []

    def _flush_structured(self) -> None:
        lines = [" ".join(line.split()) for line in "".join(self.structured_buf).splitlines()]
        text = "\n".join(line for line in lines if line)
        if text:
            self.emit(text, "Algorithm: " if self.structured_kind == "algorithm" else "Code listing: ")
        resume = self.structured_resume
        self.structured_depth = 0
        self.structured_kind = ""
        self.structured_buf = []
        self.structured_resume = None
        if resume:
            self.capture = resume
            self.buf = []

    def _start_row(self) -> None:
        self.row = {}
        for col, (remaining, text) in list(self.rowspans.items()):
            self.row[col] = text
            if remaining <= 1:
                del self.rowspans[col]
            else:
                self.rowspans[col] = (remaining - 1, text)
        self.row_col = 0

    def _finish_cell(self) -> None:
        if self.cell is None or self.row is None:
            return
        while any(self.row_col + offset in self.row for offset in range(self.cell_colspan)):
            self.row_col += 1
        text = " ".join("".join(self.cell).split())
        for offset in range(self.cell_colspan):
            col = self.row_col + offset
            self.row[col] = text
            if self.cell_rowspan > 1:
                self.rowspans[col] = (self.cell_rowspan - 1, text)
        self.row_col += self.cell_colspan
        self.cell = None

    def handle_starttag(self, tag, attrs) -> None:
        d = dict(attrs)
        cls = d.get("class", "")
        if tag in SKIP_TAGS:
            self.skip += 1
            return
        if self.skip:
            return

        if self.suppress:
            if tag not in self.VOID_TAGS:
                self.suppress += 1
            return

        if self.structured_depth:
            if tag == "math":
                self.math_depth += 1
                if d.get("alttext"):
                    self.structured_buf.append(f"${d['alttext']}$")
                return
            if tag in self.LINE_TAGS:
                self.structured_buf.append("\n")
            if tag not in self.VOID_TAGS:
                self.structured_depth += 1
            return

        class_tokens = set(cls.split())
        if any("ltx_algorithm" in token for token in class_tokens):
            self._start_structured("algorithm")
            return
        if any("ltx_listing" in token for token in class_tokens):
            self._start_structured("listing")
            return

        if tag == "math":
            self.math_depth += 1
            alt = d.get("alttext")
            if alt:
                if self.table_depth and self.cell is not None:
                    self.cell.append(f"${alt}$")
                elif self.capture in ("para", "caption"):
                    self.buf.append(f"${alt}$")
                else:
                    self.emit(f"${alt}$")
            return
        if tag == "span" and "ltx_tag" in cls:
            self.suppress += 1
            return

        if tag in ("section", "div"):
            self.dom_depth += 1
        if tag == "section" or (tag == "div" and "ltx_abstract" in cls):
            self._open_section(tag, d, cls)
        elif tag in ("h2", "h3", "h4", "h5", "h6") and "ltx_title" in cls:
            self.flush_para()
            self.capture = "heading"
            self.heading_parts = []
        elif tag == "h1" and "ltx_title" in cls:
            self.capture = "title"
            self.title_parts = []
        elif tag == "p":
            if self.table_depth:
                return
            self.flush_para()
            self.capture = "para"
            self.buf = []
        elif tag == "figcaption":
            self.flush_para()
            self.capture = "caption"
            self.buf = []
        elif tag == "table" and "ltx_tabular" in cls:
            self.table_depth += 1
            if self.table_depth == 1:
                self.table_rows = []
                self.rowspans = {}
        elif self.table_depth:
            if tag == "tr":
                self._start_row()
            elif tag in ("td", "th"):
                self.cell = []
                self.cell_colspan = self._span(d.get("colspan"))
                self.cell_rowspan = self._span(d.get("rowspan"))

    def _open_section(self, tag: str, d: dict, cls: str) -> None:
        sid = d.get("id", "") if tag == "section" else "abstract"
        kind, level = None, None
        tokens = sid.split(".")
        if sid == "abstract" or "ltx_abstract" in cls:
            kind, level = "abstract", 0
        elif sid == "bib" or "ltx_bibliography" in cls:
            kind, level = "bibliography", 1
        elif sid == "ack":
            kind, level = "acknowledgments", 1
        elif sid == "footnote":
            kind, level = "footnote", 0
        elif re.fullmatch(r"[A-Z]\d+(\.SSS?\d+)*", sid):
            kind = "numbered" if tokens[0].startswith("S") else "appendix"
            level = len(tokens)
        sec = {"tag": tag, "id": sid, "kind": kind, "level": level,
               "title": "", "blocks": [], "recorded": kind not in (None, "footnote"),
               "dom_depth": self.dom_depth}
        if sec["recorded"]:
            self.sections.append(sec)
        self.stack.append(sec)

    def handle_endtag(self, tag) -> None:
        if tag in SKIP_TAGS:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        if self.structured_depth:
            if tag == "math":
                self.math_depth = max(0, self.math_depth - 1)
                return
            if tag in self.LINE_TAGS:
                self.structured_buf.append("\n")
            if tag in self.VOID_TAGS:
                return
            self.structured_depth -= 1
            if self.structured_depth == 0:
                self._flush_structured()
            return
        if tag == "math":
            self.math_depth = max(0, self.math_depth - 1)
            return
        if self.suppress:
            if tag not in self.VOID_TAGS:
                self.suppress = max(0, self.suppress - 1)
            return
        if tag in ("section", "div") and self.stack:
            current = self.stack[-1]
            if current["tag"] == tag and current["dom_depth"] == self.dom_depth:
                self.flush_para()
                self.stack.pop()
        elif tag in ("h2", "h3", "h4", "h5", "h6") and self.capture == "heading":
            text = " ".join("".join(self.heading_parts).split())
            for sec in reversed(self.stack):
                if sec["recorded"] and not sec["title"]:
                    sec["title"] = text
                    break
            self.capture = None
        elif tag == "h1" and self.capture == "title":
            self.doc_title = " ".join("".join(self.title_parts).split())
            self.capture = None
        elif tag in ("p", "figcaption"):
            self.flush_para()
        elif tag in ("td", "th"):
            self._finish_cell()
        elif tag == "tr":
            if self.row is not None and self.table_rows is not None:
                width = max(self.row, default=-1) + 1
                self.table_rows.append([self.row.get(i, "") for i in range(width)])
            self.row = None
        elif tag == "table":
            self.table_depth = max(0, self.table_depth - 1)
            if self.table_depth == 0 and self.table_rows is not None:
                width = max((len(row) for row in self.table_rows), default=0)
                rows = [" | ".join(row + [""] * (width - len(row))) for row in self.table_rows]
                if rows:
                    self.emit("\n".join(rows), "Table: ")
                self.table_rows = None
                self.rowspans = {}
        if tag in ("section", "div"):
            self.dom_depth = max(0, self.dom_depth - 1)

    def handle_data(self, data) -> None:
        if self.skip or self.suppress or self.math_depth:
            return
        if self.structured_depth:
            self.structured_buf.append(data)
        elif self.table_depth and self.cell is not None:
            self.cell.append(data)
        elif self.capture == "title":
            self.title_parts.append(data)
        elif self.capture == "heading":
            self.heading_parts.append(data)
        elif self.capture in ("para", "caption"):
            self.buf.append(data)


def split_version(raw: str) -> tuple[str, str | None]:
    """F04: distinguish paper identity (base ID) from material version (vN).

    2608.12345v2 → ("2608.12345", "v2"); a bare ID → (id, None).
    Both modern IDs and legacy IDs (cs.AI/0309136) are valid; invalid input fails closed.
    """
    s = raw.strip().lower().removeprefix("arxiv:")
    version = None
    m = re.search(r"v(\d+)$", s)
    if m:
        version = "v" + m.group(1)
        s = s[: m.start()]
    if re.fullmatch(r"\d{4}\.\d{4,5}", s) or re.fullmatch(r"[a-z-]+(?:\.[a-z]{2})?/\d{7}", s):
        return s, version
    die("BAD_ARGS", f"Could not parse arXiv ID: {raw}")
    raise AssertionError  # die exits; this line is only for type checking.


def normalize_id(raw: str) -> str:
    """Return the normalized base ID for a paper identity; use split_version for versioned content retrieval."""
    base, _ = split_version(raw)
    return base


def safe_key(arxiv_id: str) -> str:
    """Make an ID safe for directory and cache keys; legacy IDs contain slashes and cannot be used as paths directly."""
    return arxiv_id.replace("/", "_")


def windows_system_proxy() -> str | None:
    """Read the manually configured system proxy from the Windows registry; return None when unavailable or disabled."""
    try:
        import winreg
    except ImportError:
        return None
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
        ) as key:
            enabled = winreg.QueryValueEx(key, "ProxyEnable")[0]
            server = winreg.QueryValueEx(key, "ProxyServer")[0]
    except OSError:
        return None
    if not enabled:
        return None
    server = str(server or "").strip()
    if "=" in server:  # For example, http=127.0.0.1:7890;https=127.0.0.1:7890; choose by scheme.
        per_protocol = {}
        for part in server.split(";"):
            name, _, value = part.partition("=")
            per_protocol[name.strip().lower()] = value.strip()
        server = per_protocol.get("https") or per_protocol.get("http") or ""
    if not server:
        return None
    if "://" not in server:
        server = f"http://{server}"
    return server


def proxy_candidates() -> list[str | None]:
    """Return candidate network routes in priority order; None means direct connection.

    httpx handles environment proxy variables itself (trust_env), so do not specify them again;
    add the Windows system proxy only when no environment proxy is set. Direct connection is always the final fallback.
    """
    candidates: list[str | None] = []
    env_proxied = any(os.environ.get(v) for v in (
        "HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy"))
    if not env_proxied and sys.platform == "win32":
        proxy = windows_system_proxy()
        if proxy:
            candidates.append(proxy)
    candidates.append(None)
    return candidates


def query_arxiv_version(base: str):
    """For a bare ID, confirm the current version through arXiv API metadata (F04: never assume v1).

    Return "vN" or None (a failed query or no result also returns None; version_status remains unknown and reading can continue).
    """
    import httpx
    import xml.etree.ElementTree as ET
    import urllib.parse

    url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode({"id_list": base})
    routes = proxy_candidates()
    try:
        resp = httpx.get(url, timeout=30.0, follow_redirects=True,
                         headers={"User-Agent": "grad-companion-arxiv-html/0.1"}, proxy=routes[-1])
        body = resp.text
    except Exception:
        for proxy in routes[:-1]:
            try:
                resp = httpx.get(url, timeout=30.0, follow_redirects=True,
                                 headers={"User-Agent": "grad-companion-arxiv-html/0.1"}, proxy=proxy)
                body = resp.text
                break
            except Exception:
                continue
        else:
            return None
    try:
        root = ET.fromstring(body)
        for entry in root.iter():
            if entry.tag.endswith("}id") and entry.text:
                m = re.search(r"arxiv\.org/abs/.*?(v\d+)$", entry.text.strip())
                if m:
                    return m.group(1)
    except ET.ParseError:
        pass
    return None


def fetch_html(versioned_id: str, cache_dir: Path, no_cache: bool):
    """Fetch HTML for a specific versioned ID and return (html, cached, fetched_at).

    Keep cache entries separate by version (versioned filename plus .meta.json). A cache hit preserves the original fetch time,
    rather than resetting it to today. Treat unversioned legacy cache entries as viewable content; do not assign them a confirmed version.
    """
    key = safe_key(versioned_id)
    cache_file = cache_dir / f"{key}.html"
    meta_file = cache_dir / f"{key}.meta.json"
    if not no_cache and cache_file.exists():
        age_days = (datetime.now().timestamp() - cache_file.stat().st_mtime) / 86400
        if age_days < CACHE_TTL_DAYS:
            fetched_at = None
            if meta_file.is_file():
                try:
                    fetched_at = json.loads(meta_file.read_text(encoding="utf-8")).get("fetched_at")
                except (OSError, json.JSONDecodeError):
                    fetched_at = None
            if fetched_at is None:
                fetched_at = datetime.fromtimestamp(
                    cache_file.stat().st_mtime, tz=timezone.utc).isoformat(timespec="seconds")
            return cache_file.read_text(encoding="utf-8"), True, fetched_at

    import httpx

    url = f"https://arxiv.org/html/{versioned_id}"
    routes = proxy_candidates()
    route_index = 0
    waits: list[float] = [0.0] + list(BACKOFF_SECONDS)
    for i, wait in enumerate(waits):
        if wait:
            time.sleep(wait)
        try:
            resp = httpx.get(url, timeout=30.0, follow_redirects=True,
                             headers={"User-Agent": "grad-companion-arxiv-html/0.1"},
                             proxy=routes[route_index])
        except Exception as exc:  # Retry another route after a connection-layer failure; report the error after backoff is exhausted.
            if i == len(waits) - 1:
                tried = ", ".join(r or "direct connection" for r in routes)
                die("NETWORK", f"Could not connect to arXiv (tried {tried}): {exc}")
            route_index = (route_index + 1) % len(routes)
            continue
        # An HTTP response confirms that this route works; keep using it for subsequent retries.
        if resp.status_code == 404:
            if re.search(r"v\d+$", versioned_id):
                die("NO_HTML", f"{url} returned 404: this paper has no HTML for this version, or its LaTeXML HTML is not available yet."
                               "Do not silently switch versions when a specific version was requested; check the version or retry without one.")
            die("NO_HTML", f"{url} returned 404: this paper has no LaTeXML HTML. Download the PDF and use an external parser.")
        if resp.status_code == 429:
            if i == len(waits) - 1:
                die("RATE_LIMITED", "arXiv returned 429 and retries were exhausted. Try again later.", retry_after=60)
            continue
        if resp.status_code != 200:
            die(f"HTTP_{resp.status_code}", f"arXiv HTML returned {resp.status_code}")
        text = resp.text
        if "ltx_document" not in text and "ltx_title_section" not in text:
            die("NO_HTML", f"{url} returned 200 but contains no LaTeXML structure (not an ltx_ page); section slicing is unavailable.")
        fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(text, encoding="utf-8")
        meta_file.write_text(json.dumps({
            "fetched_at": fetched_at,
            "versioned_id": versioned_id,
            "url": url,
            "content_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        }, ensure_ascii=False), encoding="utf-8")
        return text, False, fetched_at


def resolve_section(name: str, by_id: dict[str, dict]) -> str | None:
    s = name.strip()
    if not s:
        return None
    if s in by_id:                      # Already an anchor ID (S3.SS2.SSS1 / A4.SS1 / abstract / bib).
        return s
    # Numeric dotted form: 3 / 3.2 / 3.2.1 → S3 / S3.SS2 / S3.SS2.SSS1.
    # Appendix form: A1 / A4.1 / A10.10 → A1 / A4.SS1 / A10.SS10.
    m = re.fullmatch(r"([A-Za-z]?)(\d+)((?:\.\d+)*)", s)
    if not m:
        return None
    prefix = (m.group(1) or "S").upper()
    sid = f"{prefix}{m.group(2)}"
    tail = [t for t in m.group(3).split(".") if t]
    for depth, num in enumerate(tail):
        sid += f".{'SS' if depth == 0 else 'SSS'}{num}"
    return sid if sid in by_id else None


def section_text(sec_id: str, reader: LatexmlReader) -> str:
    parts: list[str] = []
    for sec in reader.sections:  # Document order, including each section and all descendants (ID prefix match).
        if sec["id"] == sec_id or sec["id"].startswith(sec_id + "."):
            hashes = "#" * max(2, (sec["level"] or 1) + 1)
            head = f"{hashes} {sec['title'] or sec['id']}"
            parts.append(head + ("\n\n" + "\n\n".join(sec["blocks"]) if sec["blocks"] else ""))
    return "\n\n".join(parts)


def main() -> None:
    ap = argparse.ArgumentParser(description="Slice full-text arXiv HTML by section")
    ap.add_argument("paper_id", help="arXiv ID, e.g. 2410.06992 (may include the arxiv: prefix or a v2 version suffix)")
    ap.add_argument("--outline", action="store_true", help="Return only the section outline so you can choose what to read")
    ap.add_argument("--sections", default="", help="Comma-separated section numbers, e.g. 3,3.2,A1 (S2.SS1 form is also accepted)")
    ap.add_argument("--cache-dir", default=".grad/cache/arxiv", help="HTML cache directory (default: .grad/cache/arxiv)")
    ap.add_argument("--no-cache", action="store_true", help="Bypass the cache and fetch again")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    base_id, requested_version = split_version(args.paper_id)
    cache_dir = Path(args.cache_dir)

    # F04/REV-05: an explicit version requests only that version. Confirm the current version for a bare ID through API metadata first;
    # do not select an arbitrary older cache by sorting filenames as strings (v10 < v2 is also wrong). Fall back to the
    # numerically highest known cached version only when the API is unreachable, and report version_status=cache-fallback.
    version = requested_version
    version_status = "confirmed" if version else None
    cache_fallback = False
    if version is None:
        if args.no_cache:
            # Explicit cache bypass: still use the API (the API itself is not a local cache).
            version = query_arxiv_version(base_id)
            version_status = "confirmed" if version else "unknown"
        else:
            version = query_arxiv_version(base_id)
            if version:
                version_status = "confirmed"
            else:
                # If the API is unreachable, choose the cached version with the largest number (not string order) and state that only local data was used.
                best = None
                for f in cache_dir.glob(f"{safe_key(base_id)}v*.html") if cache_dir.is_dir() else []:
                    tail = f.name[len(safe_key(base_id)):-len(".html")]
                    m = re.fullmatch(r"v(\d+)", tail)
                    if m and (best is None or int(m.group(1)) > best[0]):
                        best = (int(m.group(1)), f"v{m.group(1)}")
                if best:
                    version = best[1]
                    version_status = "cache-fallback"
                    cache_fallback = True
                else:
                    version_status = "unknown"
    versioned_id = f"{base_id}{version}" if version else base_id
    legacy_cache_only = False
    if requested_version is None and version is None:
        # If the version is unknown and no versioned cache exists, allow an unversioned legacy cache for viewing without assigning a version.
        old_cache = cache_dir / f"{safe_key(base_id)}.html"
        if not args.no_cache and old_cache.exists():
            legacy_cache_only = True
            versioned_id = base_id

    html, cached, fetched_at = fetch_html(versioned_id, cache_dir, args.no_cache)
    reader = LatexmlReader()
    reader.feed(html)
    reader.close()

    html_url = f"https://arxiv.org/html/{versioned_id}"
    base = {
        "id": base_id,
        "version": version,
        "version_status": "legacy" if legacy_cache_only else version_status,
        "requested_version": requested_version,
        "version_note": ("The API was unreachable; using the highest known local cached version only. The current online version may be newer."
                         if cache_fallback else
                         ("An unversioned legacy cache is available, but its version is unconfirmed." if legacy_cache_only else None)),
        "title": reader.doc_title,
        "html_url": html_url,
        "cached": cached,
        "fetched_at": fetched_at,
    }

    if args.sections:
        picked, missing = [], []
        for name in args.sections.split(","):
            if not name.strip():
                continue
            sid = resolve_section(name, {s["id"]: s for s in reader.sections})
            if sid is None:
                missing.append(name.strip())
            else:
                picked.append({"id": sid, "title": next(s["title"] for s in reader.sections if s["id"] == sid),
                               "url": f"{html_url}#{sid}", "text": section_text(sid, reader)})
        data = {**base, "sections": picked, "not_found": missing,
                "unread": [s["id"] for s in reader.sections
                           if s["id"] not in {p["id"] for p in picked}
                           and not any(p["id"] == s["id"] or s["id"].startswith(p["id"] + ".") for p in picked)]}
        if args.json:
            print(json.dumps({"ok": True, "data": data}, ensure_ascii=False))
            return
        print(f"# {reader.doc_title} ({versioned_id})")
        for p in picked:
            print(f"\n{p['url']}\n{p['text']}\n")
        if missing:
            print("Section numbers not found: " + ",".join(missing))
        return

    # Default to --outline.
    data = {**base, "sections": [
        {"id": s["id"], "level": s["level"], "kind": s["kind"], "title": s["title"],
         "paragraphs": len(s["blocks"])} for s in reader.sections]}
    if args.json:
        print(json.dumps({"ok": True, "data": data}, ensure_ascii=False))
        return
    print(f"# {reader.doc_title} ({versioned_id})")
    for s in data["sections"]:
        indent = "  " * max(0, (s["level"] or 1) - 1)
        print("{}{:<12} {}  [{}, {} sections]".format(indent, s["id"], s["title"], s["kind"], s["paragraphs"]))


if __name__ == "__main__":
    main()
