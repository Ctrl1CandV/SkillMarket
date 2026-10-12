# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx"]
# ///
"""Search arXiv metadata (reading funnel, stage 1: screening).

Use metadata only (title, abstract, authors, categories, and date), not full text; most papers are filtered out at this stage.

Network constraints (lessons from actual use):
- Use HTTPS endpoints; HTTP returns 301.
- Send requests serially with at least 3 seconds between them. Back off after 429 responses for 3/6/12 seconds; report an error after retries are exhausted rather than silently returning no results.
- httpx reads environment proxy variables by default, but not the Windows system proxy. If a system proxy (such as Clash) is enabled,
  the script would still connect directly; repeated timeouts or resets would look like a persistent network block on arXiv.
  Read the system proxy from the registry explicitly. Route priority: environment proxy (handled by httpx) > system proxy > direct connection;
  switch routes only after a connection-layer failure, and keep the route after receiving an HTTP response.

Output contract: with --json, stdout prints one JSON object:
  {"ok": true, "data": {...}} or {"ok": false, "error": "...", "detail": "..."}
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

API_URL = "https://export.arxiv.org/api/query"
ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"
OPENSEARCH = "{http://a9.com/-/spec/opensearch/1.1/}"
MIN_INTERVAL = 3.0          # Minimum interval between requests (seconds)
BACKOFF_SECONDS = (3, 6, 12)  # Exponential backoff for 429 responses and network errors
PAGE_SIZE = 100
MAX_PAGES = 3               # At most 3 pages per run, in respect of the Terms of Use

if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


def die(error: str, detail: str, **extra) -> None:
    print(json.dumps({"ok": False, "error": error, "detail": detail, **extra}, ensure_ascii=False))
    sys.exit(1)


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
    if "=" in server:  # For example, http=127.0.0.1:7890;https=127.0.0.1:7890; select the proxy by scheme.
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


def http_get(url: str) -> str:
    import httpx

    routes = proxy_candidates()
    route_index = 0
    waits: list[float] = [0.0] + list(BACKOFF_SECONDS)
    for i, wait in enumerate(waits):
        if wait:
            time.sleep(wait)
        try:
            resp = httpx.get(
                url,
                timeout=30.0,
                follow_redirects=True,
                headers={"User-Agent": "grad-companion-arxiv-fetch/0.1"},
                proxy=routes[route_index],
            )
        except Exception as exc:  # Retry on connection-layer failures; report the error after backoff is exhausted.
            if i == len(waits) - 1:
                tried = ", ".join(r or "direct connection" for r in routes)
                die("NETWORK", f"Could not connect to arXiv (tried {tried}): {exc}")
            route_index = (route_index + 1) % len(routes)
            continue
        # An HTTP response confirms that this route works; keep using it for subsequent retries.
        if resp.status_code == 200:
            return resp.text
        if resp.status_code == 429:
            if i == len(waits) - 1:
                die("RATE_LIMITED", "arXiv returned 429 and retries were exhausted. Try again later (limit: 1 request per 3 seconds).", retry_after=60)
            continue
        # Retrying a non-429 HTTP error is not useful; report it as received.
        die(f"HTTP_{resp.status_code}", f"arXiv API returned {resp.status_code}: {resp.text[:200]}")


def build_search_query(categories: list[str], groups: list[list[str]],
                       start: datetime, end: datetime) -> str:
    parts: list[str] = []
    if categories:
        parts.append("(" + " OR ".join(f"cat:{c.strip()}" for c in categories if c.strip()) + ")")
    or_terms: list[str] = []
    for group in groups:
        terms = [t.strip() for t in group if t.strip()]
        if not terms:
            continue
        one = [f'all:"{t}"' for t in terms]
        or_terms.append(one[0] if len(one) == 1 else "(" + " AND ".join(one) + ")")
    if or_terms:
        parts.append("(" + " OR ".join(or_terms) + ")")
    parts.append(f"submittedDate:[{start:%Y%m%d%H%M} TO {end:%Y%m%d%H%M}]")
    return " AND ".join(parts)


def parse_feed(xml_text: str) -> tuple[int, list[dict]]:
    root = ET.fromstring(xml_text)
    try:
        total = int(root.findtext(f"{OPENSEARCH}totalResults", default="0"))
    except ValueError:
        total = 0
    entries: list[dict] = []
    for e in root.findall(f"{ATOM}entry"):
        id_text = e.findtext(f"{ATOM}id", default="") or ""
        m = re.search(r"/abs/(.+)$", id_text)
        raw = m.group(1) if m else id_text
        version = ""
        vm = re.search(r"v\d+$", raw)
        if vm:
            version = vm.group(0)
            raw = raw[: vm.start()]
        primary = e.find(f"{ARXIV_NS}primary_category")
        entries.append({
            "id": raw,
            "version": version,
            "title": " ".join((e.findtext(f"{ATOM}title", default="") or "").split()),
            "abstract": " ".join((e.findtext(f"{ATOM}summary", default="") or "").split()),
            "authors": [a.findtext(f"{ATOM}name", default="") for a in e.findall(f"{ATOM}author")],
            "primary_category": primary.get("term") if primary is not None else None,
            "categories": [c.get("term", "") for c in e.findall(f"{ATOM}category")],
            "published": e.findtext(f"{ATOM}published", default=""),
            "updated": e.findtext(f"{ATOM}updated", default=""),
            "abs_url": f"https://arxiv.org/abs/{raw}",
            "html_url": f"https://arxiv.org/html/{raw}",
            # F04: metadata provides the current version and versioned links; use them when a specific version is requested.
            # Older consumers without a version field continue to use abs_url/html_url (the base ID).
            "abs_versioned_url": f"https://arxiv.org/abs/{raw}{version}",
            "html_versioned_url": (f"https://arxiv.org/html/{raw}{version}" if version else None),
        })
    return total, entries


def load_seen_ids(path: Path) -> set[str]:
    seen: set[str] = set()
    if not path.exists():
        return seen
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            seen.add(json.loads(line).get("id", ""))
        except json.JSONDecodeError:
            continue  # Skip malformed rows; a partially damaged ledger should not stop the fetch.
    seen.discard("")
    return seen


def append_seen(path: Path, new_ids: list[str]) -> None:
    if not new_ids:
        return
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for pid in new_ids:
            f.write(json.dumps({"id": pid, "first_seen": now}, ensure_ascii=False) + "\n")


def fetch_all(query: str, max_results: int) -> tuple[list[dict], int, str]:
    papers: list[dict] = []
    total = 0
    last_url = ""
    for page in range(MAX_PAGES):
        remaining = max_results - len(papers)
        if remaining <= 0:
            break
        params = {
            "search_query": query,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "start": page * PAGE_SIZE,
            "max_results": min(PAGE_SIZE, remaining),
        }
        last_url = API_URL + "?" + urllib.parse.urlencode(params)
        if page > 0:
            time.sleep(MIN_INTERVAL)  # Enforce the delay before fetching the next page.
        total, entries = parse_feed(http_get(last_url))
        papers.extend(entries)
        if not entries or len(papers) >= min(total, max_results):
            break
    return papers, total, last_url


def load_radar_config(path: str) -> dict:
    """Read the radar fields (keywords/categories/daily_caps) from .grad/config.json.

    Read without validating (validation belongs to radar_config.py). Fail closed if parsing fails: if a config exists but cannot
    be read, do not pretend it is absent and silently use defaults, which would ignore the user settings.
    """
    cfg_path = Path(path)
    if not cfg_path.is_file():
        die("NO_CONFIG", f"Configuration not found: {cfg_path}; run radar_config.py init or omit --config and pass explicit options.")
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        die("BAD_CONFIG", f"Could not parse configuration: {cfg_path}: {exc}")
    if not isinstance(data, dict):
        die("BAD_CONFIG", f"The configuration root must be a JSON object: {cfg_path}")
    return data


def main() -> None:
    ap = argparse.ArgumentParser(description="Search arXiv metadata (screening stage)")
    ap.add_argument("--days", type=int, default=None,
                    help="Look back this many days (default 3: arXiv indexing can lag by 1–3 days); with --config, use its days field")
    ap.add_argument("--keywords", action="append", default=None,
                    help="Comma-separated keywords form one group (AND within each group); repeated options mean OR across groups. Example: --keywords \"llm,agent\";"
                         "Supplying any group replaces all configured groups; CLI groups are not merged with configured groups")
    ap.add_argument("--categories", default=None,
                    help="Comma-separated arXiv categories; when specified, replaces configured categories")
    ap.add_argument("--config", default="",
                    help="Read keywords/categories/days from .grad/config.json (explicit CLI options > config > defaults)")
    ap.add_argument("--max-results", type=int, default=100, help="Maximum results (default 100, capped at 300)")
    ap.add_argument("--seen-file", default=str(Path.home() / ".grad-radar" / "seen.jsonl"),
                    help="Deduplication ledger (default ~/.grad-radar/seen.jsonl, shared across projects)")
    ap.add_argument("--no-dedup", action="store_true", help="Do not read or write the ledger; treat every result as new")
    ap.add_argument("--json", action="store_true", help="Print JSON to stdout")
    args = ap.parse_args()

    # Priority: explicit CLI options > config > defaults (R12/R13). argparse defaults are all None,
    # which distinguishes an omitted option from one explicitly set to the same value as its default.
    cli_categories = args.categories  # Applying config rewrites args.categories, so preserve the original CLI value first.
    config_used: list[str] = []
    groups: list[list[str]] | None = None
    if args.config:
        cfg = load_radar_config(args.config)
        if args.keywords is not None:
            groups = [k.split(",") for k in args.keywords]  # Repeated groups replace all configured groups rather than merging with them.
            config_used.append("keywords=CLI")
        elif isinstance(cfg.get("keywords"), list) and cfg["keywords"]:
            if not all(isinstance(g, list) and g and all(isinstance(w, str) and w.strip() for w in g)
                       for g in cfg["keywords"]):
                die("BAD_CONFIG", f"Configured keywords must be a nested array of non-empty strings: {args.config}")
            groups = cfg["keywords"]
            config_used.append("keywords=config")
        if args.categories is not None:
            config_used.append("categories=CLI")
        elif isinstance(cfg.get("categories"), list) and cfg["categories"]:
            args.categories = ",".join(str(c) for c in cfg["categories"])
            config_used.append("categories=config")
        if args.days is not None:
            config_used.append("days=CLI")
        elif cfg.get("days") is not None:
            days_value = cfg["days"]
            if isinstance(days_value, bool) or not isinstance(days_value, int) or days_value < 1:
                die("BAD_CONFIG", f"Configured days must be an integer >= 1; got {days_value!r}")
            args.days = days_value
            config_used.append("days=config")
    # Record defaults when --config is absent; the --config branch records each source separately.
    if groups is None and args.keywords is not None:
        groups = [k.split(",") for k in args.keywords]
        config_used.append("keywords=CLI")
    elif groups is None and "keywords=config" not in config_used and "keywords=CLI" not in config_used:
        config_used.append("keywords=none")
    groups = groups or []
    if "categories=CLI" not in config_used and "categories=config" not in config_used:
        config_used.append("categories=CLI" if cli_categories is not None else "categories=none")
    if args.days is None:
        args.days = 3
        config_used.append("days=default")
    elif "days=CLI" not in config_used and "days=config" not in config_used:
        config_used.append("days=CLI")
    categories = [c.strip() for c in (args.categories or "").split(",") if c.strip()]

    if args.days < 1:
        die("BAD_ARGS", "--days must be >= 1")
    if not groups and not categories:
        die("BAD_ARGS", "At least one of keywords or categories is required (from CLI or --config)")
    max_results = min(args.max_results, PAGE_SIZE * MAX_PAGES)
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=args.days)
    query = build_search_query(categories, groups, start, end)

    papers, total, api_url = fetch_all(query, max_results)

    seen_path = Path(args.seen_file)
    seen = set() if args.no_dedup else load_seen_ids(seen_path)
    new_ids: list[str] = []
    for p in papers:
        is_new = p["id"] not in seen
        p["new"] = is_new
        if is_new:
            new_ids.append(p["id"])
    if not args.no_dedup:
        append_seen(seen_path, new_ids)

    data = {
        "query": query,
        "api_url": api_url,
        "effective_params": {  # Parameters actually used; R12/R13 make the source of each value visible.
            "days": args.days,
            "categories": categories,
            "keyword_groups": groups,
            "sources": config_used,
        },
        "window": {"start": start.isoformat(timespec="seconds"), "end": end.isoformat(timespec="seconds")},
        "total_matches": total,
        "fetched": len(papers),
        "new": len(new_ids),
        "truncated": total > len(papers),
        "papers": papers,
    }
    if args.json:
        print(json.dumps({"ok": True, "data": data}, ensure_ascii=False))
        return

    print(f"Query: {query}")
    categories_text = ", ".join(categories) or "(none)"; sources_text = ", ".join(data["effective_params"]["sources"])
    print(f"Effective parameters: days={args.days} | categories={categories_text} | sources: {sources_text}")
    print(f"Matched {total}; fetched {len(papers)}; new {len(new_ids)}" + (" (truncated)" if total > len(papers) else ""))
    for p in papers:
        flag = "NEW " if p["new"] else "    "
        first_author = p["authors"][0] if p["authors"] else "?"
        more = " and {} more".format(len(p["authors"])) if len(p["authors"]) > 1 else ""
        print(f"{flag}arXiv:{p['id']}  {p['title']}  [{first_author}{more} / {p['primary_category']}]")
        print(f"     {p['abs_url']}")


if __name__ == "__main__":
    main()
