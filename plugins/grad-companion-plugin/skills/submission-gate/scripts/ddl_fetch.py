# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx"]
# ///
"""从 ccfddl 拉会议截稿日期（submission-gate 的倒排期数据源）。

YAML 解析仅用标准库（不引 pyyaml：行式状态机解析，缩进结构已实测稳定）；HTTP 使用 httpx。

数据源：https://ccfddl.com/conference/allconf.yml（约 365KB，实测 200）
缓存：.grad/cache/ccfddl/allconf.yml，TTL 7 天——每周最多拉一次，可用 --refresh 强制。

网络通道：环境变量代理（httpx 自认）> Windows 系统代理（httpx 不读注册表，显式补读）> 直连；
连接层失败换通道重试。直连 ccfddl 目前可通，但与 arXiv 同属脚本唯一的出口，统一走此逻辑。

解析只认缩进结构（实测样例）：
  - title: ICLR            ← 顶级会议条目（列 0）
    confs:                 ← 年份列表
    - year: 2027           ← 年份条目（缩进 2）
      timeline:
      - abstract_deadline: '2026-09-18 23:59:59'   ← timeline 项（缩进 4，带破折号）
        deadline: '2026-09-25 23:59:59'            ← timeline 字段（缩进 6）

输出契约：--json 时 stdout 打印 {"ok": true, "data": {...}} 或 {"ok": false, ...}。
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
            continue  # 会议级字段（sub/rank/dblp）不需要
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
                if key != "timeline":  # `timeline:` 是容器标记，不覆盖已初始化的列表
                    cur_entry[key] = val
                cur_tl = None
    return confs


def windows_system_proxy() -> str | None:
    """读 Windows 注册表的系统代理（手动代理那档）；非 Windows 或未启用返回 None。"""
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
    if "=" in server:  # 形如 http=127.0.0.1:7890;https=127.0.0.1:7890，按协议取
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
    """联网通道候选，按优先级排列；None 表示直连。

    环境变量代理 httpx 自己会认（trust_env），设了就不重复指定；
    没设时补上它不读的 Windows 系统代理。直连永远垫底作回退。
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
            network_error = f"HTTP_{resp.status_code}: ccfddl 返回 {resp.status_code}"
        except Exception as exc:
            network_error = f"NETWORK: {exc}"
            if attempt < len(routes) - 1:  # 连接层失败：还有别的通道就换一条
                route_index = (route_index + 1) % len(routes)
        if attempt == 0:
            time.sleep(3)

    if cache_exists:
        try:
            text = cache_file.read_text(encoding="utf-8")
        except OSError as exc:
            die("CACHE_READ_FAILED", f"网络失败且过期缓存无法读取：{exc}", network_error=network_error)
        return text, {
            "status": "stale", "age_days": round(cache_age_days or 0.0, 3),
            "network_error": network_error,
        }
    die("NETWORK", f"无法连接 ccfddl，且没有可用缓存：{network_error}")
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
    """保留 ccfddl 的每个 timeline；comment 是原始说明，不臆造阶段类型。"""
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
        # 兼容 0.1.1 调用方；完整结果以 timelines 为准。
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
    ap = argparse.ArgumentParser(description="ccfddl 会议截稿日期")
    ap.add_argument("--venues", default="ICLR", help="逗号分隔的会议名（大小写不敏感，子串匹配。如 ACL 会同时命中 EACL/NAACL；要精确匹配加 --exact）")
    ap.add_argument("--cache-dir", default=".grad/cache/ccfddl")
    ap.add_argument("--refresh", action="store_true", help="忽略 TTL 强制重拉")
    ap.add_argument("--exact", action="store_true", help="只匹配完全同名的会议")
    ap.add_argument("--all-years", action="store_true", help="不过滤，返回全部年份条目")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    text, cache_info = fetch_yaml(Path(args.cache_dir) / "allconf.yml", args.refresh)
    confs = parse_allconf(text)
    wanted = [v.strip().lower() for v in args.venues.split(",") if v.strip()]
    if not wanted:
        die("BAD_ARGS", "--venues 不能为空")

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
        die("NOT_FOUND", f"ccfddl 中未找到这些会议：{args.venues}。可换用子串匹配的写法或 --venues 给全名")

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
                print("    - timeline-1：abstract — | deadline — | 倒计时未知")
            for tl in e["timelines"]:
                abstract_days = tl["days_until_abstract"]
                deadline_days = tl["days_until_deadline"]
                abstract_s = f"{abstract_days:+d} 天" if abstract_days is not None else "未知"
                deadline_s = f"{deadline_days:+d} 天" if deadline_days is not None else "未知"
                print(f"    - {tl['name']}：abstract {tl['abstract_deadline'] or '—'} ({abstract_s}) | "
                      f"deadline {tl['deadline'] or '—'} ({deadline_s})")


if __name__ == "__main__":
    main()
