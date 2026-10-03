# /// script
# requires-python = ">=3.12"
# ///
"""claim 台账登记（run-provenance）。evidence/support 双轴的写入护栏。

add      登记一条 claim：绑定 run 与指标键，claim_id 自动分配，support 固定 unreviewed
support  记录人的判定（supported/partial/refuted）：追加新行，同 claim_id 最后一行为当前

铁律：JSONL 只追加不回写；add 没有 --support 参数（人的判定只有 support 子命令一条路，
且 --by 必须来自用户明示，agent 不得代填）；不猜，缺失信息标 null。

输出契约：--json 时 stdout 打印 {"ok": true, "data": {...}} 或 {"ok": false, ...}。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_grouping import same_setting_runs  # 与 table_gen/claim_check 共用同一套可比性规则

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
            die("BAD_LEDGER", f"{path} 第 {no} 行不是合法 JSON：{exc}")
        if not isinstance(row, dict):
            die("BAD_LEDGER", f"{path} 第 {no} 行必须是 JSON 对象")
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
    """同 claim_id 最后一行为当前状态（台账只追加，靠解析规则取当前）。"""
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
    """台账只能写在 .grad/ 下（对齐 run_register 的 runs-dir 护栏：改动不越出项目状态目录）。"""
    resolved = Path(path_text).resolve()
    if ".grad" not in resolved.parts:
        die("BAD_ARGS", f"claims-file 必须位于项目 .grad/ 目录下：{resolved}")
    return Path(path_text)


def cmd_add(args: argparse.Namespace) -> None:
    claim = args.claim.strip()
    runs = [r.strip() for r in args.runs.split(",") if r.strip()]
    metric = args.metric.strip()
    if not claim:
        die("BAD_ARGS", "--claim 不能为空")
    if not runs:
        die("BAD_ARGS", "--runs 至少要有一个 run id")
    if not metric:
        die("BAD_ARGS", "--metric 不能为空")

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
            warnings.append(f"run {rid} 未在 {runs_dir} 找到（若稍后登记可忽略，claim_check 会复核）")
            continue
        if not meta_f.is_file():
            continue
        try:
            meta = json.loads(meta_f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            warnings.append(f"run {rid} 的 meta.json 不可解析，跳过一致性检查")
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
            warnings.append(f"绑定的 run 混用 {field}：{sorted(values)}（它们将被求均值，请确认）")
    if settings_seen and len(same_setting_runs(settings_seen)) > 1:
        warnings.append(
            "绑定的 run 分属不同比较设置（method/benchmark 或 config 快照不一致/缺配置）：claim_check 不会给已验证均值；"
            "确认属同一实验时用 run_register.py --experiment-group 显式声明同组"
        )

    binding = (claim, tuple(sorted(runs)), metric)
    for row in rows:
        existing = (str(row.get("claim_text", "")),
                    tuple(sorted(str(r) for r in (row.get("run_ids") or []))),
                    str(row.get("metric_path", "")))
        if existing == binding:
            warnings.append(
                f"与既有条目（{row.get('claim_id', 'legacy')}）绑定完全相同，可能是重复登记；仍会追加，不静默合并"
            )

    claim_id = next_claim_id(rows)
    row_index = len(rows)  # 新行在解析后行序列中的 0 基位置
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
    print(f"已登记 {claim_id} → {claims_path}（support=unreviewed，人的判定只能经 support 子命令写入）")
    for warning in warnings:
        print(f"  ⚠ {warning}")


def cmd_support(args: argparse.Namespace) -> None:
    by = args.by.strip()
    if not by:
        die("BAD_ARGS", "--by 不能为空；只记录用户明示的判定（agent 不得代填）")
    claims_path = require_grad_path(args.claims_file)
    rows = load_rows(claims_path)
    latest = current_rows(rows)
    if args.id not in latest:
        die("NOT_FOUND", f"claim_id {args.id!r} 不存在；已知：{sorted(latest) if latest else '（无）'}")
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
    print(f"已记录判定 {args.id} → {args.verdict}（by {by}）")


def main() -> None:
    ap = argparse.ArgumentParser(description="claim 台账登记（只追加；support 只能由人经 --by 写入）")
    sub = ap.add_subparsers(dest="command", required=True)

    ap_add = sub.add_parser("add", help="登记一条 claim（绑定 run 与指标键）")
    ap_add.add_argument("--claim", required=True, help="论断原文（论文里的那句话，数字保留原文写法）")
    ap_add.add_argument("--runs", required=True, help="绑定的 run id，逗号分隔；多 seed 全部绑定，不挑最好的")
    ap_add.add_argument("--metric", required=True, help="指标键，如 resolved_rate")
    ap_add.add_argument("--claims-file", default=".grad/claims.jsonl")
    ap_add.add_argument("--runs-dir", default=".grad/runs", help="仅用于存在性与一致性警告，不阻断")
    ap_add.add_argument("--json", action="store_true")

    ap_sup = sub.add_parser("support", help="记录人的判定（追加新行，同 id 最后一行为当前）")
    ap_sup.add_argument("--id", required=True, help="claim_id，如 c-001")
    ap_sup.add_argument("--verdict", required=True, choices=("supported", "partial", "refuted"))
    ap_sup.add_argument("--by", required=True, help="谁判定的——必须来自用户明示，agent 不得代填")
    ap_sup.add_argument("--claims-file", default=".grad/claims.jsonl")
    ap_sup.add_argument("--json", action="store_true")

    args = ap.parse_args()
    if args.command == "add":
        cmd_add(args)
    else:
        cmd_support(args)


if __name__ == "__main__":
    main()
