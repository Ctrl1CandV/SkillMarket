# /// script
# requires-python = ">=3.12"
# ///
"""claim 机械核对（run-provenance）。只核对，不宣判：输出是证据与清单，不是结论。

默认（台账自检）：对每条 claim 现算 evidence，从严到宽命中即止：
  run_missing → pending → metric_missing → needs_review / value_mismatch → verified
evidence 是派生属性，不写回 claims.jsonl；--log 把结果追加到 .grad/claims_checks.jsonl。

verified 的门槛（F01/F02）：只有实际完成数值比对且明确匹配、且绑定 run 属同一比较设置
（同配置快照或用户显式声明同一实验组）才 verified。多数字、无数字、量纲歧义、
配置不可比一律 needs_review——保留已有数值与原因供人查看，不升级为已验证。

--draft <路径>：额外提取草稿（tex/md）数字做**候选匹配**回查：
  found / suspected_drift（末位级差异，如论文写 71.2、均值 71.1）/ unbacked_candidates
  （表格、±、百分号上下文里无 claim 支撑的数字——候选清单，需人工筛）
  草稿回查按全文数字出现做匹配，只是「数字候选匹配」——同一数字出现在草稿某处
  不足以证明某句话正确，不构成「该 claim 已在草稿中验证」。

发现 mismatch / missing 不是失败（ok: true，发现即数据）；只有运行错误才 ok: false。

输出契约：--json 时 stdout 打印 {"ok": true, "data": {...}} 或 {"ok": false, ...}。
"""

from __future__ import annotations

import argparse
from difflib import SequenceMatcher
import json
import math
import re
import statistics
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_grouping import group_label, same_setting_runs  # 与 table_gen 共用同一套可比性规则

if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")
SUPPORT_VALUES = {"unreviewed", "supported", "partial", "refuted"}
CAVEATS_PATH = Path(__file__).resolve().parent.parent / "references" / "benchmark-caveats.md"


def load_benchmark_caveats() -> dict[str, str]:
    """从活文档条目表提取 (关键词 -> 一手来源+缺陷短摘要)。解析失败返回空表（提示不可用，不阻断核对）。"""
    if not CAVEATS_PATH.is_file():
        return {}
    try:
        text = CAVEATS_PATH.read_text(encoding="utf-8")
    except OSError:
        return {}
    table: dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r"^\|([^|]+)\|\s*(arXiv:\d{4}\.\d{4,5})[^|]*\|\s*([^|]+?)\s*\|", line)
        if m:
            keyword = m.group(1).strip()
            entry_id = f"{keyword}（{m.group(2)}）"
            summary = re.sub(r"\s+", " ", m.group(3)).strip()
            # 关键词单元格按 / 与空格切分为原子（「TAU-bench / τ-bench」→ tau-bench、τ-bench），
            # 每个原子独立参与子串匹配，避免多别名合写让条目永远无法命中
            for atom in re.split(r"[/\s]+", keyword):
                atom = atom.strip().casefold()
                if atom and atom not in ("关键词", "benchmark"):
                    table[atom] = f"{entry_id}：{summary}"
    return table


def die(error: str, detail: str, **extra) -> None:
    print(json.dumps({"ok": False, "error": error, "detail": detail, **extra}, ensure_ascii=False))
    sys.exit(1)


def now_local() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_rows(path: Path) -> list[dict]:
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


def resolve_claims(rows: list[dict]) -> list[dict]:
    """同 claim_id 取最后一行为当前（位置按首次出现）；无 claim_id 的行为独立 legacy claim。"""
    latest: dict[str, dict] = {}
    first_pos: dict[str, int] = {}
    legacy_rows: dict[int, dict] = {}
    for idx, row in enumerate(rows):
        cid = row.get("claim_id")
        if isinstance(cid, str) and cid:
            first_pos.setdefault(cid, idx)
            latest[cid] = row
        else:
            legacy_rows[idx] = row
    marks = ([(pos, cid, False) for cid, pos in first_pos.items()]
             + [(idx, f"legacy-{idx}", True) for idx in legacy_rows])
    marks.sort(key=lambda item: item[0])
    return [{"claim_id": cid, "legacy": legacy,
             "row": legacy_rows[pos] if legacy else latest[cid]}
            for pos, cid, legacy in marks]


