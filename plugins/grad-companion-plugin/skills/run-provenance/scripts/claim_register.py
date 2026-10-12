# /// script
# requires-python = ">=3.12"
# ///
"""Register claims in run-provenance. Write guardrails for the evidence/support axes.

add      Register a claim bound to a run and metric key; claim_id is assigned automatically and support starts as unreviewed.
support  Record a human verdict (supported/partial/refuted) by appending a row; the latest row for a claim_id is current.

Core rules: JSONL is append-only and never rewritten. add has no --support option (human verdicts can only be recorded with the support subcommand,
and --by must be explicitly supplied by the user; the agent must not fill it in). Never guess; mark missing information null.

Output contract: with --json, stdout prints {"ok": true, "data": {...}} or {"ok": false, ...}.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_grouping import same_setting_runs  # Share comparability rules with table_gen and claim_check.

if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


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


def next_claim_id(rows: list[dict]) -> str:
    max_no = 0
    for row in rows:
        m = re.fullmatch(r"c-(\d+)", str(row.get("claim_id", "")))
        if m:
            max_no = max(max_no, int(m.group(1)))
    return f"c-{max_no + 1:03d}"


def current_rows(rows: list[dict]) -> dict[str, dict]:
    """The latest row for a claim_id is its current state (the ledger is append-only, so parsing determines the current row)."""
    latest: dict[str, dict] = {}
    for row in rows:
        cid = row.get("claim_id")
        if isinstance(cid, str) and cid:
            latest[cid] = row
    return latest


def append_row(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def require_grad_path(path_text: str) -> Path:
    """The ledger may only be written under .grad/ (matching run_register runs-dir guardrails; writes must stay in project state)."""
    resolved = Path(path_text).resolve()
    if ".grad" not in resolved.parts:
        die("BAD_ARGS", f"claims-file must be inside the project .grad/ directory: {resolved}")
    return Path(path_text)


def cmd_add(args: argparse.Namespace) -> None:
    claim = args.claim.strip()
    runs = [r.strip() for r in args.runs.split(",") if r.strip()]
    metric = args.metric.strip()
    if not claim:
        die("BAD_ARGS", "--claim must not be empty")
    if not runs:
        die("BAD_ARGS", "--runs must include at least one run ID")
    if not metric:
        die("BAD_ARGS", "--metric must not be empty")

    claims_path = require_grad_path(args.claims_file)
    rows = load_rows(claims_path)

    warnings: list[str] = []
    runs_dir = Path(args.runs_dir)
    fields_seen: dict[str, set[str]] = {"method": set(), "benchmark": set()}
    settings_seen: list[dict] = []
    for rid in runs:
        run_dir = runs_dir / rid
        meta_f = run_dir / "meta.json"
        if not run_dir.is_dir():
            warnings.append(f"Run {rid} was not found under {runs_dir}; ignore this if it will be registered later, as claim_check will recheck it.")
            continue
        if not meta_f.is_file():
            continue
        try:
            meta = json.loads(meta_f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            warnings.append(f"Could not parse meta.json for run {rid}; skipping the comparability check.")
            continue
        if isinstance(meta, dict):
            for field in ("method", "benchmark"):
                value = meta.get(field)
                if isinstance(value, str) and value:
                    fields_seen[field].add(value)
            settings_seen.append({
                "run_id": rid,
                "method": meta.get("method"),
                "benchmark": meta.get("benchmark"),
                "experiment_group": meta.get("experiment_group"),
                "config": meta.get("config") if isinstance(meta.get("config"), dict) else None,
            })
    for field, values in fields_seen.items():
        if len(values) > 1:
            warnings.append(f"Bound runs use mixed {field} values: {sorted(values)} (they would be averaged; please confirm).")
    if settings_seen and len(same_setting_runs(settings_seen)) > 1:
        warnings.append(
            "Bound runs use different comparison settings (method/benchmark or config snapshot mismatch/missing config), so claim_check will not report a verified mean; "
            "if they are the same experiment, declare that explicitly with run_register.py --experiment-group")
        )

    binding = (claim, tuple(sorted(runs)), metric)
    for row in rows:
        existing = (str(row.get("claim_text", "")),
                    tuple(sorted(str(r) for r in (row.get("run_ids") or []))),
                    str(row.get("metric_path", "")))
        if existing == binding:
            warnings.append(
                "Binding exactly matches existing entry {}; this may be a duplicate. The new row will still be appended without silent merging.".format(row.get("claim_id", "legacy"))
            )

    claim_id = next_claim_id(rows)
    row_index = len(rows)  # Zero-based position of the new row in the parsed sequence.
    append_row(claims_path, {
        "claim_id": claim_id,
        "claim_text": claim,
        "run_ids": runs,
        "metric_path": metric,
        "support": "unreviewed",
        "support_by": None,
        "support_at": None,
        "recorded_at": now_local(),
    })
    data = {"claim_id": claim_id, "row_index": row_index, "claims_file": str(claims_path),
            "support": "unreviewed", "warnings": warnings}
    if args.json:
        print(json.dumps({"ok": True, "data": data}, ensure_ascii=False))
        return
    print(f"Recorded {claim_id} → {claims_path} (support=unreviewed; human verdicts can only be written with the support subcommand)")
    for warning in warnings:
        print(f"  ⚠ {warning}")


def cmd_support(args: argparse.Namespace) -> None:
    by = args.by.strip()
    if not by:
        die("BAD_ARGS", "--by must not be empty; record only a verdict explicitly provided by the user (the agent must not fill it in)")
    claims_path = require_grad_path(args.claims_file)
    rows = load_rows(claims_path)
    latest = current_rows(rows)
    if args.id not in latest:
        die("NOT_FOUND", "claim_id {} not found; known IDs: {}".format(args.id, sorted(latest) if latest else "(none)"))
    base = latest[args.id]
    timestamp = now_local()
    append_row(claims_path, {
        "claim_id": args.id,
        "claim_text": base.get("claim_text"),
        "run_ids": base.get("run_ids") or [],
        "metric_path": base.get("metric_path"),
        "support": args.verdict,
        "support_by": by,
        "support_at": timestamp,
        "recorded_at": timestamp,
    })
    data = {"claim_id": args.id, "row_index": len(rows), "support": args.verdict,
            "support_by": by, "claims_file": str(claims_path)}
    if args.json:
        print(json.dumps({"ok": True, "data": data}, ensure_ascii=False))
        return
    print(f"Recorded verdict for {args.id} → {args.verdict} (by {by})")


def main() -> None:
    ap = argparse.ArgumentParser(description="Register claims (append-only; support verdicts require a human-supplied --by)")
    sub = ap.add_subparsers(dest="command", required=True)

    ap_add = sub.add_parser("add", help="Register a claim (bind it to runs and a metric key)")
    ap_add.add_argument("--claim", required=True, help="Claim text as written in the paper; preserve its numeric wording")
    ap_add.add_argument("--runs", required=True, help="Comma-separated run IDs; bind every seed and do not select the best one")
    ap_add.add_argument("--metric", required=True, help="Metric key, e.g. resolved_rate")
    ap_add.add_argument("--claims-file", default=".grad/claims.jsonl")
    ap_add.add_argument("--runs-dir", default=".grad/runs", help="Used only for existence and comparability warnings; does not block registration")
    ap_add.add_argument("--json", action="store_true")

    ap_sup = sub.add_parser("support", help="Record a human verdict (append a row; latest row for an ID is current)")
    ap_sup.add_argument("--id", required=True, help="claim_id, e.g. c-001")
    ap_sup.add_argument("--verdict", required=True, choices=("supported", "partial", "refuted"))
    ap_sup.add_argument("--by", required=True, help="Who made the verdict; must be explicitly provided by the user, never filled in by the agent")
    ap_sup.add_argument("--claims-file", default=".grad/claims.jsonl")
    ap_sup.add_argument("--json", action="store_true")

    args = ap.parse_args()
    if args.command == "add":
        cmd_add(args)
    else:
        cmd_support(args)


if __name__ == "__main__":
    main()
