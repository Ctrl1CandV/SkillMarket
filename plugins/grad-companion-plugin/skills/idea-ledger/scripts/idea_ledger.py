# /// script
# requires-python = ">=3.12"
# ///
"""idea-ledger. An append-only record of candidate directions and dead ends, so you can later see why an idea was not chosen or what was disproved.

Core rules:
- **Record, do not decide**: people decide whether an idea should be killed; the script only records and counts.
- A killed idea requires a non-empty --reason (a method-level rejection). If the reason looks like an environmental failure (OOM, dependencies, rate limits, etc.),
  warn without blocking: fixing the environment may leave the idea viable. Preserve the users exact wording when they insist on rejecting it.
- Prevent memory poisoning (lesson from ARIS capture-antipatterns): do not store claims such as "a tool cannot do X" in the ledger body.

Subcommands: add / update / list / stagnation (detect-only counts).
The latest row for an idea_id is its current state (latest-wins); JSONL is append-only and is never rewritten.

Output contract: with --json, stdout prints {"ok": true, "data": {...}} or {"ok": false, ...}.
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

# Signals of environmental failure trigger a warning that the reason may not reject the method; this heuristic never blocks on a miss.
ENV_FAILURE_RE = re.compile(
    r"oom|out of memory|cuda|graphics memory|显存|429|rate.?limit|限流|quota|pip|conda|uv sync|cannot install|installation failed|装不上|安装失败|"
    r"dependencies|依赖|network|dns|connection failed|连不上|超时|timeout|disk full|磁盘|permission denied|权限",
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
            die("BAD_LEDGER", f"{path} line {no} is not valid JSON: {exc}")
        if not isinstance(row, dict):
            die("BAD_LEDGER", f"{path} line {no} must be a JSON object")
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
    """The ledger may only be written under .grad/ (matching the directory guard in claim_register/run_register)."""
    resolved = Path(path_text).resolve()
    if ".grad" not in resolved.parts:
        die("BAD_ARGS", f"ideas-file must be inside the project .grad/ directory: {resolved}")
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
        die("BAD_ARGS", "--text must not be empty")

    ledger = require_grad_path(args.ideas_file)
    rows = load_rows(ledger)

    warnings: list[str] = []
    for cid, current in current_rows(rows).items():
        if current.get("status") in ("candidate", "selected") \
                and str(current.get("text", "")).strip() == text:
            warnings.append(f"Text matches unresolved entry {cid}; this may be a duplicate. The new row will still be appended.")
    if re.search(r"(?i)(cannot do|does not support|cannot use|does not work|做不到|不支持|无法使用)\s*.{0,12}$", text[-40:]) or "not supported" in text.casefold():
        warnings.append("Text looks like a capability claim such as \"a tool cannot do X\" (later sessions may repeat it as fact); "
                        "record a workaround or requirement instead of a negative conclusion.")

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
    print(f"Recorded {idea_id} → {ledger}")
    for warning in warnings:
        print(f"  ⚠ {warning}")


def cmd_update(args: argparse.Namespace) -> None:

    ledger = require_grad_path(args.ideas_file)
    rows = load_rows(ledger)
    latest = current_rows(rows)
    if args.id not in latest:
        die("NOT_FOUND", "idea_id {} not found; known IDs: {}".format(args.id, sorted(latest) if latest else "(none)"))
    base = latest[args.id]

    warnings: list[str] = []
    reason = args.reason.strip() if args.reason else None
    if args.status == "killed":
        if not reason:
            die("BAD_ARGS", "--status killed requires a non-empty --reason (explain why the idea itself is invalid as a method)")
        if ENV_FAILURE_RE.search(reason):
            warnings.append(
                "The reason looks like an environmental failure, not a method rejection: fixing the environment may leave the idea viable. "
                "If you still reject it, preserve that wording; if the issue is environmental, keep the idea as a candidate.")
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
        print(f"# {args.ideas_file} is empty or does not exist")
        return
    counts: dict[str, int] = {}
    for item in items:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    print("# {} items (".format(len(items)) + ", ".join("{} {}".format(k, v) for k, v in sorted(counts.items())) + ", {} historical rows)".format(n_rows))
    for item in items:
        head = str(item["text"])[:48]
        extra = ""
        if item["status"] == "killed" and item["killed_reason"]:
            extra = " | Reason: {}".format(item["killed_reason"])
        elif item["why_not_selected"]:
            extra = " | Not selected because: {}".format(item["why_not_selected"])
        print(f"  {item['idea_id']:<7} [{item['status']:<9}] {head}{extra}")


def cmd_stagnation(args: argparse.Namespace) -> None:
    repo = Path(args.repo).resolve()
    grad = repo / ".grad"
    now = datetime.now()
    # Tradeoff: subtract from the local naive clock; same-machine timezone offsets cancel, and cross-zone error is negligible for detect-only counts.
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
        "note": "Detect-only count: reports numbers only; a person decides whether to change direction (Type-A does not judge).",
    }
    if args.json:
        print(json.dumps({"ok": True, "data": data}, ensure_ascii=False))
        return
    print("# Stagnation count (window {} weeks): open={}, oldest open {} weeks | {} days since last claim | {} days since last run | signal: {}".format(args.window_weeks, data["open_candidates"], oldest_open_weeks, days_since_claims, days_since_runs, "yes" if data["any_signal"] else "no"))




def main() -> None:
    ap = argparse.ArgumentParser(description="idea-ledger (records only; does not decide)")
    sub = ap.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="Record a candidate direction")
    p_add.add_argument("--ideas-file", default=".grad/ideas.jsonl")
    p_add.add_argument("--json", action="store_true")
    p_add.add_argument("--text", required=True, help="One-sentence description of the direction")
    p_add.add_argument("--source", default="", help="Source: arXiv ID, discussion reference, or a short note")
    p_add.add_argument("--why-not-selected", dest="why_not_selected", default="",
                       help="Why it was not selected now (make the ranking rationale explicit for later review)")
    p_add.set_defaults(func=cmd_add)

    p_upd = sub.add_parser("update", help="Change status (append a new row)")
    p_upd.add_argument("--ideas-file", default=".grad/ideas.jsonl")
    p_upd.add_argument("--json", action="store_true")
    p_upd.add_argument("--id", required=True, help="idea_id, e.g. i-001")
    p_upd.add_argument("--status", required=True, choices=STATUSES)
    p_upd.add_argument("--reason", default="", help="Required when status=killed: method-level rejection reason")
    p_upd.add_argument("--why-not-selected", dest="why_not_selected", default="", help="")
    p_upd.add_argument("--note", default="", help="Transition note (for example, the new direction)")
    p_upd.set_defaults(func=cmd_update)

    p_list = sub.add_parser("list", help="Show current states")
    p_list.add_argument("--ideas-file", default=".grad/ideas.jsonl")
    p_list.add_argument("--json", action="store_true")
    p_list.set_defaults(func=cmd_list)

    p_stag = sub.add_parser("stagnation", help="Count topic stagnation (detect-only)")
    p_stag.add_argument("--ideas-file", default=".grad/ideas.jsonl")
    p_stag.add_argument("--json", action="store_true")
    p_stag.add_argument("--repo", default=".")
    p_stag.add_argument("--window-weeks", type=int, default=3)
    p_stag.set_defaults(func=cmd_stagnation)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