def drift_hints(available_keys: list[str], metric_path: str) -> list[str]:
    """只发现疑似拼写漂移并提示；原始 key 永远不自动合并（与 table_gen 同一纪律）。

    判定三选一命中即提示：归一化相等 / 编辑距离 ≤1（单字符插入、删除、替换）/
    SequenceMatcher 相似度 ≥0.94（长键的复合变形）。
    """
    def norm(key: str) -> str:
        return re.sub(r"[\s\.,;:!?，。；：]+$", "", key.strip().casefold())

    target = norm(metric_path)
    hints: list[str] = []
    for key in available_keys:
        nk = norm(key)
        if nk == target or _within_one_edit(nk, target) or (
                target and nk and SequenceMatcher(None, target, nk).ratio() >= 0.94):
            hints.append(key)
    return hints


def _within_one_edit(a: str, b: str) -> bool:
    """编辑距离 ≤1：单字符插入 / 删除 / 替换内相等。"""
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) <= 1
    if len(a) > len(b):
        a, b = b, a  # 保证 b 比 a 恰长 1：等价于「b 删去一个字符后恰等于 a」
    i = 0
    while i < len(a) and a[i] == b[i]:
        i += 1
    return a[i:] == b[i + 1:]


def check_claim_value(claim_text: str, mean: float | None) -> tuple[str, str | None, str]:
    """返回 (value_check 展示文本, claim 声明数字, 机械状态 verified/mismatch/needs_review)。

    只有 claim 恰含一个数字、且与均值完成明确数值比对（量纲调和：原值 / ×100）才算匹配。
    多数字、无数字、量纲歧义都是 needs_review：不能升级为 verified，保留原因供人查看。
    """
    nums = NUMBER_RE.findall(claim_text)
    if len(nums) != 1:
        reason = (f"claim_text 含 {len(nums)} 个数字，无法确定哪个数字对应本指标" if nums
                  else "claim_text 不含数字，无数值可比对")
        return f"needs_review（{reason}，数值需人工核对）", None, "needs_review"
    if mean is None:
        return "needs_review（无可用的 run 数值）", None, "needs_review"
    declared_raw = nums[0]
    declared = float(declared_raw)
    decimals = len(declared_raw.split(".")[1]) if "." in declared_raw else 0
    candidates = [mean, mean * 100] if mean != 0 else [mean]  # mean=0 时两种量纲同值，不报 ambiguous
    matched = [c for c in candidates if abs(round(c, decimals) - declared) < 1e-9]
    if len(matched) == 1:
        return "matched", declared_raw, "verified"
    if len(matched) > 1:
        return ("needs_review（量纲歧义：原值与 ×100 两种量纲都吻合，未做单位推理）",
                declared_raw, "needs_review")
    return "mismatch", declared_raw, "mismatch"


