# /// script
# requires-python = ">=3.12"
# ///
"""Record results for an already registered experiment run (run-provenance). Update metrics/status without creating a new run ID.

Only update: metrics, status (running/success/failed), failure_reason, and updated_at.
**Do not recollect Git state and present it as the commit from experiment time; do not change the config snapshot or seed**—preserve the original provenance.

Core rules:
- Validate every input before writing (metrics must be finite numbers; failed runs require a reason); write nothing if validation fails.
- Write through a same-directory temporary file and atomic replacement. If the second step fails, roll back the first; do not leave a partial update.
- Do not invent updated_at for historical runs that lack it. This script writes the actual time of this update.

Output contract: with --json, stdout prints {"ok": true, "data": {...}} or {"ok": false, ...}.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


def die(error: str, detail: str, **extra) -> None:
    print(json.dumps({"ok": False, "error": error, "detail": detail, **extra}, ensure_ascii=False))
    sys.exit(1)


def reject_json_constant(value: str) -> None:
    raise ValueError(f"Non-finite JSON constant is not allowed: {value}")


def parse_metrics(text: str, source: str) -> dict[str, int | float]:
    try:
        data = json.loads(text, parse_constant=reject_json_constant)
    except (json.JSONDecodeError, ValueError) as exc:
        die("BAD_METRICS", f"{source} is not valid metrics JSON: {exc}")
    if not isinstance(data, dict):
        die("BAD_METRICS", "metrics must be a JSON object mapping metric names to values")
    for key, value in data.items():
        if not isinstance(key, str) or not key.strip():
            die("BAD_METRICS", "metrics keys must be non-empty strings")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            die("BAD_METRICS", f"Metric {key!r} must be a finite number, not a bool, string, object, NaN, or Infinity")
    return data


def atomic_replace(path: Path, content: str) -> None:
    temp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        temp.write_text(content, encoding="utf-8")
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="Record results for an existing run (update metrics/status/timestamp only)")
    ap.add_argument("--run-id", required=True, help="Run ID to update (directory name)")
    ap.add_argument("--runs-dir", default=".grad/runs")
    ap.add_argument("--status", choices=("running", "success", "failed"), default="",
                    help="Status after the update; keep the existing status when omitted")
    ap.add_argument("--failure-reason", default="", help="Failure reason; required when status=failed")
    ap.add_argument("--metrics-file", default="", help="Metrics JSON file path (replaces metrics.json entirely)")
    ap.add_argument("--metrics", default="", help="Inline metrics JSON (replaces metrics.json entirely)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    runs_input = Path(args.runs_dir)
    if ".grad" not in runs_input.resolve().parts:
        die("BAD_ARGS", f"runs-dir must be under project .grad/: {runs_input.resolve()}")
    # REV-08: accept only a single valid directory name for run-id; reject absolute paths, parent traversal, and path separators.
    rid = args.run_id
    if (not rid or rid.strip() != rid or rid.startswith(".")
            or "/" in rid or "\\" in rid or re.search(r"[<>|:*?\x00]", rid)):
        die("BAD_ARGS", f"run-id must be one valid directory name (no path separators, absolute paths, or parent traversal): {rid!r}")
    runs_resolved = runs_input.resolve()
    run_dir = (runs_resolved / rid)
    if not run_dir.resolve().is_relative_to(runs_resolved):
        die("BAD_ARGS", f"Resolved run-id escapes the runs root directory: {rid!r}; refusing to write")
    if args.status == "failed" and not args.failure_reason.strip():
        die("BAD_ARGS", "A non-empty --failure-reason is required when status=failed")
    if args.status and args.status != "failed" and args.failure_reason.strip():
        die("BAD_ARGS", "failure-reason can only be used with a failed run")
    if args.metrics_file and args.metrics:
        die("BAD_ARGS", "Specify only one of --metrics and --metrics-file")

    metrics: dict[str, int | float] | None = None
    if args.metrics_file:
        metrics_file = Path(args.metrics_file)
        if not metrics_file.is_file():
            die("BAD_METRICS", f"Metrics file not found: {metrics_file}")
        try:
            metrics_text = metrics_file.read_text(encoding="utf-8")
        except OSError as exc:
            die("BAD_METRICS", f"Could not read metrics file: {exc}")
        metrics = parse_metrics(metrics_text, "metrics file")
    elif args.metrics:
        metrics = parse_metrics(args.metrics, "--metrics")

    meta_f = run_dir / "meta.json"
    if not run_dir.is_dir() or not meta_f.is_file():
        die("NOT_FOUND", f"Run not found: {run_dir}; updates apply only to registered runs (use run_register.py for a new run)")
    try:
        meta = json.loads(meta_f.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        die("BAD_RUN_DATA", f"Could not parse {meta_f}; refusing to update corrupted data: {exc}")
    if not isinstance(meta, dict):
        die("BAD_RUN_DATA", f"{meta_f} must be a JSON object")

    old_meta_text = meta_f.read_text(encoding="utf-8")
    metrics_f = run_dir / "metrics.json"
    old_metrics_text = metrics_f.read_text(encoding="utf-8") if metrics_f.is_file() else None

    # REV-07: apply status and failure-reason rules to the final data that will be written:
    # an update without --status leaves status and reason unchanged; an explicit transition to failed requires a valid reason (and may update it);
    # an explicit transition away from failed clears the old reason.
    new_status = args.status or str(meta.get("status") or "success")
    meta["status"] = new_status
    if args.status == "failed":
        meta["failure_reason"] = args.failure_reason.strip()
    elif args.status and args.status != "failed":
        meta["failure_reason"] = None
    # If args.status is empty, retain both status and failure_reason.
    if str(meta.get("status")) == "failed" and not str(meta.get("failure_reason") or "").strip():
        die("BAD_ARGS", "The final status is failed but no valid failure reason is available; "
                        "pass --failure-reason or choose the correct status. Refusing to write a partial record.")
    meta["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    warnings: list[str] = []
    if metrics is not None and new_status == "success" and not metrics:
        warnings.append("Metrics were updated to an empty object while status is success; a run with no results should not be marked successful. Keep it running or mark it failed accurately.")
    if metrics is None and args.status == "success":
        warnings.append("Status changed to success without metrics; this run still has no checkable numeric results.")

    # Write meta first, then metrics; roll back the first write if the second fails (single-writer sequence, not a power-loss-safe transaction).
    try:
        atomic_replace(meta_f, json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
        if metrics is not None:
            atomic_replace(metrics_f, json.dumps(metrics, ensure_ascii=False, indent=2) + "\n")
    except OSError as exc:
        try:
            atomic_replace(meta_f, old_meta_text)
            if old_metrics_text is not None:
                atomic_replace(metrics_f, old_metrics_text)
            elif metrics_f.is_file():
                metrics_f.unlink()  # There was no metrics.json before; remove the incomplete file created by this update.
            rollback = "Rolled back to the pre-update contents"
        except OSError as rollback_exc:
            rollback = f"Rollback also failed ({rollback_exc}); use the original meta text in the error to restore it manually"
        die("WRITE_FAILED", f"Update did not complete: {exc}; {rollback}. The operation is not reported as successful.")

    data = {"run_id": args.run_id, "meta": meta,
            "metrics": metrics if metrics is not None else "(unchanged)",
            "warnings": warnings,
            "note": "Update changes metrics/status/updated_at only; created_at, Git commit, and config snapshot remain unchanged"}
    if args.json:
        print(json.dumps({"ok": True, "data": data}, ensure_ascii=False))
        return
    print("Updated run {}: status={} | updated_at={}".format(args.run_id, new_status, meta["updated_at"]))
    if metrics is not None:
        print(f"  metrics → {json.dumps(metrics, ensure_ascii=False)}")
    for w in warnings:
        print(f"  ⚠ {w}")


if __name__ == "__main__":
    main()
