# /// script
# requires-python = ">=3.12"
# ///
"""实验 run 结果补录（run-provenance）。更新已存在 run 的指标/状态，不重建 run id。

只允许改动：metrics、status（running/success/failed）、failure_reason、updated_at。
**不重新采集 git 状态冒充实验当时的 commit，不改 config 快照与 seed**——原来源永远保留。

铁律：
- 写入前先完成全部输入校验（指标有限数值、failed 必须带原因）；校验不过不落盘
- 落盘用同目录临时文件 + 原子替换；第二步失败时回滚第一步，不留「半更新」状态
- 历史 run 没有 updated_at 不猜补录时间；本脚本写入的 updated_at 是真实的本次更新时间

输出契约：--json 时 stdout 打印 {"ok": true, "data": {...}} 或 {"ok": false, ...}。
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


def atomic_replace(path: Path, content: str) -> None:
    temp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        temp.write_text(content, encoding="utf-8")
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="补录已登记 run 的结果（只动指标/状态/更新时间）")
    ap.add_argument("--run-id", required=True, help="要补录的 run id（目录名）")
    ap.add_argument("--runs-dir", default=".grad/runs")
    ap.add_argument("--status", choices=("running", "success", "failed"), default="",
                    help="补录后的状态；不给则保持原状态")
    ap.add_argument("--failure-reason", default="", help="失败原因；status=failed 时必填")
    ap.add_argument("--metrics-file", default="", help="指标 JSON 文件路径（整体替换 metrics.json）")
    ap.add_argument("--metrics", default="", help="内联指标 JSON（整体替换 metrics.json）")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    runs_input = Path(args.runs_dir)
    if ".grad" not in runs_input.resolve().parts:
        die("BAD_ARGS", f"runs-dir 必须位于项目 .grad/ 下：{runs_input.resolve()}")
    # REV-08：run-id 只接受单个合法目录名——绝对路径、父目录跳转、含分隔符一律先拒
    rid = args.run_id
    if (not rid or rid.strip() != rid or rid.startswith(".")
            or "/" in rid or "\\" in rid or re.search(r"[<>|:*?\x00]", rid)):
        die("BAD_ARGS", f"run-id 必须是单个合法目录名（不含路径分隔符/绝对路径/上级跳转）：{rid!r}")
    runs_resolved = runs_input.resolve()
    run_dir = (runs_resolved / rid)
    if not run_dir.resolve().is_relative_to(runs_resolved):
        die("BAD_ARGS", f"run-id 解析后逃逸 runs 根目录：{rid!r}；拒绝写入")
    if args.status == "failed" and not args.failure_reason.strip():
        die("BAD_ARGS", "status=failed 时必须提供非空 --failure-reason")
    if args.status and args.status != "failed" and args.failure_reason.strip():
        die("BAD_ARGS", "failure-reason 只用于 failed run")
    if args.metrics_file and args.metrics:
        die("BAD_ARGS", "--metrics 与 --metrics-file 只能给一个")

    metrics: dict[str, int | float] | None = None
    if args.metrics_file:
        metrics_file = Path(args.metrics_file)
        if not metrics_file.is_file():
            die("BAD_METRICS", f"metrics 文件不存在：{metrics_file}")
        try:
            metrics_text = metrics_file.read_text(encoding="utf-8")
        except OSError as exc:
            die("BAD_METRICS", f"无法读取 metrics 文件：{exc}")
        metrics = parse_metrics(metrics_text, "metrics 文件")
    elif args.metrics:
        metrics = parse_metrics(args.metrics, "--metrics")

    meta_f = run_dir / "meta.json"
    if not run_dir.is_dir() or not meta_f.is_file():
        die("NOT_FOUND", f"run 不存在：{run_dir}；补录只能针对已登记的 run（新 run 用 run_register.py）")
    try:
        meta = json.loads(meta_f.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        die("BAD_RUN_DATA", f"{meta_f} 不可解析，拒绝在坏数据上补录：{exc}")
    if not isinstance(meta, dict):
        die("BAD_RUN_DATA", f"{meta_f} 必须是 JSON 对象")

    old_meta_text = meta_f.read_text(encoding="utf-8")
    metrics_f = run_dir / "metrics.json"
    old_metrics_text = metrics_f.read_text(encoding="utf-8") if metrics_f.is_file() else None

    # REV-07：状态与失败原因按「最终要写入的数据」处理——
    # 只补指标（不给 --status）不动状态与原因；显式转 failed 必须带有效原因（可用新原因更新）；
    # 显式转非 failed 才清除旧原因。
    new_status = args.status or str(meta.get("status") or "success")
    meta["status"] = new_status
    if args.status == "failed":
        meta["failure_reason"] = args.failure_reason.strip()
    elif args.status and args.status != "failed":
        meta["failure_reason"] = None
    # args.status 为空：status 与 failure_reason 均保持原值
    if str(meta.get("status")) == "failed" and not str(meta.get("failure_reason") or "").strip():
        die("BAD_ARGS", "补录后的最终状态是 failed 但没有有效失败原因；"
                        "给 --failure-reason 或改到正确状态，拒绝写入半残记录")
    meta["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    warnings: list[str] = []
    if metrics is not None and new_status == "success" and not metrics:
        warnings.append("补录了空指标且状态为 success：无结果的 run 不应登记为成功实验，可保持 running 或如实 failed")
    if metrics is None and args.status == "success":
        warnings.append("仅改状态为 success 但未补录指标：该 run 仍无可核对数值")

    # 先写 meta，再写 metrics；第二步失败回滚第一步（单写者顺序操作，不承诺断电级事务）
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
                metrics_f.unlink()  # 原本没有 metrics.json：删除本次写坏的半成品
            rollback = "已回滚到更新前内容"
        except OSError as rollback_exc:
            rollback = f"回滚也失败（{rollback_exc}），原 meta 文本仍可参照报错手工恢复"
        die("WRITE_FAILED", f"补录未完成：{exc}；{rollback}，不返回成功")

    data = {"run_id": args.run_id, "meta": meta,
            "metrics": metrics if metrics is not None else "（未改动）",
            "warnings": warnings,
            "note": "补录只更新指标/状态/updated_at；created_at、git commit、config 快照保持原样"}
    if args.json:
        print(json.dumps({"ok": True, "data": data}, ensure_ascii=False))
        return
    print(f"已补录 {args.run_id}：status={new_status}｜updated_at={meta['updated_at']}")
    if metrics is not None:
        print(f"  metrics → {json.dumps(metrics, ensure_ascii=False)}")
    for w in warnings:
        print(f"  ⚠ {w}")


if __name__ == "__main__":
    main()
