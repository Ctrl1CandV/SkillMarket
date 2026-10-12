# /// script
# requires-python = ">=3.12"
# ///
"""Lab-meeting commitment reconciliation (weekly-brief). Extract prior-brief plan items and the current evidence pool for mechanical review.

Division of responsibility (Type-A / Type-B):
- This script performs **mechanical extraction only**: items to reconcile, evidence pool (commits/new or updated runs/claim changes), and window calculation.
- The agent decides whether an item was fulfilled under SKILL.md: **evidence must directly cover the commitment; partial coverage is partial; no evidence means no completion evidence found; unreadable sources mean unverifiable, not proof that it was not done.** The script does not adjudicate.

Reporting window (F03): the generator supplies the current window explicitly; if omitted, the CLI defaults to the host's local today and previous six days.
The previous brief provides plans and questions to check; **the current window is no longer derived from its heading**.
--since/--until include both dates (half-open interval from start-day 00:00 through the day after end-day 00:00).
If only one side is supplied, the other is six days away. Convert timezone-aware timestamps to host-local time before comparing.
Mark historical timestamps without timezones as legacy; do not claim precise timezone attribution.
Evidence sources: git log; .grad/runs/ (new_runs by created_at, updated_runs by updated_at); new rows in claims.jsonl (including support decisions).

With --json, stdout prints {"ok": true, "data": {...}} or {"ok": false, ...}.
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
    """Brief heading format: `# Weekly Report · YYYY-MM-DD ~ YYYY-MM-DD` or frontmatter date."""
    m = re.search(r"#\s*Weekly Report\s*·\s*(\d{4}-\d{2}-\d{2})", text, re.I)
    if m:
        return m.group(1)
    m = re.match(r"^---\n.*?^date:\s*(\d{4}-\d{2}-\d{2})", text, re.S | re.M)
    return m.group(1) if m else None


def extract_plan_items(text: str) -> list[str]:
    """Extract top-level bullets from the “Plan for next week” section; return an empty list if absent."""
    m = re.search(r"^#+\s*[^#\n]*Plan for next week[^\n]*\n(.*?)(?=^#{1,3}\s|\Z)", text, re.S | re.M | re.I)
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
    """Extract items from the advisor-decision section; return an empty list if absent."""
    m = re.search(r"^#+\s*[^#\n]*Questions requiring the advisor's decision[^\n]*\n(.*?)(?=^#{1,3}\s|\Z)",
                  text, re.S | re.M | re.I)
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
    """REV-09: distinguish unreadable sources from genuinely empty ones; include a reason when unavailable."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "log", "--since", start.isoformat(),
             "--until", end.isoformat(),
             "--pretty=format:%h%x00%ad%x00%s", "--date=short"],
            capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as exc:
        return {"commits": [], "source_status": "unavailable",
                "reason": f"git exited with {exc.returncode} (not a Git directory or history missing); evidence pool unavailable, not empty"}
    except OSError as exc:
        return {"commits": [], "source_status": "unavailable",
                "reason": f"git could not run: {exc}; evidence pool unavailable, not empty"}
    commits = []
    for line in proc.stdout.splitlines():
        parts = line.split("\x00")
        if len(parts) == 3 and parts[0].strip():
            commits.append({"hash": parts[0], "date": parts[1], "subject": parts[2]})
    return {"commits": commits, "source_status": "ok", "reason": None}


