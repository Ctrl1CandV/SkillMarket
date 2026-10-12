# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx"]
# ///
"""Fetch conference deadlines from ccfddl (the deadline source for submission-gate).

Parse YAML with the standard library only (no pyyaml: the line-based state machine has been verified against the source indentation); use httpx for HTTP.

Source: https://ccfddl.com/conference/allconf.yml (about 365 KB; verified HTTP 200).
Cache: .grad/cache/ccfddl/allconf.yml, TTL 7 days—fetch at most once a week unless --refresh is used.

Network routes: environment proxy (handled by httpx) > Windows system proxy (read explicitly because httpx ignores the registry) > direct connection;
retry another route only after a connection-layer failure. Direct access to ccfddl currently works, and ccfddl is one of this script two external endpoints, so use the same routing logic.

Parse only the indentation structure (verified against examples):
  - title: ICLR            ← Top-level conference entry (column 0)
    confs:                 ← Year list
    - year: 2027           ← Year entry (indentation 2)
      timeline:
      - abstract_deadline: '2026-09-18 23:59:59'   ← Timeline item (indentation 4, with a dash)
        deadline: '2026-09-25 23:59:59'            ← Timeline field (indentation 6)

Output contract: with --json, stdout prints {"ok": true, "data": {...}} or {"ok": false, ...}.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

YAML_URL = "https://ccfddl.com/conference/allconf.yml"
CACHE_TTL_DAYS = 7.0

if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


def die(error: str, detail: str, **extra) -> None:
    print(json.dumps({"ok": False, "error": error, "detail": detail, **extra}, ensure_ascii=False))
    sys.exit(1)


def strip_q(v: str) -> str:
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
        return v[1:-1]
    return v


def parse_allconf(text: str) -> list[dict]:
    confs: list[dict] = []
    cur_conf: dict | None = None
    cur_entry: dict | None = None
    cur_tl: dict | None = None
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        m = re.match(r"- title:\s*(.+)$", line)
        if indent == 0 and m:
            cur_conf = {"title": strip_q(m.group(1)), "entries": []}
            confs.append(cur_conf)
            cur_entry = cur_tl = None
            continue
        if cur_conf is None:
            continue
        m = re.match(r"- year:\s*(\d+)", line)
        if m and indent <= 2:
            cur_entry = {"year": int(m.group(1)), "timeline": []}
            cur_conf["entries"].append(cur_entry)
            cur_tl = None
            continue
        if cur_entry is None:
            continue  # Conference-level fields (sub/rank/dblp) are not needed.
        m = re.match(r"- (\w+):\s*(.*)$", line)
        if m and indent >= 4:
            cur_tl = {m.group(1): strip_q(m.group(2))}
            cur_entry["timeline"].append(cur_tl)
            continue
        m = re.match(r"(\w+):\s*(.*)$", line)
        if m:
            key, val = m.group(1), strip_q(m.group(2))
            if cur_tl is not None and indent >= 6:
                cur_tl[key] = val
            else:
                if key != "timeline":  # The timeline: key marks a container; do not overwrite the initialized list.
                    cur_entry[key] = val
                cur_tl = None
    return confs


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


def fetch_yaml(cache_file: Path, refresh: bool) -> tuple[str, dict]:
    cache_exists = cache_file.is_file()
    cache_age_days = None
    if cache_exists:
        cache_age_days = (datetime.now().timestamp() - cache_file.stat().st_mtime) / 86400
        if not refresh and cache_age_days < CACHE_TTL_DAYS:
            return cache_file.read_text(encoding="utf-8"), {
                "status": "hit", "age_days": round(cache_age_days, 3), "network_error": None,
            }

    import httpx

    routes = proxy_candidates()
    route_index = 0
    network_error = None
    for attempt in range(2):
        try:
            resp = httpx.get(YAML_URL, timeout=60.0, follow_redirects=True,
                             headers={"User-Agent": "grad-companion-ddl-fetch/0.1"},
                             proxy=routes[route_index])
            if resp.status_code == 200:
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                cache_file.write_text(resp.text, encoding="utf-8")
                return resp.text, {"status": "miss", "age_days": 0.0, "network_error": None}
            network_error = f"HTTP_{resp.status_code}: ccfddl returned {resp.status_code}"
        except Exception as exc:
            network_error = f"NETWORK: {exc}"
            if attempt < len(routes) - 1:  # On connection-layer failure, try another route if available.
                route_index = (route_index + 1) % len(routes)
        if attempt == 0:
            time.sleep(3)

    if cache_exists:
        try:
            text = cache_file.read_text(encoding="utf-8")
        except OSError as exc:
            die("CACHE_READ_FAILED", f"Network request failed and the expired cache could not be read: {exc}", network_error=network_error)
        return text, {
            "status": "stale", "age_days": round(cache_age_days or 0.0, 3),
            "network_error": network_error,
        }
    die("NETWORK", f"Could not connect to ccfddl, and no usable cache is available: {network_error}")
    raise AssertionError("unreachable")


def parse_timezone(name: str | None):
    if not name:
        return None
    value = name.strip()
    if value == "AoE":
        return timezone(timedelta(hours=-12))
    if value == "UTC":
        return timezone.utc
    match = re.fullmatch(r"UTC([+-])(\d{1,2})", value)
    if match:
        hours = int(match.group(2)) * (1 if match.group(1) == "+" else -1)
        if -23 <= hours <= 23:
            return timezone(timedelta(hours=hours))
        return None
    if value == "PT":
        try:
            return ZoneInfo("America/Los_Angeles")
        except ZoneInfoNotFoundError:
            return None
    return None


def days_until(date_str: str, timezone_name: str | None = None, now: datetime | None = None) -> int | None:
    target_tz = parse_timezone(timezone_name)
    if target_tz is None:
        return None
    try:
        target = datetime.strptime(date_str or "", "%Y-%m-%d %H:%M:%S").replace(tzinfo=target_tz)
    except ValueError:
        return None
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return (target.date() - current.astimezone(target_tz).date()).days


def normalize_timelines(items: list[dict], timezone_name: str | None = None) -> list[dict]:
    """Preserve every ccfddl timeline; comment is the source wording, so do not invent stage types."""
    normalized = []
    for index, item in enumerate(items, 1):
        abstract = item.get("abstract_deadline") or None
        deadline = item.get("deadline") or None
        comment = item.get("comment") or None
        normalized.append({
            "name": comment or f"timeline-{index}",
            "comment": comment,
            "abstract_deadline": abstract,
            "deadline": deadline,
            "days_until_abstract": days_until(abstract or "", timezone_name),
            "days_until_deadline": days_until(deadline or "", timezone_name),
            "origin": item.get("origin") or "timeline",
        })
    return normalized


def normalize_entry(entry: dict) -> dict:
    timezone_name = entry.get("timezone") or None
    raw_timelines = list(entry.get("timeline") or [])
    entry_abstract = entry.get("abstract_deadline") or None
    entry_deadline = entry.get("deadline") or None
    if entry_abstract or entry_deadline:
        raw_timelines.append({
            "abstract_deadline": entry_abstract or "",
            "deadline": entry_deadline or "",
            "comment": "entry-level deadline",
            "origin": "entry",
        })
    timelines = normalize_timelines(raw_timelines, timezone_name)
    first = timelines[0] if timelines else {
        "abstract_deadline": None, "deadline": None,
        "days_until_abstract": None, "days_until_deadline": None,
    }
    return {
        "year": entry["year"],
        "conf_id": entry.get("id") or None,
        "link": entry.get("link") or None,
        "timezone": timezone_name,
        "conf_date": entry.get("date") or None,
        "entry_abstract_deadline": entry_abstract,
        "entry_deadline": entry_deadline,
        "days_until_entry_abstract": days_until(entry_abstract or "", timezone_name),
        "days_until_entry_deadline": days_until(entry_deadline or "", timezone_name),
        # Backward compatibility for callers on 0.1.1; the complete result is in timelines.
        "abstract_deadline": first["abstract_deadline"],
        "deadline": first["deadline"],
        "days_until_deadline": first["days_until_deadline"],
        "days_until_abstract": first["days_until_abstract"],
        "timelines": timelines,
    }


def venue_matches(title: str, wanted: list[str], exact: bool) -> bool:
    title_l = title.lower()
    if exact:
        return any(w == title_l for w in wanted)
    return any(w == title_l or w in title_l for w in wanted)


def main() -> None:
    ap = argparse.ArgumentParser(description="Conference deadlines from ccfddl")
    ap.add_argument("--venues", default="ICLR", help="Comma-separated conference names (case-insensitive substring match; ACL may also match EACL/NAACL; use --exact for exact names)")
    ap.add_argument("--cache-dir", default=".grad/cache/ccfddl")
    ap.add_argument("--refresh", action="store_true", help="Ignore the TTL and fetch again")
    ap.add_argument("--exact", action="store_true", help="Match conference names exactly")
    ap.add_argument("--all-years", action="store_true", help="Do not filter; return entries for all years")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    text, cache_info = fetch_yaml(Path(args.cache_dir) / "allconf.yml", args.refresh)
    confs = parse_allconf(text)
    wanted = [v.strip().lower() for v in args.venues.split(",") if v.strip()]
    if not wanted:
        die("BAD_ARGS", "--venues must not be empty")

    now_year = datetime.now().year
    out = []
    for conf in confs:
        if not venue_matches(conf["title"], wanted, args.exact):
            continue
        entries = []
        for entry in conf["entries"]:
            if not args.all_years and entry["year"] < now_year - 1:
                continue
            entries.append(normalize_entry(entry))

        if entries:
            out.append({"title": conf["title"], "entries": sorted(entries, key=lambda x: -x["year"])})

    if not out:
        die("NOT_FOUND", f"No conferences found in ccfddl for: {args.venues}. Try substring matching or pass each full name with --venues.")

    data = {"fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "cache": cache_info["status"], "cache_age_days": cache_info["age_days"],
            "network_error": cache_info["network_error"], "venues": out}
    if args.json:
        print(json.dumps({"ok": True, "data": data}, ensure_ascii=False))
        return
    for v in out:
        print(f"## {v['title']}")
        for e in v["entries"]:
            print(f"  {e['year']} | {e['timezone'] or ''} | {e['conf_date'] or ''}")
            if not e["timelines"]:
                print("    - timeline-1: abstract — | deadline — | countdown unknown")
            for tl in e["timelines"]:
                abstract_days = tl["days_until_abstract"]
                deadline_days = tl["days_until_deadline"]
                abstract_s = f"{abstract_days:+d} days" if abstract_days is not None else "unknown"
                deadline_s = f"{deadline_days:+d} days" if deadline_days is not None else "unknown"
                print(f"    - {tl['name']}：abstract {tl['abstract_deadline'] or '—'} ({abstract_s}) | "
                      f"deadline {tl['deadline'] or '—'} ({deadline_s})")


if __name__ == "__main__":
    main()
