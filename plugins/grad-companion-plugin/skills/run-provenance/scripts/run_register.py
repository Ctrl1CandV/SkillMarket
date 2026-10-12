# /// script
# requires-python = ">=3.12"
# ///
"""Register an experiment run (run-provenance). Read and record metadata only: do not start training, change hyperparameters, or delete files.

What it does: create a run ID, collect Git state, snapshot config, record metrics/seed/hardware, and write .grad/runs/<run-id>/meta.json and metrics.json.

Core rule: never guess. If the user gives no seed, write null and warn; if the directory is not a Git repository, record unknown;
if the config path does not exist, record null. Always mark missing information unknown/null instead of inventing values.

Reproducibility is recorded, not proven: new records use reproducibility_status=not_verified. Complete seed and clean
commit metadata only means the information was recorded; no rerun verification was performed (rerun verification is outside this skill scope).
Use --status running for a placeholder run that has started but has no results; record its results later with run_update.py.

Output contract: with --json, stdout prints {"ok": true, "data": {...}} or {"ok": false, ...}.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_grouping import reproducibility_info  # Shared helper for grouping and reproducibility metadata within this skill.

if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


def die(error: str, detail: str, **extra) -> None:
    print(json.dumps({"ok": False, "error": error, "detail": detail, **extra}, ensure_ascii=False))
    sys.exit(1)


def git_info(cwd: Path) -> dict:
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                           cwd=str(cwd), timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return {"commit": None, "dirty": None, "dirty_files": 0,
                "note": "Git is unavailable; commit recorded as unknown"}
    if r.returncode != 0:
        return {"commit": None, "dirty": None, "dirty_files": 0,
                "note": "Not a Git repository; commit recorded as unknown"}
    commit = r.stdout.strip()
    s = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True,
                       cwd=str(cwd), timeout=15)
    dirty_lines = [l for l in (s.stdout or "").splitlines() if l.strip()]
    return {"commit": commit, "dirty": bool(dirty_lines), "dirty_files": len(dirty_lines)}


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


def main() -> None:
    ap = argparse.ArgumentParser(description="Register an experiment run (read and record only)")
    ap.add_argument("--method", required=True, help="Method name (tables group by method × benchmark)")
    ap.add_argument("--benchmark", required=True, help="Benchmark or dataset name")
    ap.add_argument("--seed", type=int, default=None, help="Random seed; record null and warn about reproducibility if omitted")
    ap.add_argument("--status", choices=("success", "failed", "running"), default="success",
                    help="Run status; register failed runs too. Use running as a placeholder when results are not ready, then update with run_update.py")
    ap.add_argument("--failure-reason", default="", help="Failure reason; required when status=failed")
    ap.add_argument("--experiment-group", default="",
                    help="Optional experiment group; set only when the user confirms these runs share comparison settings (the agent must not guess)")
    ap.add_argument("--cmd", default="", help="Command line actually executed")
    ap.add_argument("--hardware", default="", help="Hardware description, e.g. A100 x8")
    ap.add_argument("--cost", default="", help="Cost record (tokens, money, duration; free text)")
    ap.add_argument("--label", default="", help="Human-readable note")
    ap.add_argument("--config", default="", help="Config file path (a snapshot is copied into the run directory)")
    ap.add_argument("--metrics-file", default="", help="Path to a metrics JSON file")
    ap.add_argument("--metrics", default="", help="Inline metrics JSON string, e.g. {\"acc\": 0.712}")
    ap.add_argument("--runs-dir", default=".grad/runs")
    ap.add_argument("--repo", default=".", help="Git repository directory (default: current directory)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.status == "failed" and not args.failure_reason.strip():
        die("BAD_ARGS", "A non-empty --failure-reason is required when status=failed")
    if args.status != "failed" and args.failure_reason.strip():
        die("BAD_ARGS", "failure-reason can only be used with a failed run")

    warnings: list[str] = []
    repo = Path(args.repo).resolve()
    grad_root = (repo / ".grad").resolve()
    runs_input = Path(args.runs_dir)
    runs_dir = (runs_input if runs_input.is_absolute() else repo / runs_input).resolve()
    if runs_dir == grad_root or not runs_dir.is_relative_to(grad_root):
        die("BAD_ARGS", f"runs-dir must be inside a subdirectory of project .grad/: {grad_root}")

    # Validate all inputs before creating any run directory.
    metrics: dict[str, int | float] = {}
    if args.metrics_file:
        metrics_file = Path(args.metrics_file)
        if not metrics_file.is_file():
            warnings.append(f"Metrics file not found: {metrics_file}; metrics will be empty.")
        else:
            try:
                metrics_text = metrics_file.read_text(encoding="utf-8")
            except OSError as exc:
                die("BAD_METRICS", f"Could not read metrics file: {exc}")
            metrics = parse_metrics(metrics_text, "metrics file")
    elif args.metrics:
        metrics = parse_metrics(args.metrics, "--metrics")
    else:
        warnings.append("No metrics supplied; metrics.json will be empty (you can add them after the run finishes).")

    config_record = None
    config_bytes: bytes | None = None
    if args.config:
        config_source = Path(args.config)
        if not config_source.is_file():
            config_record = {"path": str(config_source), "snapshot": None, "sha256": None}
            warnings.append(f"Config file not found: {config_source}; recording null.")
        else:
            try:
                config_bytes = config_source.read_bytes()
            except OSError as exc:
                die("CONFIG_READ_FAILED", f"Could not read config: {exc}")
            snapshot_name = "config_snapshot" + config_source.suffix
            config_record = {
                "path": str(config_source),
                "snapshot": snapshot_name,
                "sha256": hashlib.sha256(config_bytes).hexdigest(),
            }

    git = git_info(Path(args.repo))
    if git["commit"] is None:
        warnings.append(git.get("note", "commit unknown"))
    if git["dirty"]:
        warnings.append("Working tree is dirty ({} uncommitted files); the commit alone cannot identify the code used for this run.".format(git["dirty_files"]))
    if args.seed is None:
        warnings.append("No seed recorded; reproducibility metadata is incomplete.")

    run_id = datetime.now().strftime("run-%Y%m%d-%H%M%S-") + f"{random.randrange(0x10000):04x}"
    run_dir = runs_dir / run_id
    temp_dir = runs_dir / f".{run_id}.tmp"
    if run_dir.exists() or temp_dir.exists():
        die("CONFLICT", f"Run ID conflict: {run_id}; register the run again")

    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    meta = {
        "run_id": run_id,
        "created_at": created_at,
        "updated_at": created_at,
        "method": args.method,
        "benchmark": args.benchmark,
        "experiment_group": args.experiment_group.strip() or None,
        "seed": args.seed,
        "status": args.status,
        "failure_reason": args.failure_reason.strip() or None,
        "cmd": args.cmd or None,
        "hardware": args.hardware or None,
        "cost": args.cost or None,
        "label": args.label or None,
        "git": git,
        "config": config_record,
        # F06: new records no longer write the reproducible boolean (a legacy field kept only for reading older runs);
        # report reproducibility_status=not_verified with a list of recorded and missing metadata instead.
        **reproducibility_info({"seed": args.seed, "git": git, "config": config_record}),
        "warnings": warnings,
    }

    runs_dir.mkdir(parents=True, exist_ok=True)
    try:
        temp_dir.mkdir(exist_ok=False)
        if config_bytes is not None and config_record is not None:
            (temp_dir / config_record["snapshot"]).write_bytes(config_bytes)
        (temp_dir / "meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (temp_dir / "metrics.json").write_text(
            json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        temp_dir.rename(run_dir)
    except Exception as exc:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        die("WRITE_FAILED", f"Run registration did not complete; no partial result was kept: {exc}")

    if args.json:
        print(json.dumps({"ok": True, "data": {"run_id": run_id, "run_dir": str(run_dir),
                                               "meta": meta, "metrics": metrics}},
                         ensure_ascii=False))
        return
    print("Registered {} → {}".format(run_id, run_dir))
    print("  {} × {} | seed={}".format(args.method, args.benchmark, args.seed if args.seed is not None else "null"))
    print("  commit={}{}".format((git["commit"] or "unknown")[:12], " (dirty)" if git["dirty"] else "") + (" | experiment group {}".format(args.experiment_group.strip()) if args.experiment_group.strip() else ""))

    missing = meta["repro_missing"]
    print("  Reproducibility metadata: no rerun verification was performed (not_verified)"
          + (" | Missing: " + missing if missing else " | Seed/clean commit/config recorded; this is still not verified"))
    if args.status == "running":
        print("  Placeholder run: record results with run_update.py when available; keep the same run ID")
    for w in warnings:
        print(f"  ⚠ {w}")


if __name__ == "__main__":
    main()
