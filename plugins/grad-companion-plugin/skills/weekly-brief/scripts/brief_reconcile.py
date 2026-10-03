# /// script
# requires-python = ">=3.12"
# ///
"""组会承诺对账（weekly-brief）。提取上一份 brief 的计划条目 + 本期证据池，供 agent 机械对账。

分工边界（Type-A / Type-B）：
- 本脚本只做**机械提取**：待对账条目、证据池（commit / run 新增与补录 / claim 变化）、时间窗计算
- 「条目是否兑现」由 agent 按 SKILL.md 规则判断：**证据直接覆盖承诺才算完成；只覆盖一部分标
  部分完成；无证据标未找到完成证据；数据源读不了标无法核对（不等于证明没做）**。脚本不替人下结论

时间窗（F03）：本期窗口由生成方明确给出——CLI 不给时默认宿主当地「今天及之前 6 天」。
prev brief 只提供待核对计划与问题，**不再从其标题推导本期**。
--since/--until 起止都含当天（按起日 00:00 至结束日后一天 00:00 半开区间）；
只给一侧时另一侧 ±6 天。带时区的时间戳统一换算到宿主当地时区再比较；
无时区的历史时间戳标 legacy，不宣称精确跨时区归属。
证据池三源：git log、.grad/runs/（new_runs 按 created_at、updated_runs 按 updated_at 补录）、
claims.jsonl 新增行（含 support 判定）。

输出契约：--json 时 stdout 打印 {"ok": true, "data": {...}} 或 {"ok": false, ...}。
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, tzinfo
from pathlib import Path

if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


def die(error: str, detail: str, **extra) -> None:
    print(json.dumps({"ok": False, "error": error, "detail": detail, **extra}, ensure_ascii=False))
    sys.exit(1)


def parse_prev_date(text: str) -> str | None:
    """brief 头部格式：`# 周报 · YYYY-MM-DD ~ YYYY-MM-DD` 或 frontmatter date。"""
    m = re.search(r"#\s*周报\s*·\s*(\d{4}-\d{2}-\d{2})", text)
    if m:
        return m.group(1)
    m = re.match(r"^---\n.*?^date:\s*(\d{4}-\d{2}-\d{2})", text, re.S | re.M)
    return m.group(1) if m else None


def extract_plan_items(text: str) -> list[str]:
    """「下周计划」段的顶层 bullet；无该段返回空表。"""
    m = re.search(r"^#+\s*[^#\n]*下周计划[^\n]*\n(.*?)(?=^#{1,3}\s|\Z)", text, re.S | re.M)
    if not m:
        return []
    items = []
    for line in m.group(1).splitlines():
        bullet = re.match(r"^\s*[-*]\s+(.*)$", line)
        if bullet:
            item = bullet.group(1).strip()
            if item:
                items.append(item)
    return items


def extract_pending_decisions(text: str) -> list[str]:
    """「需要拍板」/「拍板的问题」段的条目；无该段返回空表。"""
    m = re.search(r"^#+\s*[^#\n]*(?:需要导师拍板|拍板的问题|需要拍板)[^\n]*\n(.*?)(?=^#{1,3}\s|\Z)",
                  text, re.S | re.M)
    if not m:
        return []
    items = []
    for line in m.group(1).splitlines():
        bullet = re.match(r"^\s*(?:[-*]|\d+[.)])\s+(.*)$", line)
        if bullet:
            item = bullet.group(1).strip()
            if item:
                items.append(item)
    return items


def git_log(repo: Path, start: datetime, end: datetime) -> dict:
    """REV-09：区分「读不了」与「确实没有」——不可用时给非空 reason，周报据此标无法核对。"""
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "log", "--since", start.isoformat(),
             "--until", end.isoformat(),
             "--pretty=format:%h%x00%ad%x00%s", "--date=short"],
            capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as exc:
        return {"commits": [], "source_status": "unavailable",
                "reason": f"git 返回 {exc.returncode}（非 git 目录/缺历史）：证据池不可用，不是零证据"}
    except OSError as exc:
        return {"commits": [], "source_status": "unavailable",
                "reason": f"git 不可执行：{exc}：证据池不可用，不是零证据"}
    commits = []
    for line in proc.stdout.splitlines():
        parts = line.split("\x00")
        if len(parts) == 3 and parts[0].strip():
            commits.append({"hash": parts[0], "date": parts[1], "subject": parts[2]})
    return {"commits": commits, "source_status": "ok", "reason": None}


def to_local(ts: str | None) -> tuple[datetime | None, bool]:
    """时间戳换算到宿主当地时区。返回 (本地 naive 或 None, legacy?)。

    带时区的先 convert 到同一时区再比较（不截前十位、不裸去 tzinfo）；
    无时区的历史值按原值归属并标 legacy；不可解析返回 (None, False)。
    """
    if not ts:
        return None, False
    try:
        parsed = datetime.fromisoformat(str(ts))
    except ValueError:
        return None, False
    if parsed.tzinfo is not None:
        return parsed.astimezone().replace(tzinfo=None), False
    return parsed, True


def collect_runs(grad: Path, start: datetime, end: datetime) -> dict:
    """按时间窗收集 run：created_at 在窗内 → 新 run；否则 updated_at 在窗内 → 本期补录。

    本期创建又更新的 run 只按新 run 计一次，并保留更新时间。
    REV-09：损坏的 meta.json 不再静默跳过——计入 unreadable_entries 并降级 source_status，
    让周报能区分「证据池完整为小」与「部分条目读取失败」。
    返回 {new_runs, updated_runs, legacy_ids, source_status, unreadable_entries}。
    """
    new_runs: list[dict] = []
    updated_runs: list[dict] = []
    legacy_ids: list[str] = []
    unreadable: list[str] = []
    runs_dir = grad / "runs"
    if not runs_dir.is_dir():
        return {"new_runs": [], "updated_runs": [], "legacy_ids": [],
                "source_status": "not_present", "unreadable_entries": [],
                "reason": f"{runs_dir} 不存在：没有 run 记录这一事实可信，但不等于证据池覆盖全部工作"}
    for d in sorted(runs_dir.iterdir()):
        meta_f = d / "meta.json"
        if not d.is_dir():
            continue
        if not meta_f.is_file():
            unreadable.append(d.name)  # 有 run 目录却读不到 meta：不能假装它不存在
            continue
        try:
            meta = json.loads(meta_f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            unreadable.append(d.name)
            continue
        if not isinstance(meta, dict):
            unreadable.append(d.name)
            continue
        run_id = str(meta.get("run_id") or d.name)
        created, created_legacy = to_local(meta.get("created_at"))
        updated, updated_legacy = to_local(meta.get("updated_at"))
        row = {"run_id": run_id,
               "method": meta.get("method"), "benchmark": meta.get("benchmark"),
               "status": meta.get("status"),
               "created_at": meta.get("created_at"), "updated_at": meta.get("updated_at")}
        if created is not None and start <= created < end:
            new_runs.append(row)  # 当周创建又补录：只按新 run 计一次，updated_at 已随行带出
            if created_legacy:
                legacy_ids.append(run_id)
        elif updated is not None and start <= updated < end:
            row["result_updated"] = True
            updated_runs.append(row)  # 上周创建、本期补录结果
            if updated_legacy:
                legacy_ids.append(run_id)
        # 历史 run 没有 updated_at：不猜补录时间，也不把迁移/登记时间当结果完成时间
    return {"new_runs": new_runs, "updated_runs": updated_runs, "legacy_ids": legacy_ids,
            "source_status": "partial" if unreadable else "ok", "unreadable_entries": unreadable,
            "reason": (f"{len(unreadable)} 个 run 目录的 meta.json 读取失败：证据池不完整"
                       if unreadable else None)}


def new_claims(grad: Path, start: datetime, end: datetime) -> dict:
    """REV-09：台账缺文件 / 坏行 / 不可读分别上报，坏行不中断其余有效行。"""
    path = grad / "claims.jsonl"
    if not path.is_file():
        return {"claims": [], "legacy_ids": [], "source_status": "not_present",
                "reason": f"{path.name} 不存在：没有 claim 事件可信，但不覆盖其他记录源"}
    out: list[dict] = []
    legacy_ids: list[str] = []
    bad_lines = 0
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {"claims": [], "legacy_ids": [], "source_status": "unavailable",
                "reason": f"claims 台账读取失败：{exc}"}
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            bad_lines += 1
            continue
        if not isinstance(row, dict):
            bad_lines += 1
            continue
        # 只追加台账：带 support_at 的行是人的判定事件；否则按 recorded_at 记新增绑定
        stamp = row.get("support_at") or row.get("recorded_at")
        ts, legacy = to_local(stamp)
        if ts is None:
            bad_lines += 1
            continue
        event = "support_verdict" if row.get("support_at") else "binding"
        if start <= ts < end:
            out.append({"event": event, "claim_id": row.get("claim_id"),
                        "claim_text": str(row.get("claim_text", ""))[:60],
                        "support": row.get("support"), "recorded_at": stamp,
                        "legacy_naive": legacy or None})
            if legacy:
                legacy_ids.append(str(row.get("claim_id") or "?"))
    if bad_lines:
        return {"claims": out, "legacy_ids": legacy_ids, "source_status": "partial",
                "reason": f"claims 台账 {bad_lines} 行损坏被跳过：证据池不完整"}
    return {"claims": out, "legacy_ids": legacy_ids, "source_status": "ok", "reason": None}


def main() -> None:
    ap = argparse.ArgumentParser(description="组会承诺对账：机械提取条目与证据池（判定归人/agent 规则）")
    ap.add_argument("--prev", required=True, help="上一份周报的路径（提供待核对计划，不推导本期窗口）")
    ap.add_argument("--repo", default=".", help="项目根（git 与 .grad/ 所在）")
    ap.add_argument("--since", default="", help="本期窗口起点 YYYY-MM-DD（默认宿主当地今天−6 天）")
    ap.add_argument("--until", default="", help="本期窗口终点 YYYY-MM-DD（默认宿主当地今天）")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    prev = Path(args.prev)
    if not prev.is_file():
        die("NO_PREV", f"上一份周报不存在：{prev}；首次生成时无需对账，跳过本步即可")
    text = prev.read_text(encoding="utf-8")
    plan_items = extract_plan_items(text)
    pending_decisions = extract_pending_decisions(text)

    # 本期窗口：显式 > 默认「今天及之前 6 天」；不再从 prev 标题推导（上期窗口是旧周期）。
    today = datetime.now().astimezone()
    if args.since and args.until:
        since, until = args.since, args.until
    elif args.since:
        since, until = args.since, args.since  # 占位，下面 +6 天
    elif args.until:
        since, until = args.until, args.until
    else:
        since = (today - timedelta(days=6)).strftime("%Y-%m-%d")
        until = today.strftime("%Y-%m-%d")
    try:
        start_dt = datetime.strptime(since, "%Y-%m-%d")
        end_dt = datetime.strptime(until, "%Y-%m-%d")
    except ValueError as exc:
        die("BAD_ARGS", f"--since/--until 日期不合法：{exc}")
    if args.since and not args.until:
        until = (start_dt + timedelta(days=6)).strftime("%Y-%m-%d")
        end_dt = datetime.strptime(until, "%Y-%m-%d")
    if args.until and not args.since:
        since = (end_dt - timedelta(days=6)).strftime("%Y-%m-%d")
        start_dt = datetime.strptime(since, "%Y-%m-%d")
    if end_dt < start_dt:
        die("BAD_ARGS", f"窗口反向：until {until} 早于 since {since}；不会静默返回空证据池")
    start = start_dt
    end = end_dt + timedelta(days=1)  # 起止均含当天：按半开区间 [start 00:00, until+1 00:00) 比较

    repo = Path(args.repo).resolve()
    grad = repo / ".grad"
    runs_info = collect_runs(grad, start, end)
    claims_info = new_claims(grad, start, end)
    commits_info = git_log(repo, start, end)
    tz_offset = datetime.now().astimezone().utcoffset()
    offset_str = f"UTC{tz_offset / timedelta(hours=1):+g}" if tz_offset is not None else "UTC?"
    legacy_ids = sorted(set(runs_info["legacy_ids"]) | set(claims_info["legacy_ids"]))
    # REV-09：每个证据源单独给状态；顶层 overall 让周报消费者知道证据池是否完整
    source_status = {
        "commits": {"status": commits_info["source_status"], "reason": commits_info["reason"]},
        "runs": {"status": runs_info["source_status"], "reason": runs_info["reason"],
                 "unreadable_entries": runs_info["unreadable_entries"]},
        "claims": {"status": claims_info["source_status"], "reason": claims_info["reason"]},
    }
    statuses = {v["status"] for v in source_status.values()}
    overall = ("unavailable" if statuses <= {"unavailable", "not_present"}
               else "partial" if statuses & {"unavailable", "partial"}
               else "complete")
    data = {
        "period": {"since": since, "until": until, "timezone": offset_str},
        "prev_path": str(prev),
        "prev_date": parse_prev_date(text),
        "plan_items": plan_items,
        "pending_decisions": pending_decisions,
        "evidence": {
            "commits": commits_info["commits"],
            "new_runs": runs_info["new_runs"],
            "updated_runs": runs_info["updated_runs"],
            "new_claims": claims_info["claims"],
        },
        "evidence_status": {"per_source": source_status, "overall": overall},
        "legacy_naive_ids": legacy_ids,
        "note": ("对账规则在 weekly-brief/SKILL.md：证据必须直接覆盖承诺内容才算完成；"
                 "只覆盖承诺的一部分标「部分完成」并写明未覆盖部分；窗口内指不回证据标「未找到完成证据」；"
                 "某证据源 source_status=unavailable/not_present 时对相关条目用「无法核对」，不能推断用户没做；"
                 "overall=partial 时输出必须声明证据池不完整；"
                 "拍板问题只在有实际决定记录时标解决，不能由相关代码提交推断导师决定"),
    }
    if args.json:
        print(json.dumps({"ok": True, "data": data}, ensure_ascii=False))
        return
    e = data["evidence"]
    print(f"# 对账窗口 {since} ~ {until}（含起止当天；时区 {offset_str}"
          + (f"；legacy 无时区时间戳 {len(legacy_ids)} 个，归属不宣称精确" if legacy_ids else "") + "）")
    print(f"## 待对账计划 {len(plan_items)} 条｜拍板问题 {len(pending_decisions)} 条")
    print(f"## 证据池（overall={overall}）：commit {len(e['commits'])}｜新 run {len(e['new_runs'])}"
          f"｜补录更新 run {len(e['updated_runs'])}｜claim 变化 {len(e['new_claims'])}")
    for name, info in source_status.items():
        if info["status"] != "ok" and info["reason"]:
            print(f"  ⚠ {name}：{info['reason']}")
    for row in e["updated_runs"]:
        print(f"  ↻ {row['run_id']}（本期补录，创建于 {row['created_at']}）")


if __name__ == "__main__":
    main()
