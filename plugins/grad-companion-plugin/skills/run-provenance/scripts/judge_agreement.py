# /// script
# requires-python = ">=3.12"
# ///
"""Check agreement between judges (run-provenance). Pure arithmetic: accept two sets of scores and report agreement rate, Cohen kappa, and a confusion matrix.

This addresses the first ARR method weakness, "unvalidated LLM-as-judge": turn agreement between a judge and a human (or two judges)
into reportable evidence. The code does not decide what kappa value is good enough; that threshold is a methodological judgment.
See references/judge-protocol.md for the protocol and research anchors; a person interprets the result.

Matching rule: pair the intersection of samples present on both sides by id-key. Count excluded samples without imputing or guessing.
Agreement requires exact equality; no numeric tolerance is applied (if tolerance is needed, declare it in the protocol and review it).

Exit-code semantics: an undefined kappa is not a failure; return ok: true with kappa=null and degenerate_reason, since the degeneracy is itself data.

Output contract: with --json, stdout prints {"ok": true, "data": {...}} or {"ok": false, ...}.
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
    """Accept a JSON array [{...}] or a single-key wrapper {label: [...]}; return an (id -> value) mapping and input diagnostics."""
    path = Path(path_text)
    if not path.is_file():
        die("NO_FILE", f"Score file not found: {path}")
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        die("BAD_SCORES", f"Could not parse {path}: {exc}")
    if isinstance(loaded, dict):
        arrays = [v for v in loaded.values() if isinstance(v, list)]
        if len(arrays) == 1:
            loaded = arrays[0]
        else:
            die("BAD_SCORES", f"{path} is an object without exactly one array field; pass the array directly")
    if not isinstance(loaded, list):
        die("BAD_SCORES", f"{path} must be an array of score objects")
    return {"items": loaded}


def extract_pairs(items: list, side: str, id_key: str, value_key: str,
                  source: Path) -> tuple[dict, list[str]]:
    scores: dict = {}
    problems: list[str] = []
    for no, item in enumerate(items, 1):
        if not isinstance(item, dict):
            problems.append(f"{source.name}[{no}]: must be an object")
            continue
        if id_key not in item or value_key not in item:
            problems.append(f"{source.name}[{no}]: missing {id_key!r} or {value_key!r}")
            continue
        rid, value = item[id_key], item[value_key]
        key = str(rid)
        if key in scores:
            problems.append(f"{source.name}[{no}]: duplicate id {key!r}; keeping the first and dropping later rows")
            continue
        scores[key] = value
    return scores, problems


def cohens_kappa(pairs: list[tuple]) -> tuple[float | None, str | None]:
    """Cohen kappa = (po - pe) / (1 - pe). Return (None, reason) when the metric is degenerate."""
    n = len(pairs)
    if n == 0:
        return None, "no paired samples"
    labels = sorted({a for a, _ in pairs} | {b for _, b in pairs})
    obs_a = Counter(a for a, _ in pairs)
    obs_b = Counter(b for _, b in pairs)
    if any(obs_a[label] == n or obs_b[label] == n for label in labels):
        # When either or both marginal distributions are constant, pe=1 and the denominator is zero.
        return None, "both marginal distributions are degenerate (all ratings are identical); kappa is undefined"
    po = sum(a == b for a, b in pairs) / n
    pe = sum((obs_a[label] / n) * (obs_b[label] / n) for label in labels)
    denom = 1.0 - pe
    if abs(denom) < 1e-12:
        return None, "expected agreement pe≈1, so the kappa denominator is zero"
    return (po - pe) / denom, None


def main() -> None:
    ap = argparse.ArgumentParser(description="Check judge agreement (compute metrics only; do not decide whether they are good enough)")
    ap.add_argument("--a", required=True, help="JSON array file for rating set A (for example, human annotations)")
    ap.add_argument("--b", required=True, help="JSON array file for rating set B (for example, LLM-as-judge)")
    ap.add_argument("--id-key", default="id", help="Sample identifier field (default: id)")
    ap.add_argument("--value-key", default="value", help="Rating field (default: value)")
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
        "note": "A person decides what kappa value is good enough; see references/judge-protocol.md",
    }
    if args.json:
        print(json.dumps({"ok": True, "data": data}, ensure_ascii=False))
        return
    s = data
    head = "Paired {} (A only {}, B only {}, mismatched types excluded {})".format(s["n_paired"], s["n_excluded_a"], s["n_excluded_b"], s["n_type_mismatch_excluded"])

    if s["cohens_kappa"] is not None:
        print("# kappa={} | agreement rate {:.2%} | {}".format(s["cohens_kappa"], s["agreement_rate"], head))
    else:
        print("# kappa undefined ({}) | agreement rate {:.2%} | {}".format(s["degenerate_reason"], s["agreement_rate"], head))

    for row, cols in confusion.items():
        for col, count in cols.items():
            print(f"  {row} → {col}: {count}")


def _compatible(a, b) -> bool:
    """Only compare values of the same kind: string × string or number × number (bool is not numeric)."""
    def is_num(v):
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    return (isinstance(a, str) and isinstance(b, str)) or (is_num(a) and is_num(b))


if __name__ == "__main__":
    main()
