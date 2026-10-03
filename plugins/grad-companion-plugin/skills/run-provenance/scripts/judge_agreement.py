# /// script
# requires-python = ">=3.12"
# ///
"""judge 一致性验证（run-provenance）。纯算术：输入两组评分，输出一致率、Cohen's κ、混淆矩阵。

回答的是 ARR 方法缺陷首条「未经验证的 LLM-as-judge」：把 judge 与人工（或 judge 与 judge）
的评分一致性变成可报告的证据。**κ 多高算「够好」不在代码里判定**——阈值是方法论判断，
协议与学界锚点见 references/judge-protocol.md，结论由人下。

匹配规则：按 id-key 取两边都出现的样本求交集配对；被排除的样本只计数不插值（不猜）。
一致性判定为等值精确匹配，不做数值容差（要容差请在 protocol 文档里声明并由人复核）。

退出码语义：κ 不可计算不是失败——ok: true 且 kappa=null + degenerate_reason（发现即数据）。

输出契约：--json 时 stdout 打印 {"ok": true, "data": {...}} 或 {"ok": false, ...}。
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


def die(error: str, detail: str, **extra) -> None:
    print(json.dumps({"ok": False, "error": error, "detail": detail, **extra}, ensure_ascii=False))
    sys.exit(1)


def load_scores(path_text: str) -> dict:
    """接受 JSON 数组 [{...}] 或单键包装 {label: [...]}; 返回 (id -> value) 映射与读取信息。"""
    path = Path(path_text)
    if not path.is_file():
        die("NO_FILE", f"评分文件不存在：{path}")
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        die("BAD_SCORES", f"{path} 解析失败：{exc}")
    if isinstance(loaded, dict):
        arrays = [v for v in loaded.values() if isinstance(v, list)]
        if len(arrays) == 1:
            loaded = arrays[0]
        else:
            die("BAD_SCORES", f"{path} 是 JSON 对象但不含唯一的数组字段；请直接给数组")
    if not isinstance(loaded, list):
        die("BAD_SCORES", f"{path} 必须是评分对象数组")
    return {"items": loaded}


def extract_pairs(items: list, side: str, id_key: str, value_key: str,
                  source: Path) -> tuple[dict, list[str]]:
    scores: dict = {}
    problems: list[str] = []
    for no, item in enumerate(items, 1):
        if not isinstance(item, dict):
            problems.append(f"{source.name}[{no}]: 不是对象")
            continue
        if id_key not in item or value_key not in item:
            problems.append(f"{source.name}[{no}]: 缺 {id_key!r} 或 {value_key!r}")
            continue
        rid, value = item[id_key], item[value_key]
        key = str(rid)
        if key in scores:
            problems.append(f"{source.name}[{no}]: id {key!r} 重复，保留首个、丢弃后续")
            continue
        scores[key] = value
    return scores, problems


def cohens_kappa(pairs: list[tuple]) -> tuple[float | None, str | None]:
    """Cohen's κ = (po - pe) / (1 - pe)。退化时返回 (None, 原因)。"""
    n = len(pairs)
    if n == 0:
        return None, "无配对样本"
    labels = sorted({a for a, _ in pairs} | {b for _, b in pairs})
    obs_a = Counter(a for a, _ in pairs)
    obs_b = Counter(b for _, b in pairs)
    if any(obs_a[label] == n or obs_b[label] == n for label in labels):
        # 单边或双边边际完全退化时 pe=1、分母为 0
        return None, "边际分布完全退化（全部同分），κ 无定义"
    po = sum(a == b for a, b in pairs) / n
    pe = sum((obs_a[label] / n) * (obs_b[label] / n) for label in labels)
    denom = 1.0 - pe
    if abs(denom) < 1e-12:
        return None, "期望一致率 pe≈1，κ 分母为零"
    return (po - pe) / denom, None


def main() -> None:
    ap = argparse.ArgumentParser(description="judge 一致性验证（只算数，不下「够不够好」的结论）")
    ap.add_argument("--a", required=True, help="评分组 A 的 JSON 数组文件（如人工标注）")
    ap.add_argument("--b", required=True, help="评分组 B 的 JSON 数组文件（如 LLM-as-judge）")
    ap.add_argument("--id-key", default="id", help="样本标识字段名（默认 id）")
    ap.add_argument("--value-key", default="value", help="分值字段名（默认 value）")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    a_load, b_load = load_scores(args.a), load_scores(args.b)
    path_a, path_b = Path(args.a), Path(args.b)
    a_scores, a_problems = extract_pairs(a_load["items"], "A", args.id_key, args.value_key, path_a)
    b_scores, b_problems = extract_pairs(b_load["items"], "B", args.id_key, args.value_key, path_b)

    excluded_a = sorted(set(a_scores) - set(b_scores))
    excluded_b = sorted(set(b_scores) - set(a_scores))
    common = sorted(set(a_scores) & set(b_scores))
    pairs = [(a_scores[k], b_scores[k]) for k in common]
    mismatched_types = [k for k, (a, b) in zip(common, pairs) if not _compatible(a, b)]
    valid_pairs = [(a, b) for a, b in pairs if _compatible(a, b)]
    agreement = sum(a == b for a, b in valid_pairs)
    kappa, reason = cohens_kappa(valid_pairs)

    confusion: dict[str, dict[str, int]] = {}
    marginals_a: Counter = Counter()
    marginals_b: Counter = Counter()
    for a, b in valid_pairs:
        sa, sb = repr(a), repr(b)
        confusion.setdefault(sa, {})[sb] = confusion.setdefault(sa, {}).get(sb, 0) + 1
        marginals_a[sa] += 1
        marginals_b[sb] += 1

    data = {
        "n_paired": len(valid_pairs),
        "n_type_mismatch_excluded": len(mismatched_types),
        "type_mismatch_ids": mismatched_types,
        "n_excluded_a": len(excluded_a),
        "excluded_a": excluded_a,
        "n_excluded_b": len(excluded_b),
        "excluded_b": excluded_b,
        "agreement_rate": round(agreement / len(valid_pairs), 4) if valid_pairs else None,
        "cohens_kappa": round(kappa, 4) if kappa is not None else None,
        "degenerate_reason": reason,
        "confusion_matrix": confusion,
        "marginals": {"a": dict(marginals_a), "b": dict(marginals_b)},
        "parse_problems": {"a": a_problems, "b": b_problems},
        "note": "κ 多高算「够好」由人下结论，锚点见 references/judge-protocol.md",
    }
    if args.json:
        print(json.dumps({"ok": True, "data": data}, ensure_ascii=False))
        return
    s = data
    head = (f"配对 {s['n_paired']}（A 独有 {s['n_excluded_a']}，B 独有 {s['n_excluded_b']}，"
            f"类型不符排除 {s['n_type_mismatch_excluded']}）")
    if s["cohens_kappa"] is not None:
        print(f"# κ={s['cohens_kappa']} | 一致率 {s['agreement_rate']:.2%} | {head}")
    else:
        print(f"# κ 未定义（{s['degenerate_reason']}）| 一致率 "
              f"{f'{s["agreement_rate"]:.2%}' if s['agreement_rate'] is not None else 'N/A'} | {head}")
    for row, cols in confusion.items():
        for col, count in cols.items():
            print(f"  {row} → {col}: {count}")


def _compatible(a, b) -> bool:
    """同一可比类型才参与统计：字符串×字符串 或 数值×数值（bool 不算数值）。"""
    def is_num(v):
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    return (isinstance(a, str) and isinstance(b, str)) or (is_num(a) and is_num(b))


if __name__ == "__main__":
    main()
