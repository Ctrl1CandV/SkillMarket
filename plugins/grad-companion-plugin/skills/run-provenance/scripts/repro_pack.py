# /// script
# requires-python = ">=3.12"
# ///
"""可复现发布包生成（run-provenance）。从 .grad/runs/ 与 claims 台账生成 REPRODUCING.md。

对冲「83% 发布代码 vs 38% 发布 seed/trace」的差距（arXiv:2608.05179）：发布包里
seed 表 + 可复制命令行 + commit/config 指针，审稿人问「怎么跑出来的」直接给文件。

铁律：
- 不执行任何命令、不猜缺失字段——缺 seed/cmd/hardware 一律标 MISSING 并汇总计数
- **只报告复现信息登记状态，不声称实验可复现**：seed/commit/干净工作区齐全 = 信息已登记
  （reproducibility_status=not_verified）；本工具从未在别的机器重跑过，没有验证这回事。
  历史 run 的 `reproducible` 布尔仅作旧字段兼容读取，不继承为「已验证可复现」
- 默认只打印；--out 写文件走 CONFLICT/--force 护栏（同 table_gen）
- 自查清单来自 references/budget.md 五项，其中两项按表自动填 ✅/❌，其余留给人工

输出契约：--json 时 stdout 打印 {"ok": true, "data": {...}} 或 {"ok": false, ...}。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_grouping import reproducibility_info  # F06：复现信息只登记、不证明（与 run_register 同一规则）

if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

SUPPORT_VALUES = {"unreviewed", "supported", "partial", "refuted"}


def die(error: str, detail: str, **extra) -> None:
    print(json.dumps({"ok": False, "error": error, "detail": detail, **extra}, ensure_ascii=False))
    sys.exit(1)


def load_runs(runs_dir: Path) -> list[dict]:
    runs = []
    for d in sorted(runs_dir.iterdir()) if runs_dir.is_dir() else []:
        meta_f = d / "meta.json"
        if not d.is_dir() or not meta_f.is_file():
            continue
        try:
            meta = json.loads(meta_f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            die("BAD_RUN_DATA", f"{d} 的 meta.json 解析失败：{exc}")
        if not isinstance(meta, dict):
            die("BAD_RUN_DATA", f"{meta_f} 必须是 JSON 对象")
        config = meta.get("config") or {}
        runs.append({
            "run_id": str(meta.get("run_id") or d.name),
            "method": meta.get("method"),
            "benchmark": meta.get("benchmark"),
            "seed": meta.get("seed"),
            "status": str(meta.get("status") or "success"),
            "failure_reason": meta.get("failure_reason"),
            "hardware": meta.get("hardware"),
            "cmd": meta.get("cmd"),
            "commit": (meta.get("git") or {}).get("commit"),
            "dirty": (meta.get("git") or {}).get("dirty"),
            "config_path": config.get("path"),
            "config_sha256": config.get("sha256"),
            # F06：每 run 现算复现信息登记状态；legacy `reproducible` 布尔只兼容读取，
            # 不继承为「已验证可复现」——本工具从未在别的机器重跑过
            "repro": reproducibility_info(meta),
        })
    return runs


def resolve_claims(claims_path: Path) -> list[dict]:
    """同 claim_id 最后一行为当前；无 claim_id 为 legacy 行（support 视为 unreviewed）。"""
    if not claims_path.is_file():
        return []
    rows: list[dict] = []
    for line in claims_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # 坏行跳过并计数，不中断发布包生成
    latest: dict[str, dict] = {}
    legacy: list[dict] = []
    for row in rows:
        cid = row.get("claim_id")
        if isinstance(cid, str) and cid:
            latest[cid] = row
        else:
            legacy.append(row)
    out = list(latest.values()) + [{"claim_id": f"legacy-{i}", **row} for i, row in enumerate(legacy)]
    for c in out:
        if c.get("support") not in SUPPORT_VALUES:
            c["support"] = "unreviewed"  # 执行者写的旧 status 不继承为人的判定
    return out


def render(runs: list[dict], claims: list[dict]) -> tuple[str, dict]:
    lines: list[str] = [
        "# REPRODUCING",
        "",
        f"> 由 repro_pack.py 于 {datetime.now().astimezone().isoformat(timespec='seconds')} 从 .grad/runs/ 生成；"
        "MISSING 表示台账里没有该字段（不猜测）。",
        "",
        "## Seed 表",
        "",
        "| run | method × benchmark | seed | status | hardware | commit | config (sha256 前 8) |",
        "|---|---|---|---|---|---|---|",
    ]
    missing = {"seed": [], "cmd": [], "hardware": []}
    seeded_count = 0
    for run in runs:
        has_seed = run["seed"] is not None
        if has_seed:
            seeded_count += 1
        else:
            missing["seed"].append(run["run_id"])
        if not run["cmd"]:
            missing["cmd"].append(run["run_id"])
        if not run["hardware"]:
            missing["hardware"].append(run["run_id"])
        sha = (run["config_sha256"] or "")[:8]
        config_cell = ""
        if run["config_path"]:
            config_cell = f"`{run['config_path']}` ({sha})" if sha else f"`{run['config_path']}`"
        else:
            config_cell = "MISSING"
        status_cell = run["status"]
        if run["status"] == "failed" and run["failure_reason"]:
            status_cell += f"（{run['failure_reason']}）"
        lines.append(
            f"| `{run['run_id']}` | {run['method'] or 'MISSING'} × {run['benchmark'] or 'MISSING'} "
            f"| {run['seed'] if has_seed else '**MISSING**'} | {status_cell} "
            f"| {run['hardware'] or '**MISSING**'} "
            f"| {(run['commit'] or '')[:10] or 'MISSING'} | {config_cell} |"
        )

    cmd_section = ["", "## 复现命令（已登记，不等于已验证重跑）", ""]
    usable_cmds = [run for run in runs if run["cmd"]]
    if usable_cmds:
        for run in usable_cmds:
            label = f"{run['method']} × {run['benchmark']}".strip(" ×")
            cmd_section += [f"# {label} — seed={run['seed'] if run['seed'] is not None else 'MISSING'} "
                            f"@ {(run['commit'] or 'unknown')[:10]}",
                            "```bash", str(run["cmd"]), "```", ""]
    else:
        cmd_section += ["（没有任何 run 登记过 `--cmd`，全部标 MISSING——可复制性检查不过）", ""]
    missing_cmds = sum(1 for run in runs if not run["cmd"])

    repro_section = ["", "## 复现信息登记状态（reproducibility_status: not_verified——未执行复现验证）", ""]
    for run in runs:
        info = run["repro"]
        missing_note = "、".join(info["repro_missing"]) if info["repro_missing"] else "无（登记信息齐全）"
        repro_section.append(f"- `{run['run_id']}`：缺 {missing_note}")
    repro_section += [
        "",
        "登记信息齐全也只说明复现材料完备；本包从未在其他机器重跑验证，不能据此宣称实验可复现。"
        "历史 run 的旧 `reproducible` 布尔仅兼容读取，不继承为已验证结论。",
        "",
    ]

    claim_section = ["", "## 论文数字 ↔ run 关联（claims 台账当前状态）", ""]
    if claims:
        claim_section += ["| claim | runs | evidence 键存在 | support | by |", "|---|---|---|---|---|"]
        n_supported = 0
        for claim in claims:
            supports = ", ".join(f"`{r}`" for r in (claim.get("run_ids") or [])) or "—"
            support = claim.get("support")
            if support == "supported":
                n_supported += 1
            text = str(claim.get("claim_text", "")).replace("|", "\\|").replace("\n", " ")
            if len(text) > 60:
                text = text[:57] + "…"
            claim_section.append(
                f"| {text} | {supports} | （见 seed 表与 metrics.json） | {support} "
                f"| {claim.get('support_by') or '—'} |")
        claim_section.append("")
        claim_section.append(f"{len(claims)} 条中 {n_supported} 条为 supported（人的判定），"
                             "其余 unreviewed/partial/refuted 如实保留。")
    else:
        claim_section += ["（claims.jsonl 不存在或为空：没有论文数字 ↔ run 绑定记录。）"]

    all_seeded = len(missing["seed"]) == 0
    all_cmds = missing_cmds == 0
    checklist = [
        "", "## 发布前自查（budget.md 清单；✅ 已机械核对 / ❌ 未过 / ☐ 需人工）", "",
        f"- {'✅' if all_seeded else '❌'} 每个 seed 都在上方 Seed 表显式列出"
        + ("" if all_seeded else f"（缺：{', '.join(missing['seed'])}）"),
        f"- {'✅' if all_cmds else '❌'} 关键实验命令行可复制粘贴重跑"
        + ("" if all_cmds else f"（{missing_cmds}/{len(runs)} 个 run 缺 cmd）"),
        "- ☐ 代码发布：repo 指向论文里的 commit（不是最新 main）",
        "- ☐ 随机性来源盘点：numpy/torch seed、CUDA 非确定性、shuffle、温度采样——逐一固定或声明",
        "- ☐ 执行 trace（可选但差异化）：输入输出日志、中间 checkpoint 索引",
    ]
    body = "\n".join(lines + cmd_section + repro_section + claim_section + checklist) + "\n"
    stats = {"n_runs": len(runs), "n_claims": len(claims), "n_seeded": seeded_count,
             "n_missing_seed": len(missing["seed"]), "n_missing_cmd": len(missing["cmd"]),
             "n_missing_hardware": len(missing["hardware"]),
             "reproducibility_status": "not_verified",
             "all_seeded": all_seeded, "all_commands_recorded": all_cmds}
    return body, stats


def main() -> None:
    ap = argparse.ArgumentParser(description="生成 REPRODUCING.md（只搬运台账事实，不猜不执行）")
    ap.add_argument("--runs-dir", default=".grad/runs")
    ap.add_argument("--claims", default=".grad/claims.jsonl")
    ap.add_argument("--out", default="", help="写入该 .md 文件（默认打印）；已存在时报 CONFLICT")
    ap.add_argument("--force", action="store_true", help="允许覆盖 --out 指定的既有文件")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.json and args.out:
        die("BAD_ARGS", "--json 与 --out 不能同时使用")
    if args.force and not args.out:
        die("BAD_ARGS", "--force 只能与 --out 一起使用")

    runs_dir = Path(args.runs_dir)
    runs = load_runs(runs_dir)
    if not runs:
        die("NO_RUNS", f"{runs_dir} 下没有可用的 run（需要 meta.json）。先跑 run_register.py 登记")
    claims = resolve_claims(Path(args.claims))
    doc, stats = render(runs, claims)

    out = Path(args.out) if args.out else None
    if out is not None and out.exists() and not args.force:
        die("CONFLICT", f"输出已存在，不会覆盖：{out}；明确需要覆盖时加 --force")
    if args.json:
        print(json.dumps({"ok": True, "data": {**stats}}, ensure_ascii=False))
        return

    print(doc)
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        temp = out.with_name(f".{out.name}.tmp-{os.getpid()}")
        try:
            temp.write_text(doc, encoding="utf-8")
            os.replace(temp, out)
        finally:
            temp.unlink(missing_ok=True)
        print(f"\n已写入 {out}")
    flagged = stats["n_missing_seed"] + stats["n_missing_cmd"]
    print(f"\n# {stats['n_runs']} 个 run｜seed 覆盖 {stats['n_seeded']}/{stats['n_runs']}｜"
          f"cmd 覆盖 {stats['n_runs'] - stats['n_missing_cmd']}/{stats['n_runs']}｜MISSING 提示 {flagged} 处")
    print("# 复现信息登记状态：not_verified——未执行复现验证（见文档「复现信息登记状态」段）")


if __name__ == "__main__":
    main()
