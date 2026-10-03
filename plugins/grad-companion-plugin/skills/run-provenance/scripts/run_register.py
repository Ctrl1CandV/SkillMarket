# /// script
# requires-python = ">=3.12"
# ///
"""实验 run 登记（run-provenance）。**只读只记，不执行任何东西**——不启动训练、不改超参、不删文件。

做什么：生成 run id、采集 git 状态、快照 config、记录指标/seed/硬件，写 `.grad/runs/<run-id>/meta.json` 与 `metrics.json`。

铁律：不猜。用户没给 seed 就写 null 并输出警告；不在 git 仓库就记 unknown；
config 路径不存在就记 null。缺失信息永远标 unknown/null，不填猜测值。

「可复现」只登记、不证明：新记录写 reproducibility_status=not_verified——seed 与干净
commit 齐全也只说明复现信息已登记，不代表做过重跑验证（复现验证不在本 skill 范围）。
占位 run（实验刚启动、无结果）用 --status running；结束后用 run_update.py 补录结果。

输出契约：--json 时 stdout 打印 {"ok": true, "data": {...}} 或 {"ok": false, ...}。
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
from run_grouping import reproducibility_info  # 同 skill 内共享的分组/复现信息小模块

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
                "note": "git 不可用，commit 记为 unknown"}
    if r.returncode != 0:
        return {"commit": None, "dirty": None, "dirty_files": 0,
                "note": "不在 git 仓库，commit 记为 unknown"}
    commit = r.stdout.strip()
    s = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True,
                       cwd=str(cwd), timeout=15)
    dirty_lines = [l for l in (s.stdout or "").splitlines() if l.strip()]
    return {"commit": commit, "dirty": bool(dirty_lines), "dirty_files": len(dirty_lines)}


def reject_json_constant(value: str) -> None:
    raise ValueError(f"不允许非有限 JSON 常量：{value}")


def parse_metrics(text: str, source: str) -> dict[str, int | float]:
    try:
        data = json.loads(text, parse_constant=reject_json_constant)
    except (json.JSONDecodeError, ValueError) as exc:
        die("BAD_METRICS", f"{source} 不是合法指标 JSON：{exc}")
    if not isinstance(data, dict):
        die("BAD_METRICS", "metrics 必须是 JSON 对象（指标名到数值的映射）")
    for key, value in data.items():
        if not isinstance(key, str) or not key.strip():
            die("BAD_METRICS", "metrics 的键必须是非空字符串")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            die("BAD_METRICS", f"指标 {key!r} 必须是有限数值，不能是 bool、字符串、对象、NaN 或 Infinity")
    return data


def main() -> None:
    ap = argparse.ArgumentParser(description="登记一个实验 run（只读只记）")
    ap.add_argument("--method", required=True, help="方法名（表格按 方法×benchmark 分组）")
    ap.add_argument("--benchmark", required=True, help="benchmark/数据集名")
    ap.add_argument("--seed", type=int, default=None, help="随机种子；不给就记 null（并警告不可复现）")
    ap.add_argument("--status", choices=("success", "failed", "running"), default="success",
                    help="run 状态；失败 run 也要登记；实验刚启动无结果用 running 占位（结束后 run_update.py 补录）")
    ap.add_argument("--failure-reason", default="", help="失败原因；status=failed 时必填")
    ap.add_argument("--experiment-group", default="",
                    help="可选实验组名：用户明确确认这些 run 属同一比较设置时才填（agent 不得猜填）")
    ap.add_argument("--cmd", default="", help="实际执行的命令行")
    ap.add_argument("--hardware", default="", help="硬件描述，如 'A100 x8'")
    ap.add_argument("--cost", default="", help="成本记录（token 数/费用/时长，自由文本）")
    ap.add_argument("--label", default="", help="人类可读备注")
    ap.add_argument("--config", default="", help="config 文件路径（会复制快照进 run 目录）")
    ap.add_argument("--metrics-file", default="", help="指标 JSON 文件路径")
    ap.add_argument("--metrics", default="", help="内联指标 JSON 字符串，如 '{\"acc\": 0.712}'")
    ap.add_argument("--runs-dir", default=".grad/runs")
    ap.add_argument("--repo", default=".", help="git 仓库目录（默认当前目录）")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.status == "failed" and not args.failure_reason.strip():
        die("BAD_ARGS", "status=failed 时必须提供非空 --failure-reason")
    if args.status != "failed" and args.failure_reason.strip():
        die("BAD_ARGS", "failure-reason 只用于 failed run")

    warnings: list[str] = []
    repo = Path(args.repo).resolve()
    grad_root = (repo / ".grad").resolve()
    runs_input = Path(args.runs_dir)
    runs_dir = (runs_input if runs_input.is_absolute() else repo / runs_input).resolve()
    if runs_dir == grad_root or not runs_dir.is_relative_to(grad_root):
        die("BAD_ARGS", f"runs-dir 必须位于项目 .grad/ 的子目录下：{grad_root}")

    # 所有输入先验证，失败时不创建任何 run 目录。
    metrics: dict[str, int | float] = {}
    if args.metrics_file:
        metrics_file = Path(args.metrics_file)
        if not metrics_file.is_file():
            warnings.append(f"metrics 文件不存在：{metrics_file}，metrics 记为空")
        else:
            try:
                metrics_text = metrics_file.read_text(encoding="utf-8")
            except OSError as exc:
                die("BAD_METRICS", f"无法读取 metrics 文件：{exc}")
            metrics = parse_metrics(metrics_text, "metrics 文件")
    elif args.metrics:
        metrics = parse_metrics(args.metrics, "--metrics")
    else:
        warnings.append("未提供指标，metrics.json 为空（结束后可补填）")

    config_record = None
    config_bytes: bytes | None = None
    if args.config:
        config_source = Path(args.config)
        if not config_source.is_file():
            config_record = {"path": str(config_source), "snapshot": None, "sha256": None}
            warnings.append(f"config 文件不存在：{config_source}，记为 null")
        else:
            try:
                config_bytes = config_source.read_bytes()
            except OSError as exc:
                die("CONFIG_READ_FAILED", f"无法读取 config：{exc}")
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
        warnings.append(f"工作区脏（{git['dirty_files']} 个未提交文件），commit 不足以定位此 run 的代码")
    if args.seed is None:
        warnings.append("未登记 seed，复现信息不完整")

    run_id = datetime.now().strftime("run-%Y%m%d-%H%M%S-") + f"{random.randrange(0x10000):04x}"
    run_dir = runs_dir / run_id
    temp_dir = runs_dir / f".{run_id}.tmp"
    if run_dir.exists() or temp_dir.exists():
        die("CONFLICT", f"run id 冲突：{run_id}，请重新登记")

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
        # F06：新记录不再写 reproducible 布尔（那是旧字段，只兼容读取历史 run）；
        # 复现信息以 reproducibility_status=not_verified + 已登记/缺失清单呈现
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
        die("WRITE_FAILED", f"run 登记未完成，未保留半成品：{exc}")

    if args.json:
        print(json.dumps({"ok": True, "data": {"run_id": run_id, "run_dir": str(run_dir),
                                               "meta": meta, "metrics": metrics}},
                         ensure_ascii=False))
        return
    print(f"已登记 {run_id} → {run_dir}")
    print(f"  {args.method} × {args.benchmark}｜seed={args.seed if args.seed is not None else 'null'}"
          f"｜commit={(git['commit'] or 'unknown')[:12]}{'（脏）' if git['dirty'] else ''}"
          + (f"｜实验组 {args.experiment_group.strip()}" if args.experiment_group.strip() else ""))
    missing = meta["repro_missing"]
    print("  复现信息：未执行复现验证（not_verified）"
          + (f"｜缺 {missing}" if missing else "｜seed/干净 commit/config 已登记，仍不代表可复现已验证"))
    if args.status == "running":
        print("  占位登记：结果出来后用 run_update.py 补录，不重建 run id")
    for w in warnings:
        print(f"  ⚠ {w}")


if __name__ == "__main__":
    main()