def classify_claim(entry: dict, runs_dir: Path, include_failed: bool,
                   caveats: dict[str, str]) -> tuple[dict, set[float], set[float]]:
    """返回 (claim 输出, 主候选, 全部候选)。主候选 = mean 渲染（found 以它为准）；
    次候选 = std 渲染（只在 matched_candidates 与 drift 里参考）。"""
    row, legacy = entry["row"], entry["legacy"]
    run_ids = [str(r) for r in (row.get("run_ids") or [])]
    metric_path = row.get("metric_path")
    claim_text = str(row.get("claim_text", ""))
    if not claim_text.strip():
        warnings: list[str] = ["claim_text 为空"]
    else:
        warnings: list[str] = []
    runs_detail: list[dict] = []
    missing_runs: list[str] = []
    placeholder_runs: list[str] = []
    metric_missing_runs: list[str] = []
    non_numeric_runs: list[str] = []
    hints: list[str] = []
    methods, benchmarks = set(), set()
    metrics_by_run: dict[str, dict] = {}
    status_by_run: dict[str, str] = {}
    settings_by_run: dict[str, dict] = {}  # 比较设置归组用（experiment_group / config 快照）

    for rid in run_ids:
        run_dir = runs_dir / rid
        if not run_dir.is_dir():
            missing_runs.append(rid)
            runs_detail.append({"run_id": rid, "found": False})
            continue
        meta: dict = {}
        meta_f = run_dir / "meta.json"
        if meta_f.is_file():
            try:
                loaded = json.loads(meta_f.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    meta = loaded
            except (OSError, json.JSONDecodeError):
                warnings.append(f"run {rid} 的 meta.json 不可解析")
        metrics: dict = {}
        metrics_f = run_dir / "metrics.json"
        if metrics_f.is_file():
            try:
                loaded = json.loads(metrics_f.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    metrics = loaded
                else:
                    warnings.append(f"run {rid} 的 metrics.json 不是 JSON 对象")
            except (OSError, json.JSONDecodeError):
                warnings.append(f"run {rid} 的 metrics.json 不可解析")
        status = str(meta.get("status") or "success")
        status_by_run[rid] = status
        settings_by_run[rid] = {
            "run_id": rid,
            "method": meta.get("method"),
            "benchmark": meta.get("benchmark"),
            "experiment_group": meta.get("experiment_group"),
            "config": meta.get("config") if isinstance(meta.get("config"), dict) else None,
        }
        if isinstance(meta.get("method"), str):
            methods.add(meta["method"])
        if isinstance(meta.get("benchmark"), str):
            benchmarks.add(meta["benchmark"])
        if not metrics:
            placeholder_runs.append(rid)
        metrics_by_run[rid] = metrics
        runs_detail.append({"run_id": rid, "found": True, "status": status})
    if len(methods) > 1:
        warnings.append(f"绑定的 run 混用 method：{sorted(methods)}（它们将被求均值，请确认）")
    if len(benchmarks) > 1:
        warnings.append(f"绑定的 run 混用 benchmark：{sorted(benchmarks)}（它们将被求均值，请确认）")

    values: list[float] = []
    used_rids: list[str] = []  # 实际进入均值的 run（可比性只对它们判定；被排除的 running/failed 不拖组）
    excluded_failed: list[str] = []
    excluded_running: list[str] = []
    mean: float | None = None
    std: float | None = None
    comparable: bool | None = None
    value_check = "skipped"
    claim_number: str | None = None

    if missing_runs or not run_ids:
        evidence = "run_missing"
    elif not metric_path:
        evidence = "metric_missing"
        warnings.append("该行缺 metric_path")
    elif placeholder_runs:
        evidence = "pending"  # 设计内状态：run 先登记占位、结果未出
    else:
        assert metric_path is not None
        for rid in run_ids:
            metrics = metrics_by_run.get(rid) or {}
            if metric_path not in metrics:
                metric_missing_runs.append(rid)
                hints.extend(drift_hints(sorted(metrics), metric_path))
                continue
            value = metrics[metric_path]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                non_numeric_runs.append(rid)
                continue
            if status_by_run.get(rid) == "running":
                excluded_running.append(rid)
                continue
            if status_by_run.get(rid) == "failed" and not include_failed:
                excluded_failed.append(rid)
                continue
            values.append(float(value))
            used_rids.append(rid)
        if metric_missing_runs or non_numeric_runs:
            evidence = "metric_missing"
        elif not values:
            # 没有任何可比数字：全部 run 为 running 占位，或 failed 全被排除——fail-closed 不给 verified
            evidence = "pending"
            if excluded_running and not excluded_failed:
                warnings.append("全部绑定 run 仍为 running 占位（结果未出），无可核对的数值")
            else:
                warnings.append("全部绑定 run 均为 failed/running 被排除，无可核对的数值"
                                "（failed 可用 --include-failed 纳入；running 等补录后再核对）")
        else:
            if excluded_failed:
                warnings.append(f"已从均值排除 failed run：{excluded_failed}（--include-failed 可纳入）")
            if excluded_running:
                warnings.append(f"已从均值排除 running 占位 run：{excluded_running}（结果未出，不参与统计）")
            mean = statistics.fmean(values)
            if len(values) >= 2:
                std = statistics.stdev(values)  # 样本标准差 ddof=1，与 table_gen 一致
            value_check, claim_number, value_status = check_claim_value(claim_text, mean)
            # F02：参与统计的 run 必须属同一比较设置（同配置快照或同一显式实验组）才有均值可比性；
            # 混用设置时不给已验证均值，needs_review 交人确认（与 table_gen 同一套规则）
            buckets = same_setting_runs(
                [settings_by_run[rid] for rid in used_rids if rid in settings_by_run])
            comparable = len(buckets) <= 1
            if value_status == "verified" and not comparable:
                value_status = "needs_review"
                value_check = ("needs_review（绑定的 run 分属不同比较设置（method/benchmark/配置），"
                               "均值无对比基础："
                               + "；".join(group_label(k, v)
                                          for k, v in sorted(buckets.items(), key=lambda i: str(i[0]))) + "）")
                warnings.append("绑定 run 不可比（不同 method/benchmark/配置快照/缺配置）：显式实验组不能跨 "
                                "method/benchmark 边界；确认后修正绑定或用 run_register.py --experiment-group 重新分组")
            evidence = {"verified": "verified", "mismatch": "value_mismatch"}.get(value_status, "needs_review")
    detail = {
        "runs": runs_detail,
        "missing_runs": missing_runs,
        "placeholder_runs": placeholder_runs,
        "metric_missing_runs": metric_missing_runs,
        "non_numeric_runs": non_numeric_runs,
        "drift_hints": sorted(set(hints)),
        "values": values,
        "mean": mean,
        "std": std,
        "n": len(values),
        "excluded_failed": excluded_failed,
        "excluded_running": excluded_running,
        "comparable_settings": comparable,
        "value_check": value_check,
        "warnings": warnings,
    }
    if claim_number is not None:
        detail["claim_number"] = claim_number
        if mean is not None:
            detail["mean_x100"] = mean * 100

    support = row.get("support") if not legacy else None
    if support not in SUPPORT_VALUES:
        support = "unreviewed"  # legacy 行的旧 status 是执行者写的，不继承为人的判定
    benchmark_caveats = [
        entry for name, entry in caveats.items() if any(name in b.casefold() for b in benchmarks)
    ]
    out = {
        "claim_id": entry["claim_id"],
        "claim_text": claim_text,
        "legacy": legacy,
        "evidence": evidence,
        "support": support,
        "support_by": row.get("support_by") if not legacy else None,
        "benchmark_caveats": benchmark_caveats,
        "detail": detail,
    }
    primary, all_candidates = candidate_renderings(mean, std)
    return out, primary, all_candidates


def candidate_renderings(mean: float | None, std: float | None) -> tuple[set[float], set[float]]:
    """草稿回查的候选渲染：mean 与 std 各自 ×1 / ×100、1-3 位小数。"""
    if mean is None:
        return set(), set()
    primary = {round(value, digits) for value in (mean, mean * 100) for digits in (1, 2, 3)}
    if std is None:
        return primary, primary
    secondary = {round(value, digits) for value in (std, std * 100) for digits in (1, 2, 3)}
    return primary, primary | secondary


def extract_draft_numbers(text: str) -> list[dict]:
    numbers: list[dict] = []
    in_tex_table = False
    for lineno, line in enumerate(text.splitlines(), 1):
        if re.search(r"\\begin\{table\*?\}", line):
            in_tex_table = True
        table_line = in_tex_table or "|" in line
        if re.search(r"\\end\{table\*?\}", line):
            in_tex_table = False
        for m in NUMBER_RE.finditer(line):
            raw = m.group()
            before = line[max(0, m.start() - 6):m.start()]
            after = line[m.end():m.end() + 6]
            flags: list[str] = []
            if re.match(r"\s*\\?%", after):
                flags.append("percent")
            if "±" in before + after or "\\pm" in before + after:
                flags.append("pm")
            if table_line:
                flags.append("table")
            numbers.append({
                "value": float(raw),
                "decimals": len(raw.split(".")[1]) if "." in raw else 0,
                "line": lineno,
                "context": flags,
            })
    return numbers


def match_draft(claims_out: list[dict], primaries: list[set[float]],
                all_candidates_per_claim: list[set[float]],
                draft_numbers: list[dict]) -> list[dict]:
    all_candidates: set[float] = set()
    for candidates in all_candidates_per_claim:
        all_candidates |= candidates
    globally_matched = {n["value"] for n in draft_numbers
                        if any(abs(n["value"] - c) < 1e-9 for c in all_candidates)}
    for claim, primary, candidates in zip(claims_out, primaries, all_candidates_per_claim):
        if not candidates:
            continue
        matched = sorted({n["value"] for n in draft_numbers
                          if any(abs(n["value"] - c) < 1e-9 for c in candidates)})
        found = any(abs(n["value"] - c) < 1e-9 for n in draft_numbers for c in primary)
        drifts: list[dict] = []
        if not found:
            # 同一草稿数字只报一条（取最近候选），避免一次漂移在 summary 里虚增计数
            for n in draft_numbers:
                if n["value"] in globally_matched:
                    continue
                hits = [(abs(n["value"] - expected), expected)
                        for expected in sorted(candidates)
                        if 0 < abs(n["value"] - expected) <= 10 ** (-n["decimals"]) + 1e-9]
                if hits:
                    _, expected = min(hits)
                    drifts.append({"expected": expected, "draft": n["value"], "line": n["line"]})
        claim["draft"] = {"found": found, "matched_candidates": matched,
                          "suspected_drift": drifts,
                          "match_scope": "全文数字候选匹配：只能说明该数值出现在草稿某处，"
                                         "不足以证明某句话正确，不构成 claim 已核验"}
    unbacked: list[dict] = []
    for n in draft_numbers:
        if not n["context"]:
            continue
        if any(abs(n["value"] - c) < 1e-9 for c in all_candidates):
            continue
        if n["decimals"] == 0 and float(n["value"]).is_integer() and 1900 <= n["value"] <= 2100:
            continue  # 年份
        unbacked.append({"value": n["value"], "context": n["context"], "line": n["line"]})
    return unbacked


def main() -> None:
    ap = argparse.ArgumentParser(description="claim 机械核对（只核对，不宣判）")
    ap.add_argument("--repo", default=".", help="项目根（claims 与 runs 在其 .grad/ 下）")
    ap.add_argument("--draft", default="", help="草稿路径（tex/md）；给了就额外做数字回查")
    ap.add_argument("--include-failed", action="store_true",
                    help="均值纳入带数值指标的 failed run（默认排除，与 table_gen 语义一致）")
    ap.add_argument("--log", action="store_true", help="把本次结果追加到 .grad/claims_checks.jsonl")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    grad = repo / ".grad"
    claims_path = grad / "claims.jsonl"
    runs_dir = grad / "runs"
    if not claims_path.is_file():
        die("NO_CLAIMS", f"{claims_path} 不存在；先用 claim_register.py add 登记 claim")

    entries = resolve_claims(load_rows(claims_path))
    claims_out: list[dict] = []
    primaries: list[set[float]] = []
    all_candidates_per_claim: list[set[float]] = []
    caveats = load_benchmark_caveats()
    for entry in entries:
        out, primary, candidates = classify_claim(entry, runs_dir, args.include_failed, caveats)
        claims_out.append(out)
        primaries.append(primary)
        all_candidates_per_claim.append(candidates)

    unbacked: list[dict] = []
    if args.draft:
        draft_path = Path(args.draft)
        if not draft_path.is_file():
            die("NO_FILE", f"草稿不存在：{draft_path}；不降级到部分核对")
        draft_numbers = extract_draft_numbers(draft_path.read_text(encoding="utf-8", errors="replace"))
        unbacked = match_draft(claims_out, primaries, all_candidates_per_claim, draft_numbers)

    summary = {
        "claims": len(claims_out),
        "verified": sum(1 for c in claims_out if c["evidence"] == "verified"),
        "value_mismatch": sum(1 for c in claims_out if c["evidence"] == "value_mismatch"),
        "needs_review": sum(1 for c in claims_out if c["evidence"] == "needs_review"),
        "metric_missing": sum(1 for c in claims_out if c["evidence"] == "metric_missing"),
        "pending": sum(1 for c in claims_out if c["evidence"] == "pending"),
        "run_missing": sum(1 for c in claims_out if c["evidence"] == "run_missing"),
        "found": sum(1 for c in claims_out if c.get("draft", {}).get("found")),
        "not_found": sum(1 for c in claims_out if c.get("draft", {}).get("found") is False),
        "suspected_drift": sum(len(c.get("draft", {}).get("suspected_drift", [])) for c in claims_out),
        "unbacked_candidates": len(unbacked),
    }
    if args.log:
        log_path = grad / "claims_checks.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps({
                "checked_at": now_local(),
                "mode": "draft" if args.draft else "ledger",
                "draft_path": args.draft or None,
                "include_failed": bool(args.include_failed),
                "summary": summary,
                "results": [{"claim_id": c["claim_id"], "evidence": c["evidence"],
                             "support": c["support"]} for c in claims_out],
            }, ensure_ascii=False) + "\n")

    data = {
        "mechanical_check": True,
        "note": "机械核对结果，不是审稿意见；needs_review 与 unbacked/suspected_drift 都需人工确认；"
                "draft.found 只是全文数字候选匹配，不等于该论断已在草稿中验证",
        "claims": claims_out,
        "unbacked_candidates": unbacked,
        "summary": summary,
    }
    if args.json:
        print(json.dumps({"ok": True, "data": data}, ensure_ascii=False))
        return
    s = summary
    print(f"# claim 核对 {s['claims']} 条：verified {s['verified']} | value_mismatch {s['value_mismatch']} "
          f"| needs_review {s['needs_review']} "
          f"| metric_missing {s['metric_missing']} | pending {s['pending']} | run_missing {s['run_missing']}")
    for c in claims_out:
        text = c["claim_text"][:36] + ("…" if len(c["claim_text"]) > 36 else "")
        suffix = ""
        if "draft" in c:
            suffix = (f" | draft候选: {'出现' if c['draft']['found'] else '未出现'}"
                      "（全文数字匹配，不证明论断正确）")
            if c["draft"]["suspected_drift"]:
                suffix += f", suspected_drift ×{len(c['draft']['suspected_drift'])}"
        print(f"  {c['claim_id']:<12} evidence={c['evidence']:<15} support={c['support']:<11}"
              f"{' [legacy]' if c['legacy'] else ''} {text}{suffix}")
    for item in unbacked:
        print(f"  ⚠ unbacked 候选：{item['value']}（line {item['line']}，{'+'.join(item['context'])}）——需人工确认")
    for c in claims_out:
        for warning in c["detail"]["warnings"]:
            print(f"  ⚠ {c['claim_id']}: {warning}")


if __name__ == "__main__":
    main()
