# /// script
# requires-python = ">=3.12"
# ///
"""Aggregate .grad/runs/ into LaTeX booktabs tables (run-provenance).

Rules (defenses against effective ARR weaknesses R1/R5):
- Group by (method × benchmark × comparison settings); compute mean ± std (sample standard deviation, ddof=1) across seeds in a group.
- **Never silently combine different configs**: keep runs in separate columns/groups when config snapshot SHAs differ or are missing. Merge only when the user explicitly declares
  the same experiment_group (even then, show config differences and grouping basis). Rules live in run_grouping.py.
- **For n=1, output value (n=1), never ±**—a standard deviation from one run would be fabricated.
- Add % provenance comments after each table to trace every number to its run ID and commit.
- Warn about duplicate seeds in the same group (a best-of-N cherry-picking risk); warn without excluding rows.
- Exclude running placeholders (results are not ready); exclude failed by default and include them only with --include-failed.
- Do arithmetic and formatting only; do not judge which method is better (no bolding or best-result marker).

Output contract: with --json, stdout prints {"ok": true, "data": {...}} or {"ok": false, ...}.
"""

from __future__ import annotations

import argparse
from difflib import SequenceMatcher
import hashlib
import json
import math
import os
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_grouping import group_label, same_setting_runs

if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


def die(error: str, detail: str, **extra) -> None:
    print(json.dumps({"ok": False, "error": error, "detail": detail, **extra}, ensure_ascii=False))
    sys.exit(1)


def reject_json_constant(value: str) -> None:
    raise ValueError(f"Non-finite JSON constant is not allowed: {value}")


def validate_metrics(metrics: object, source: Path) -> dict[str, int | float]:
    if not isinstance(metrics, dict):
        die("BAD_RUN_DATA", f"{source} must be a JSON object")
    for key, value in metrics.items():
        if not isinstance(key, str) or not key.strip():
            die("BAD_RUN_DATA", f"{source} metric keys must be non-empty strings")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            die("BAD_RUN_DATA", f"Metric {key!r} in {source} must be a finite number")
    return metrics


def load_runs(runs_dir: Path) -> list[dict]:
    runs = []
    for d in sorted(runs_dir.iterdir()) if runs_dir.is_dir() else []:
        meta_f, metrics_f = d / "meta.json", d / "metrics.json"
        if not d.is_dir() or not meta_f.is_file():
            continue
        try:
            meta = json.loads(meta_f.read_text(encoding="utf-8"), parse_constant=reject_json_constant)
            metrics_raw = (json.loads(metrics_f.read_text(encoding="utf-8"), parse_constant=reject_json_constant)
                           if metrics_f.is_file() else {})
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            die("BAD_RUN_DATA", f"Could not parse run data under {d}: {exc}")
        if not isinstance(meta, dict):
            die("BAD_RUN_DATA", f"{meta_f} must be a JSON object")
        metrics = validate_metrics(metrics_raw, metrics_f)
        config = meta.get("config") if isinstance(meta.get("config"), dict) else None
        runs.append({
            "run_id": meta.get("run_id", d.name),
            "method": meta.get("method") or "unknown",
            "benchmark": meta.get("benchmark") or "unknown",
            "seed": meta.get("seed"),
            "commit": (meta.get("git") or {}).get("commit"),
            "status": meta.get("status") or "success",
            "failure_reason": meta.get("failure_reason"),
            "experiment_group": meta.get("experiment_group"),
            "config": config,
            "metrics": metrics,
        })
    return runs


def latex_escape(s: str) -> str:
    return re.sub(r"([&%$#_{}])", r"\\\1", s).replace("~", r"\textasciitilde{}").replace("^", r"\textasciicircum{}")