def to_local(ts: str | None) -> tuple[datetime | None, bool]:
    """Convert timestamps to the host's local timezone; return (local naive datetime or None, legacy?).

    Convert timezone-aware values before comparison (do not truncate to ten characters or strip tzinfo);
    keep timezone-naive historical values and mark them legacy; invalid input returns (None, False).
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
    """Collect runs by window: created_at in range -> new run; otherwise updated_at in range -> result update this period.

    A run created and updated this period counts once as new and retains its update time.
    REV-09: do not silently skip a corrupt meta.json; include it in unreadable_entries and downgrade source_status
    so the report can distinguish a complete but small evidence pool from partial read failure.
    Return {new_runs, updated_runs, legacy_ids, source_status, unreadable_entries}.
    """
    new_runs: list[dict] = []
    updated_runs: list[dict] = []
    legacy_ids: list[str] = []
    unreadable: list[str] = []
    runs_dir = grad / "runs"
    if not runs_dir.is_dir():
        return {"new_runs": [], "updated_runs": [], "legacy_ids": [],
                "source_status": "not_present", "unreadable_entries": [],
                "reason": f"{runs_dir} does not exist: no run records is a reliable fact, but does not mean the evidence pool covers all work"}
    for d in sorted(runs_dir.iterdir()):
        meta_f = d / "meta.json"
        if not d.is_dir():
            continue
        if not meta_f.is_file():
            unreadable.append(d.name)  # A run directory exists but its meta is unreadable; do not pretend it is absent.
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
            new_runs.append(row)  # Created and updated this week: count once as new; updated_at remains in the row.
            if created_legacy:
                legacy_ids.append(run_id)
        elif updated is not None and start <= updated < end:
            row["result_updated"] = True
            updated_runs.append(row)  # Created earlier; results appended this period.
            if updated_legacy:
                legacy_ids.append(run_id)
        # If an old run lacks updated_at, do not guess when results were added or use migration/registration time.
    return {"new_runs": new_runs, "updated_runs": updated_runs, "legacy_ids": legacy_ids,
            "source_status": "partial" if unreadable else "ok", "unreadable_entries": unreadable,
            "reason": (f"Could not read meta.json in {len(unreadable)} run directories; evidence pool is incomplete"
                       if unreadable else None)}


def new_claims(grad: Path, start: datetime, end: datetime) -> dict:
    """REV-09: report missing files, malformed rows, and unreadable files separately; bad rows do not stop valid rows."""
    path = grad / "claims.jsonl"
    if not path.is_file():
        return {"claims": [], "legacy_ids": [], "source_status": "not_present",
                "reason": f"{path.name} does not exist: no claim events is reliable, but other evidence sources remain"}
    out: list[dict] = []
    legacy_ids: list[str] = []
    bad_lines = 0
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {"claims": [], "legacy_ids": [], "source_status": "unavailable",
                "reason": f"Could not read claims ledger: {exc}"}
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
        # Append-only ledger: support_at marks a human judgment; otherwise recorded_at marks a new binding.
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
                "reason": f"Skipped {bad_lines} malformed row(s) in claims ledger; evidence pool is incomplete"}
    return {"claims": out, "legacy_ids": legacy_ids, "source_status": "ok", "reason": None}


def main() -> None:
    ap = argparse.ArgumentParser(description="Reconcile lab commitments: mechanically extract prior items and current evidence")
    ap.add_argument("--prev", required=True, help="Path to previous weekly report (provides plans to check, not the current window)")
    ap.add_argument("--repo", default=".", help="Project root (contains Git repository and .grad/)")
    ap.add_argument("--since", default="", help="Current window start YYYY-MM-DD (default: host-local today minus six days)")
    ap.add_argument("--until", default="", help="Current window end YYYY-MM-DD (default: host-local today)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    prev = Path(args.prev)
    if not prev.is_file():
        die("NO_PREV", f"Previous weekly report does not exist: {prev}; skip reconciliation when creating the first report")
    text = prev.read_text(encoding="utf-8")
    plan_items = extract_plan_items(text)
    pending_decisions = extract_pending_decisions(text)

    # Current window: explicit arguments > default (today and previous six days); never derive it from the prior heading.
    today = datetime.now().astimezone()
    if args.since and args.until:
        since, until = args.since, args.until
    elif args.since:
        since, until = args.since, args.since  # Placeholder; add six days below.
    elif args.until:
        since, until = args.until, args.until
    else:
        since = (today - timedelta(days=6)).strftime("%Y-%m-%d")
        until = today.strftime("%Y-%m-%d")
    try:
        start_dt = datetime.strptime(since, "%Y-%m-%d")
        end_dt = datetime.strptime(until, "%Y-%m-%d")
    except ValueError as exc:
        die("BAD_ARGS", f"Invalid --since/--until date: {exc}")
    if args.since and not args.until:
        until = (start_dt + timedelta(days=6)).strftime("%Y-%m-%d")
        end_dt = datetime.strptime(until, "%Y-%m-%d")
    if args.until and not args.since:
        since = (end_dt - timedelta(days=6)).strftime("%Y-%m-%d")
        start_dt = datetime.strptime(since, "%Y-%m-%d")
    if end_dt < start_dt:
        die("BAD_ARGS", f"Reversed window: until {until} is earlier than since {since}; refusing to return a silently empty evidence pool")
    start = start_dt
    end = end_dt + timedelta(days=1)  # Both dates inclusive; compare using [start 00:00, until+1 00:00).

    repo = Path(args.repo).resolve()
    grad = repo / ".grad"
    runs_info = collect_runs(grad, start, end)
    claims_info = new_claims(grad, start, end)
    commits_info = git_log(repo, start, end)
    tz_offset = datetime.now().astimezone().utcoffset()
    offset_str = f"UTC{tz_offset / timedelta(hours=1):+g}" if tz_offset is not None else "UTC?"
    legacy_ids = sorted(set(runs_info["legacy_ids"]) | set(claims_info["legacy_ids"]))
    # REV-09: report each source status separately; top-level overall tells the report whether evidence is complete.
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
        "note": ("Reconciliation rules are in weekly-brief/SKILL.md: evidence must directly cover the commitment to count as complete; "
                 "mark partial coverage and state what remains; if no evidence points to an item in this window, say no completion evidence was found; "
                 "when source_status=unavailable/not_present, mark affected items unverifiable and do not infer that the user did nothing; "
                 "when overall=partial, state that the evidence pool is incomplete; "
                 "mark advisor questions resolved only with an actual decision record, never infer an advisor decision from a related code commit."),
    }
    if args.json:
        print(json.dumps({"ok": True, "data": data}, ensure_ascii=False))
        return
    e = data["evidence"]
    print(f"# Reconciliation window {since} ~ {until} (inclusive; timezone {offset_str}"
          + (f"; {len(legacy_ids)} legacy timezone-naive timestamps with imprecise attribution" if legacy_ids else "") + ")")
    print(f"## Plans to reconcile: {len(plan_items)} | Pending advisor decisions: {len(pending_decisions)}")
    print(f"## Evidence pool (overall={overall}): commits {len(e['commits'])} | new runs {len(e['new_runs'])}"
          f" | updated runs {len(e['updated_runs'])} | claim changes {len(e['new_claims'])}")
    for name, info in source_status.items():
        if info["status"] != "ok" and info["reason"]:
            print(f"  ⚠ {name}：{info['reason']}")
    for row in e["updated_runs"]:
        print(f"  ↻ {row['run_id']} (results added this period; created {row['created_at']})")


if __name__ == "__main__":
    main()
