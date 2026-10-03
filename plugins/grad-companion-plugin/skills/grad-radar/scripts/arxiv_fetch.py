# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx"]
# ///
"""arXiv 元数据检索（阅读漏斗·阶段一：筛选）。

只用元数据（标题/摘要/作者/分类/日期），不取全文——大部分论文在这一层被筛掉。

网络约束（实测教训）：
- 端点必须用 https，http 返回 301
- 串行请求，间隔 >= 3s；429 指数退避 3s/6s/12s，耗尽后如实报错退出，不静默返回空结果
- httpx 默认只读环境变量代理、不读 Windows 系统代理：机器开着系统代理（Clash 等）时
  脚本仍直连，若直连被网络阻断（持续超时/reset），表现即「网络对 arXiv 持续阻断」。
  故显式读注册表系统代理；通道优先级 = 环境变量代理（httpx 自认）> 系统代理 > 直连，
  连接层失败才换通道，拿到过 HTTP 响应就固定通道

输出契约：--json 时 stdout 打印单个 JSON 对象：
  {"ok": true, "data": {...}}  或  {"ok": false, "error": "...", "detail": "..."}
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
MIN_INTERVAL = 3.0          # 请求间隔下限（秒）
BACKOFF_SECONDS = (3, 6, 12)  # 429/网络错误的指数退避
PAGE_SIZE = 100
MAX_PAGES = 3               # 单次运行最多 3 页，尊重 ToU

if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


def die(error: str, detail: str, **extra) -> None:
    print(json.dumps({"ok": False, "error": error, "detail": detail, **extra}, ensure_ascii=False))
    sys.exit(1)


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
        except Exception as exc:  # 连接层失败：换通道再试；退避耗尽后如实报错
            if i == len(waits) - 1:
                tried = "、".join(r or "直连" for r in routes)
                die("NETWORK", f"无法连接 arXiv（已尝试 {tried}）：{exc}")
            route_index = (route_index + 1) % len(routes)
            continue
        # 拿到 HTTP 响应说明当前通道能通，后续重试固定走它
        if resp.status_code == 200:
            return resp.text
        if resp.status_code == 429:
            if i == len(waits) - 1:
                die("RATE_LIMITED", "arXiv 返回 429，退避耗尽。请稍后再试（限速 1 req/3s）", retry_after=60)
            continue
        # 非 429 的 HTTP 错误：重试无意义，如实报错
        die(f"HTTP_{resp.status_code}", f"arXiv API 返回 {resp.status_code}：{resp.text[:200]}")


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
            # F04：元数据返回的当前版本与版本化链接——指定版本读取时以这两个为准，
            # 无 version 字段的旧消费者继续用 abs_url/html_url（基础 ID）
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
            continue  # 坏行跳过：台账局部损坏不应中断拉取
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
            time.sleep(MIN_INTERVAL)  # 翻页前强制间隔
        total, entries = parse_feed(http_get(last_url))
        papers.extend(entries)
        if not entries or len(papers) >= min(total, max_results):
            break
    return papers, total, last_url


def load_radar_config(path: str) -> dict:
    """读 .grad/config.json 的 radar 字段（keywords/categories/daily_caps）。

    只读不校验（校验归 radar_config.py）；解析失败 fail-closed——配置存在但读不懂
    不能假装没配置去用默认值，那会让用户的设置静默失效。
    """
    cfg_path = Path(path)
    if not cfg_path.is_file():
        die("NO_CONFIG", f"配置不存在：{cfg_path}；先运行 radar_config.py init，或去掉 --config 用显式参数")
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        die("BAD_CONFIG", f"配置无法解析：{cfg_path}：{exc}")
    if not isinstance(data, dict):
        die("BAD_CONFIG", f"配置根节点必须是 JSON 对象：{cfg_path}")
    return data


def main() -> None:
    ap = argparse.ArgumentParser(description="arXiv 元数据检索（筛选层）")
    ap.add_argument("--days", type=int, default=None,
                    help="回看天数（默认 3：arXiv 索引滞后 1-3 天）；--config 时可由配置 days 字段提供")
    ap.add_argument("--keywords", action="append", default=None,
                    help="逗号分隔关键词=一组（组内 AND）；重复给出=组间 OR。如 --keywords \"llm,agent\"；"
                         "给出任一组即整体替代配置组，不与配置混拼")
    ap.add_argument("--categories", default=None,
                    help="逗号分隔 arXiv 分类；显式给出时替代配置 categories")
    ap.add_argument("--config", default="",
                    help="从 .grad/config.json 读取 keywords/categories/days（显式 CLI 参数 > 配置 > 默认）")
    ap.add_argument("--max-results", type=int, default=100, help="上限（默认 100，封顶 300）")
    ap.add_argument("--seen-file", default=str(Path.home() / ".grad-radar" / "seen.jsonl"),
                    help="去重台账路径（默认 ~/.grad-radar/seen.jsonl，跨项目共享）")
    ap.add_argument("--no-dedup", action="store_true", help="不读写台账，全部视为 new")
    ap.add_argument("--json", action="store_true", help="stdout 输出 JSON")
    args = ap.parse_args()

    # 参数优先级：显式 CLI > 配置 > 默认（R12/R13）。argparse 默认全部置 None，
    # 才能区分「用户没传」与「用户传了和默认相同的值」。
    cli_categories = args.categories  # config 会改写 args.categories，先记住 CLI 原值
    config_used: list[str] = []
    groups: list[list[str]] | None = None
    if args.config:
        cfg = load_radar_config(args.config)
        if args.keywords is not None:
            groups = [k.split(",") for k in args.keywords]  # 重复传组=整体替代配置组，不与旧组混拼
            config_used.append("keywords=CLI")
        elif isinstance(cfg.get("keywords"), list) and cfg["keywords"]:
            if not all(isinstance(g, list) and g and all(isinstance(w, str) and w.strip() for w in g)
                       for g in cfg["keywords"]):
                die("BAD_CONFIG", f"配置 keywords 必须是非空字符串的嵌套数组：{args.config}")
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
                die("BAD_CONFIG", f"配置 days 必须是 >=1 的整数，收到 {days_value!r}")
            args.days = days_value
            config_used.append("days=config")
    # 无 --config 时补齐来源记录（--config 分支已逐项记录过）
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
        die("BAD_ARGS", "--days 必须 >= 1")
    if not groups and not categories:
        die("BAD_ARGS", "keywords 与 categories 至少给一个（CLI 或 --config 均可）")
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
        "effective_params": {  # 用户可见的实际生效参数（R12/R13 验收：查询用的是谁的值一目了然）
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

    print(f"查询：{query}")
    print(f"有效参数：days={args.days}｜分类={','.join(categories) or '（无）'}｜"
          f"来源：{'、'.join(data['effective_params']['sources'])}")
    print(f"命中 {total}，取回 {len(papers)}，其中新 {len(new_ids)}" + ("（已截断）" if total > len(papers) else ""))
    for p in papers:
        flag = "新 " if p["new"] else "  "
        first_author = p["authors"][0] if p["authors"] else "?"
        more = f" 等{len(p['authors'])}人" if len(p["authors"]) > 1 else ""
        print(f"{flag}arXiv:{p['id']}  {p['title']}  [{first_author}{more} / {p['primary_category']}]")
        print(f"     {p['abs_url']}")


if __name__ == "__main__":
    main()
