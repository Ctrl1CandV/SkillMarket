# /// script
# requires-python = ">=3.12"
# ///
"""idea 台账（idea-ledger）。候选方向与弯路的只追加台账：半年后回看得知「当时为什么没选它」「什么被否证过」。

铁律：
- **只记录，不裁决**——某个 idea 该不该杀由人决定；脚本只做机械记录与计数
- killed 必须给非空 --reason（方法级否定）；reason 像环境性失败（OOM/依赖/限流…）时
  只警告不阻断——环境修了想法依然成立，人坚持否决请保留原话
- 防记忆投毒（ARIS capture-antipatterns 教训）：「某工具做不到 X」类断言不写入台账正文

子命令：add / update / list / stagnation（detect-only 纯计数）。
同 idea_id 最后一行为当前状态（latest-wins），JSONL 只追加不回写。

输出契约：--json 时 stdout 打印 {"ok": true, "data": {...}} 或 {"ok": false, ...}。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

STATUSES = ("candidate", "selected", "killed")

# 环境性失败信号——命中即警告「不像方法级否定」；正则是启发式，漏报不阻断
ENV_FAILURE_RE = re.compile(
    r"oom|out of memory|cuda|显存|429|rate.?limit|限流|quota|pip|conda|uv sync|装不上|安装失败|"
    r"依赖|network|dns|连不上|超时|timeout|磁盘|disk full|权限",
    re.IGNORECASE)


def die(error: str, detail: str, **extra) -> None:
    print(json.dumps({"ok": False, "error": error, "detail": detail, **extra}, ensure_ascii=False))
    sys.exit(1)


def now_local() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_rows(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows: list[dict] = []
    for no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            die("BAD_LEDGER", f"{path} 第 {no} 行不是合法 JSON：{exc}")
        if not isinstance(row, dict):
            die("BAD_LEDGER", f"{path} 第 {no} 行必须是 JSON 对象")
        rows.append(row)
    return rows


def current_rows(rows: list[dict]) -> dict[str, dict]:
    latest: dict[str, dict] = {}
    for row in rows:
        cid = row.get("idea_id")
        if isinstance(cid, str) and cid:
            latest[cid] = row
    return latest


def next_idea_id(rows: list[dict]) -> str:
    max_no = 0
    for row in rows:
        m = re.fullmatch(r"i-(\d+)", str(row.get("idea_id", "")))
        if m:
            max_no = max(max_no, int(m.group(1)))
    return f"i-{max_no + 1:03d}"


def require_grad_path(path_text: str) -> Path:
    """台账只能写在 .grad/ 下（对齐 claim_register/run_register 的目录护栏）。"""
    resolved = Path(path_text).resolve()
    if ".grad" not in resolved.parts:
        die("BAD_ARGS", f"ideas-file 必须位于项目 .grad/ 目录下：{resolved}")
    return Path(path_text)


def append_row(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def age_weeks(iso_ts: str | None, now: datetime) -> float | None:
    if not iso_ts:
        return None
    try:
        ts = datetime.fromisoformat(str(iso_ts)).replace(tzinfo=None)
    except ValueError:
        return None
    return round((now - ts).total_seconds() / (7 * 24 * 3600), 2)


def cmd_add(args: argparse.Namespace) -> None:
    text = args.text.strip()
    if not text:
        die("BAD_ARGS", "--text 不能为空")

    ledger = require_grad_path(args.ideas_file)
    rows = load_rows(ledger)

    warnings: list[str] = []
    for cid, current in current_rows(rows).items():
        if current.get("status") in ("candidate", "selected") \
                and str(current.get("text", "")).strip() == text:
            warnings.append(f"与未收敛条目 {cid} 文本相同，可能是重复登记；仍会追加")
    if re.search(r"(?i)(做不到|不支持|无法使用)\s*.{0,12}$", text[-40:]) or "not supported" in text.casefold():
        warnings.append("text 像「工具做不到 X」类能力断言（载入后续会话会自我引用）；"
                        "请改记 workaround 或要求，而非负面结论")

    idea_id = next_idea_id(rows)
    append_row(ledger, {
        "idea_id": idea_id,
        "text": text,
        "status": "candidate",
        "source": args.source.strip() or None,
        "why_not_selected": args.why_not_selected.strip() or None,
        "killed_reason": None,
        "recorded_at": now_local(),
    })
    data = {"idea_id": idea_id, "row_index": len(rows), "ideas_file": str(ledger),
            "status": "candidate", "warnings": warnings}
    if args.json:
        print(json.dumps({"ok": True, "data": data}, ensure_ascii=False))
        return
    print(f"已登记 {idea_id} → {ledger}")
    for warning in warnings:
        print(f"  ⚠ {warning}")


def cmd_update(args: argparse.Namespace) -> None:

    ledger = require_grad_path(args.ideas_file)
    rows = load_rows(ledger)
    latest = current_rows(rows)
    if args.id not in latest:
        die("NOT_FOUND", f"idea_id {args.id!r} 不存在；已知：{sorted(latest) if latest else '（无）'}")
    base = latest[args.id]

    warnings: list[str] = []
    reason = args.reason.strip() if args.reason else None
    if args.status == "killed":
        if not reason:
            die("BAD_ARGS", "--status killed 必须提供非空 --reason（方法级否定：为什么这个想法本身不成立）")
        if ENV_FAILURE_RE.search(reason):
            warnings.append(
                "理由像环境性失败（环境问题 ≠ 方法否定）：环境修了想法依然成立。"
                "坚持否决则原话保留在案；如是环境问题请改用 candidate 保留")
    transition_note = args.note.strip() or None

    timestamp = now_local()
    append_row(ledger, {
        "idea_id": args.id,
        "text": base.get("text"),
        "status": args.status,
        "source": base.get("source"),
        "why_not_selected": base.get("why_not_selected") if args.status == "killed"
                            else (args.why_not_selected.strip() or base.get("why_not_selected")),
        "killed_reason": reason,
        "note": transition_note,
        "recorded_at": timestamp,
    })
    data = {"idea_id": args.id, "status": args.status, "killed_reason": reason,
            "row_index": len(rows), "ideas_file": str(ledger), "warnings": warnings}
    if args.json:
        print(json.dumps({"ok": True, "data": data}, ensure_ascii=False))
        return
    print(f"{args.id} → {args.status}" + (f"（{reason}）" if reason else ""))
    for warning in warnings:
        print(f"  ⚠ {warning}")


def collect_current(ledger: Path, now: datetime) -> tuple[list[dict], int]:
    rows = load_rows(ledger)
    latest = current_rows(rows)
    first_pos: dict[str, int] = {}
    items: list[dict] = []
    for row in rows:
        cid = row.get("idea_id")
        if isinstance(cid, str) and cid and cid not in first_pos:
            first_pos[cid] = len(items)
    for cid, pos in sorted(first_pos.items(), key=lambda kv: kv[1]):
        row = latest[cid]
        items.append({
            "idea_id": cid,
            "text": row.get("text"),
            "status": row.get("status"),
            "source": row.get("source"),
            "why_not_selected": row.get("why_not_selected"),
            "killed_reason": row.get("killed_reason"),
            "recorded_at": row.get("recorded_at"),
            "age_weeks": age_weeks(row.get("recorded_at"), now),
        })
    return items, len(rows)


def cmd_list(args: argparse.Namespace) -> None:
    ledger = Path(args.ideas_file)
    items, n_rows = collect_current(ledger, datetime.now())
    if args.json:
        print(json.dumps({"ok": True, "data": {"items": items, "n_lines": n_rows}},
                         ensure_ascii=False))
        return
    if not items:
        print(f"# {args.ideas_file} 为空或不存在")
        return
    counts: dict[str, int] = {}
    for item in items:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    print(f"# {len(items)} 条（" + "、".join(f"{k} {v}" for k, v in sorted(counts.items())) + f"，{n_rows} 行历史）")
    for item in items:
        head = str(item["text"])[:48]
        extra = ""
        if item["status"] == "killed" and item["killed_reason"]:
            extra = f"｜理由：{item['killed_reason']}"
        elif item["why_not_selected"]:
            extra = f"｜没先选它因为：{item['why_not_selected']}"
        print(f"  {item['idea_id']:<7} [{item['status']:<9}] {head}{extra}")


def cmd_stagnation(args: argparse.Namespace) -> None:
    repo = Path(args.repo).resolve()
    grad = repo / ".grad"
    now = datetime.now()
    # 取舍：与 naive 本地时钟相减；同机同时区无误，跨时区偏移对 detect-only 计数可忽略
    window_days = args.window_weeks * 7

    items, _ = collect_current(Path(args.ideas_file), now)
    open_items = [item for item in items if item["status"] in ("candidate", "selected")]
    oldest_open_weeks = max((item["age_weeks"] or 0) for item in open_items) if open_items else None

    def days_since_latest(stamps: list[str]) -> int | None:
        parsed = []
        for stamp in stamps:
            try:
                parsed.append(datetime.fromisoformat(str(stamp)).replace(tzinfo=None))
            except ValueError:
                continue
        if not parsed:
            return None
        return max((now - ts).days for ts in [max(parsed)])

    claim_stamps: list[str] = []
    claims_path = grad / "claims.jsonl"
    if claims_path.is_file():
        for line in claims_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            for key in ("support_at", "recorded_at"):
                if row.get(key):
                    claim_stamps.append(str(row[key]))
    run_stamps: list[str] = []
    runs_dir = grad / "runs"
    for d in sorted(runs_dir.iterdir()) if runs_dir.is_dir() else []:
        meta_f = d / "meta.json"
        if not meta_f.is_file():
            continue
        try:
            meta = json.loads(meta_f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if meta.get("created_at"):
            run_stamps.append(str(meta["created_at"]))

    days_since_claims = days_since_latest(claim_stamps)
    days_since_runs = days_since_latest(run_stamps)
    stale_claims = days_since_claims is not None and days_since_claims > window_days
    stale_runs = days_since_runs is not None and days_since_runs > window_days
    stale_oldest_open = oldest_open_weeks is not None and oldest_open_weeks > args.window_weeks

    data = {
        "window_weeks": args.window_weeks,
        "open_candidates": len(open_items),
        "oldest_open_weeks": oldest_open_weeks,
        "days_since_last_claim_event": days_since_claims,
        "days_since_last_run": days_since_runs,
        "stale_claims": stale_claims,
        "stale_runs": stale_runs,
        "stale_oldest_open": stale_oldest_open,
        "any_signal": bool(stale_claims or stale_runs or stale_oldest_open),
        "note": "detect-only 纯计数：只列数字，是否换向由人裁决（Type-A 不宣判）",
    }
    if args.json:
        print(json.dumps({"ok": True, "data": data}, ensure_ascii=False))
        return
    print(f"# 停滞计数（窗口 {args.window_weeks} 周）：open={data['open_candidates']}"
          f" 最老 open {oldest_open_weeks}周｜距上次 claim {days_since_claims}天"
          f"｜距上次 run {days_since_runs}天｜信号：{'有' if data['any_signal'] else '无'}")


def main() -> None:
    ap = argparse.ArgumentParser(description="idea 台账（只记录不裁决）")
    sub = ap.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="登记候选方向")
    p_add.add_argument("--ideas-file", default=".grad/ideas.jsonl")
    p_add.add_argument("--json", action="store_true")
    p_add.add_argument("--text", required=True, help="一句话方向描述")
    p_add.add_argument("--source", default="", help="来源：arXiv id、讨论记录指针或一句话")
    p_add.add_argument("--why-not-selected", dest="why_not_selected", default="",
                       help="为什么当下没选它（排序理由显式化，半年后可复核）")
    p_add.set_defaults(func=cmd_add)

    p_upd = sub.add_parser("update", help="状态流转（追加新行）")
    p_upd.add_argument("--ideas-file", default=".grad/ideas.jsonl")
    p_upd.add_argument("--json", action="store_true")
    p_upd.add_argument("--id", required=True, help="idea_id，如 i-001")
    p_upd.add_argument("--status", required=True, choices=STATUSES)
    p_upd.add_argument("--reason", default="", help="status=killed 时必填：方法级否定理由")
    p_upd.add_argument("--why-not-selected", dest="why_not_selected", default="", help="")
    p_upd.add_argument("--note", default="", help="流转备注（如换到的方向）")
    p_upd.set_defaults(func=cmd_update)

    p_list = sub.add_parser("list", help="当前状态一览")
    p_list.add_argument("--ideas-file", default=".grad/ideas.jsonl")
    p_list.add_argument("--json", action="store_true")
    p_list.set_defaults(func=cmd_list)

    p_stag = sub.add_parser("stagnation", help="选题停滞计数（detect-only）")
    p_stag.add_argument("--ideas-file", default=".grad/ideas.jsonl")
    p_stag.add_argument("--json", action="store_true")
    p_stag.add_argument("--repo", default=".")
    p_stag.add_argument("--window-weeks", type=int, default=3)
    p_stag.set_defaults(func=cmd_stagnation)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