def label_safe(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def cell_stats(values: list[float]) -> tuple[str, float | None, float | None]:
    if not values:
        return "---", None, None
    if len(values) == 1:
        return f"{values[0]:.4g} (n=1)", values[0], None
    mean = statistics.fmean(values)
    std = statistics.stdev(values)  # Sample standard deviation, ddof=1.
    return f"{mean:.4g} $\\pm$ {std:.3g} (n={len(values)})", mean, std


def normalize_metric_key(key: str) -> str:
    """Detect suspected spelling drift only; never merge original keys automatically."""
    return re.sub(r"[\s\.,;:!?，。；：]+$", "", key.strip().casefold())


def has_numeric_metrics(run: dict) -> bool:
    return any(isinstance(value, (int, float)) and not isinstance(value, bool)
               for value in run["metrics"].values())


def metric_drift_warnings(groups: dict[tuple[str, str], list[dict]]) -> list[str]:
    warnings: list[str] = []
    for (method, benchmark), members in sorted(groups.items()):
        sources: dict[str, list[str]] = {}
        for run in members:
            for key, value in run["metrics"].items():
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    sources.setdefault(key, []).append(run["run_id"])
        keys = sorted(sources)
        for index, left in enumerate(keys):
            for right in keys[index + 1:]:
                normalized_left = normalize_metric_key(left)
                normalized_right = normalize_metric_key(right)
                same_normalized = normalized_left == normalized_right
                similar = (normalized_left and normalized_right and
                           SequenceMatcher(None, normalized_left, normalized_right).ratio() >= 0.94)
                if same_normalized or similar:
                    warnings.append(
                        f"{method}×{benchmark}: possible metric-key drift between {left!r} (run {sources[left]}) and "
                        f"{right!r} (run {sources[right]}); warning only, no automatic merge"
                    )
    return warnings


def build_tables(runs: list[dict]) -> tuple[list[dict], list[str]]:
    methods = sorted({r["method"] for r in runs})
    benchmarks = sorted({r["benchmark"] for r in runs})
    metric_keys = sorted({k for r in runs for k, value in r["metrics"].items()
                          if isinstance(value, (int, float)) and not isinstance(value, bool)})
    warnings: list[str] = []

    groups: dict[tuple[str, str], list[dict]] = {}
    setting_groups: dict[tuple[str, str], dict[tuple, list[dict]]] = {}
    for run in runs:
        groups.setdefault((run["method"], run["benchmark"]), []).append(run)
    for (method, benchmark), members in sorted(groups.items()):
        seeds = [seed for seed in (run["seed"] for run in members) if seed is not None]
        duplicates = sorted({seed for seed in seeds if seeds.count(seed) > 1})
        if duplicates:
            warnings.append(
                f"{method}×{benchmark}: duplicate seed in the same group {duplicates}—a best-of-N risk (ARR R1); "
                "the table still includes all runs; a person decides whether to exclude any"
            )
        no_seed = [run["run_id"] for run in members if run["seed"] is None]
        if no_seed:
            warnings.append(f"{method}×{benchmark}: run {no_seed} has no recorded seed")
        no_commit = [run["run_id"] for run in members if not run["commit"]]
        if no_commit:
            warnings.append(f"{method}×{benchmark}: run {no_commit} has no commit record (unknown)")
        buckets = same_setting_runs(members)
        setting_groups[(method, benchmark)] = buckets
        if len(buckets) > 1:
            warnings.append(
                warnings.append("{}×{}: Configs differ or are missing; presenting {} separate groups by comparison settings rather than silently averaging: {}".format(method, benchmark, len(buckets), "; ".join(group_label(k, v) for k, v in sorted(buckets.items(), key=lambda i: str(i[0])))))

            )
        for key, members_of_setting in buckets.items():
            if key[0] == "explicit" and len(members_of_setting) > 1:
                shas = {str((m.get("config") or {}).get("sha256") or "no-snapshot") for m in members_of_setting}
                if len(shas) > 1:
                    warnings.append(
                    warnings.append("{}×{}: Explicit experiment group {} has differing config snapshots ({}); merged per the user declaration. See row labels for the grouping basis.".format(method, benchmark, key[3], "/".join(sorted(s[:8] for s in shas))))

                    )
    warnings.extend(metric_drift_warnings(groups))

    tables = []
    for key in metric_keys:
        header = "Method & " + " & ".join(latex_escape(b) for b in benchmarks) + " \\\\"
        body_rows, provenance = [], []
        for method in methods:
            per_bench = {bench: setting_groups.get((method, bench), {}) for bench in benchmarks}
            split = any(len(buckets) > 1 for buckets in per_bench.values())
            if not split:
                cells = []
                for benchmark in benchmarks:
                    members = [run for run in groups.get((method, benchmark), []) if key in run["metrics"]]
                    values = [float(run["metrics"][key]) for run in members]
                    text, _, _ = cell_stats(values)
                    cells.append(text)
                    source = ", ".join(
                        f"{run['run_id']}@{(run['commit'] or 'unknown')[:8]}" for run in members
                    )
                    provenance.append("% provenance {} | {} | {}: {}".format(key, method, benchmark, source or "(no run)"))
                body_rows.append(latex_escape(method) + " & " + " & ".join(cells) + " \\\\")
                continue
            # Keep each (benchmark, comparison-settings group) on its own row; row labels show the grouping basis and distinguish methods with the same name.
            for benchmark in benchmarks:
                buckets = per_bench[benchmark]
                if not buckets:
                    continue
                for setting_key, setting_runs in sorted(buckets.items(), key=lambda i: str(i[0])):
                    members = [run for run in setting_runs if key in run["metrics"]]
                    text, _, _ = cell_stats([float(run["metrics"][key]) for run in members])
                    label = f"{method} ({group_label(setting_key, setting_runs)})"

                    body_rows.append(latex_escape(label) + " & " + " & ".join(row_cells) + " \\\\")
                    source = ", ".join(
                        f"{run['run_id']}@{(run['commit'] or 'unknown')[:8]}" for run in members
                    )
                    provenance.append(
                        "% provenance {} | {} | {}: {}".format(key, label, benchmark, source or "(no run; this settings group has no value for this metric)"))
        latex = "\n".join([
            "\\begin{table}[t]",
            "  \\centering",
            f"  \\caption{{{latex_escape(key)} (mean $\\pm$ std, sample standard deviation; n=1 is labeled rather than given a fabricated error; "
            "different comparison settings are shown on separate rows)}}",
            f"  \\label{{tab:{label_safe(key)}-{hashlib.sha256(key.encode('utf-8')).hexdigest()[:8]}}}",
            f"  \\begin{{tabular}}{{l{'c' * len(benchmarks)}}}",
            "    \\toprule",
            f"    {header}",
            "    \\midrule",
            *[f"    {row}" for row in body_rows],
            "    \\bottomrule",
            "  \\end{tabular}",
            "\\end{table}",
            *provenance,
        ])
        tables.append({"metric": key, "latex": latex})
    return tables, warnings



def main() -> None:
    ap = argparse.ArgumentParser(description="Aggregate runs into LaTeX tables")
    ap.add_argument("--runs-dir", default=".grad/runs")
    ap.add_argument("--out", default="", help="Write all tables to this .tex file (prints to stdout by default)")
    ap.add_argument("--include-failed", action="store_true", help="Explicitly include failed runs that have numeric metrics")
    ap.add_argument("--force", action="store_true", help="Allow overwriting the existing file specified by --out")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.json and args.out:
        die("BAD_ARGS", "--json and --out cannot be used together")
    if args.force and not args.out:
        die("BAD_ARGS", "--force can only be used with --out")

    loaded = load_runs(Path(args.runs_dir))
    if not loaded:
        die("NO_RUNS", f"No usable runs found under {args.runs_dir} (meta.json is required); register runs with run_register.py first")

    failed = [run for run in loaded if run["status"] == "failed"]
    running = [run for run in loaded if run["status"] == "running"]
    successful = [run for run in loaded if run["status"] not in ("failed", "running")]
    failed_with_metrics = [run for run in failed if has_numeric_metrics(run)]
    runs = successful + failed_with_metrics if args.include_failed else successful
    tables, warnings = build_tables(runs)
    if not tables:
        die("NO_METRICS", "No finite numeric metrics are available; no table will be generated or overwritten")
    if running:
        warnings.append("Running placeholder runs are excluded from statistics (results are not ready): {}".format([run["run_id"] for run in running]))
    counts = {
        "n_runs_loaded": len(loaded),
        "n_runs_included": len(runs),
        "n_failed_skipped": len(failed) - (len(failed_with_metrics) if args.include_failed else 0),
        "n_running_skipped": len(running),
    }
    out = Path(args.out) if args.out else None
    if out is not None and out.exists() and not args.force:
        die("CONFLICT", f"Output already exists and will not be overwritten: {out}; pass --force to overwrite it explicitly")
    if args.json:
        print(json.dumps({"ok": True, "data": {**counts, "tables": tables,
                                               "warnings": warnings}}, ensure_ascii=False))
        return
    print("# {}/{} runs included → {} tables".format(len(runs), len(loaded), len(tables)))
    if counts["n_failed_skipped"]:
        print("# {} failed runs skipped by default; use --include-failed to include them".format(counts["n_failed_skipped"]))
    if counts["n_running_skipped"]:
        print("# {} running placeholder runs skipped (results are not ready)".format(counts["n_running_skipped"]))
    for t in tables:
        print(f"\n{t['latex']}")
    for w in warnings:
        print(f"⚠ {w}")
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        content = "\n\n".join(table["latex"] for table in tables) + "\n"
        if args.force:
            temp = out.with_name(f".{out.name}.tmp-{os.getpid()}")
            try:
                temp.write_text(content, encoding="utf-8")
                os.replace(temp, out)
            finally:
                temp.unlink(missing_ok=True)
        else:
            try:
                with out.open("x", encoding="utf-8", newline="\n") as handle:
                    handle.write(content)
            except FileExistsError:
                die("CONFLICT", f"Output already exists and will not be overwritten: {out}; pass --force to overwrite it explicitly")
        print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
