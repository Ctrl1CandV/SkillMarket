# /// script
# requires-python = ">=3.12"
# ///
"""聚合 .grad/runs/ 生成 LaTeX booktabs 表（run-provenance）。

规则（对应 ARR 有效弱点 R1/R5 的防线）：
- 按 (方法 × benchmark × 比较设置) 分组，同组多 seed 算 mean ± std（样本标准差，ddof=1）
- **不同配置不能静默合并**：config 快照 sha 不一致、缺配置时保守分列；只有用户明确声明的
  同一 experiment_group 才自动合并（显式同组仍展示配置差异与分组依据）。规则在 run_grouping.py
- **n=1 时输出 `数值 (n=1)`，绝不输出 ±**——单次 run 报标准差是编造
- 表格末尾生成 % provenance 注释行，把每个数字指回 run id + commit
- 同组内出现重复 seed → 警告（cherry-picked best-of-N 的风险信号），只警告不剔除
- running 占位 run 不参与统计（结果未出）；failed 默认排除，--include-failed 显式纳入
- 只做算术与排版，不评判哪个方法好（无加粗、无最优标记）

输出契约：--json 时 stdout 打印 {"ok": true, "data": {...}} 或 {"ok": false, ...}。
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
    raise ValueError(f"不允许非有限 JSON 常量：{value}")


def validate_metrics(metrics: object, source: Path) -> dict[str, int | float]:
    if not isinstance(metrics, dict):
        die("BAD_RUN_DATA", f"{source} 必须是 JSON 对象")
    for key, value in metrics.items():
        if not isinstance(key, str) or not key.strip():
            die("BAD_RUN_DATA", f"{source} 的指标键必须是非空字符串")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            die("BAD_RUN_DATA", f"{source} 的指标 {key!r} 必须是有限数值")
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
            die("BAD_RUN_DATA", f"{d} 下的 run 数据解析失败：{exc}")
        if not isinstance(meta, dict):
            die("BAD_RUN_DATA", f"{meta_f} 必须是 JSON 对象")
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
    std = statistics.stdev(values)  # 样本标准差 ddof=1
    return f"{mean:.4g} $\\pm$ {std:.3g} (n={len(values)})", mean, std


def normalize_metric_key(key: str) -> str:
    """仅用于发现疑似拼写漂移；原始 key 永远不自动合并。"""
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
                        f"{method}×{benchmark}: 指标键疑似漂移 {left!r}（run {sources[left]}）与 "
                        f"{right!r}（run {sources[right]}）；仅告警，不自动合并"
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
                f"{method}×{benchmark}: 同组重复 seed {duplicates}——多次试验只挑最好即 best-of-N 风险（ARR R1），"
                "表内包含全部 run，是否剔除由人决定"
            )
        no_seed = [run["run_id"] for run in members if run["seed"] is None]
        if no_seed:
            warnings.append(f"{method}×{benchmark}: run {no_seed} 未登记 seed")
        no_commit = [run["run_id"] for run in members if not run["commit"]]
        if no_commit:
            warnings.append(f"{method}×{benchmark}: run {no_commit} 无 commit 记录（unknown）")
        buckets = same_setting_runs(members)
        setting_groups[(method, benchmark)] = buckets
        if len(buckets) > 1:
            warnings.append(
                f"{method}×{benchmark}: 配置不一致或缺配置，已按比较设置分为 {len(buckets)} 组分别呈现"
                f"（不静默合并均值）：{'；'.join(group_label(k, v) for k, v in sorted(buckets.items(), key=lambda i: str(i[0])))}"
            )
        for key, members_of_setting in buckets.items():
            if key[0] == "explicit" and len(members_of_setting) > 1:
                shas = {str((m.get("config") or {}).get("sha256") or "无快照") for m in members_of_setting}
                if len(shas) > 1:
                    warnings.append(
                        f"{method}×{benchmark}: 显式实验组 {key[3]} 内配置快照不一致"
                        f"（{'/'.join(sorted(s[:8] for s in shas))}），已按用户声明合并，分组依据见行标签"
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
                    provenance.append(f"% provenance {key} | {method} | {benchmark}: {source or '（无 run）'}")
                body_rows.append(latex_escape(method) + " & " + " & ".join(cells) + " \\\\")
                continue
            # 配置分列：一个 (benchmark, 比较设置组) 一行，行标签带分组依据，避免同名方法行无法区分
            for benchmark in benchmarks:
                buckets = per_bench[benchmark]
                if not buckets:
                    continue
                for setting_key, setting_runs in sorted(buckets.items(), key=lambda i: str(i[0])):
                    members = [run for run in setting_runs if key in run["metrics"]]
                    text, _, _ = cell_stats([float(run["metrics"][key]) for run in members])
                    label = f"{method}（{group_label(setting_key, setting_runs)}）"
                    row_cells = [text if bench == benchmark else "---" for bench in benchmarks]
                    body_rows.append(latex_escape(label) + " & " + " & ".join(row_cells) + " \\\\")
                    source = ", ".join(
                        f"{run['run_id']}@{(run['commit'] or 'unknown')[:8]}" for run in members
                    )
                    provenance.append(
                        f"% provenance {key} | {label} | {benchmark}: {source or '（无 run，该设置组无此指标）'}")
        latex = "\n".join([
            "\\begin{table}[t]",
            "  \\centering",
            f"  \\caption{{{latex_escape(key)} (mean $\\pm$ std, 样本标准差；n=1 标注而非伪造误差；"
            "不同比较设置分行不合并)}}",
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
    ap = argparse.ArgumentParser(description="聚合 runs 生成 LaTeX 表")
    ap.add_argument("--runs-dir", default=".grad/runs")
    ap.add_argument("--out", default="", help="把所有表写入该 .tex 文件（默认只打印）")
    ap.add_argument("--include-failed", action="store_true", help="显式纳入带数值指标的失败 run")
    ap.add_argument("--force", action="store_true", help="允许覆盖 --out 指定的既有文件")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.json and args.out:
        die("BAD_ARGS", "--json 与 --out 不能同时使用")
    if args.force and not args.out:
        die("BAD_ARGS", "--force 只能与 --out 一起使用")

    loaded = load_runs(Path(args.runs_dir))
    if not loaded:
        die("NO_RUNS", f"{args.runs_dir} 下没有可聚合的 run（需要 meta.json）。先跑 run_register.py 登记")

    failed = [run for run in loaded if run["status"] == "failed"]
    running = [run for run in loaded if run["status"] == "running"]
    successful = [run for run in loaded if run["status"] not in ("failed", "running")]
    failed_with_metrics = [run for run in failed if has_numeric_metrics(run)]
    runs = successful + failed_with_metrics if args.include_failed else successful
    tables, warnings = build_tables(runs)
    if not tables:
        die("NO_METRICS", "没有可聚合的有限数值指标；不会生成或覆盖表格文件")
    if running:
        warnings.append(f"running 占位 run 不参与统计（结果未出）：{[run['run_id'] for run in running]}")
    counts = {
        "n_runs_loaded": len(loaded),
        "n_runs_included": len(runs),
        "n_failed_skipped": len(failed) - (len(failed_with_metrics) if args.include_failed else 0),
        "n_running_skipped": len(running),
    }
    out = Path(args.out) if args.out else None
    if out is not None and out.exists() and not args.force:
        die("CONFLICT", f"输出已存在，不会覆盖：{out}；明确需要覆盖时加 --force")
    if args.json:
        print(json.dumps({"ok": True, "data": {**counts, "tables": tables,
                                               "warnings": warnings}}, ensure_ascii=False))
        return
    print(f"# {len(runs)}/{len(loaded)} 个 run 纳入 → {len(tables)} 张表")
    if counts["n_failed_skipped"]:
        print(f"# 默认跳过 {counts['n_failed_skipped']} 个失败 run；用 --include-failed 显式纳入")
    if counts["n_running_skipped"]:
        print(f"# 跳过 {counts['n_running_skipped']} 个 running 占位 run（结果未出，不参与统计）")
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
                die("CONFLICT", f"输出已存在，不会覆盖：{out}；明确需要覆盖时加 --force")
        print(f"\n已写入 {out}")


if __name__ == "__main__":
    main()
