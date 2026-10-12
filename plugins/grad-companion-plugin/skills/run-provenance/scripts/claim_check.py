# /// script
# requires-python = ">=3.12"
# ///
"""Mechanical claim checks (run-provenance). Check, do not adjudicate: output evidence and a checklist, not a conclusion.

Default (ledger self-check): calculate evidence for each claim, from strictest to broadest, and stop at the first match:
  run_missing → pending → metric_missing → needs_review / value_mismatch → verified
evidence is derived and is not written back to claims.jsonl; --log appends results to .grad/claims_checks.jsonl.

verified threshold (F01/F02): only an actual numeric comparison with a clear match and runs under the same comparison setup
(same config snapshot or a user-declared experiment group) qualifies. Multiple/no numbers, unit ambiguity, or incomparable
configurations remain needs_review; preserve existing values and reasons for human review.

--draft <path>: also extract numbers from the draft (tex/md) for **candidate matching**:
  found / suspected_drift (last-digit difference, e.g. paper says 71.2, mean is 71.1) / unbacked_candidates
  (numbers near tables, ±, or percent signs with no supporting claim; candidate list for human screening).
  Draft lookup matches number occurrences across the full text. A number appearing somewhere in the draft
  does not prove a sentence is correct and does not mean “this claim was verified in the draft.”

Finding mismatch/missing is not an execution failure (ok: true; findings are data); only runtime errors return ok: false.

With --json, stdout prints {"ok": true, "data": {...}} or {"ok": false, ...}.
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
from run_grouping import group_label, same_setting_runs  # Share comparability rules with table_gen.

if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")
SUPPORT_VALUES = {"unreviewed", "supported", "partial", "refuted"}
CAVEATS_PATH = Path(__file__).resolve().parent.parent / "references" / "benchmark-caveats.md"


def load_benchmark_caveats() -> dict[str, str]:
    """Extract keyword -> primary source + short defect summary from the living-document table.
    On parse failure, return an empty table (report unavailable but do not block checks)."""
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
            # Split keyword cells on slash and whitespace (e.g. “TAU-bench / tau-bench”),
            # then match each atom separately so multiple aliases do not prevent a hit.
            for atom in re.split(r"[/\s]+", keyword):
                atom = atom.strip().casefold()
                if atom and atom not in ("Benchmark keyword", "benchmark"):
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
            die("BAD_LEDGER", f"{path} line {no} is not valid JSON: {exc}")
        if not isinstance(row, dict):
            die("BAD_LEDGER", f"{path} line {no} must be a JSON object")
        rows.append(row)
    return rows


def resolve_claims(rows: list[dict]) -> list[dict]:
    """Use the last row for each claim_id as current, preserving first-seen order; rows without claim_id are separate legacy claims."""
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
    """Detect and report possible key spelling drift; never merge original keys automatically (same rule as table_gen).

    Report a possible match on normalized equality, edit distance <= 1 (one-character insertion/deletion/substitution),
    or SequenceMatcher similarity >= 0.94 (compound change for long keys).
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
    """Edit distance <= 1: equality after one-character insertion/deletion/substitution."""
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) <= 1
    if len(a) > len(b):
        a, b = b, a  # Ensure b is one character longer; deleting one character from b yields a.
    i = 0
    while i < len(a) and a[i] == b[i]:
        i += 1
    return a[i:] == b[i + 1:]


def check_claim_value(claim_text: str, mean: float | None) -> tuple[str, str | None, str]:
    """Return (value_check display text, claim number, mechanical status: verified/mismatch/needs_review).

    A match requires exactly one number in the claim and a clear comparison with the mean (try raw value or x100).
    Multiple/no numbers or ambiguous units stay needs_review; do not upgrade them, and retain the reason for review.
    """
    nums = NUMBER_RE.findall(claim_text)
    if len(nums) != 1:
        reason = (f"claim_text contains {len(nums)} numbers; cannot identify which refers to this metric" if nums
                  else "claim_text contains no number to compare")
        return f"needs_review ({reason}; numeric check required)", None, "needs_review"
    if mean is None:
        return "needs_review (no usable run values)", None, "needs_review"
    declared_raw = nums[0]
    declared = float(declared_raw)
    decimals = len(declared_raw.split(".")[1]) if "." in declared_raw else 0
    candidates = [mean, mean * 100] if mean != 0 else [mean]  # At mean=0, both units are identical; do not report ambiguity.
    matched = [c for c in candidates if abs(round(c, decimals) - declared) < 1e-9]
    if len(matched) == 1:
        return "matched", declared_raw, "verified"
    if len(matched) > 1:
        return ("needs_review (ambiguous units: both raw value and x100 match; no unit inference was made)",
                declared_raw, "needs_review")
    return "mismatch", declared_raw, "mismatch"


def classify_claim(entry: dict, runs_dir: Path, include_failed: bool,
                   caveats: dict[str, str]) -> tuple[dict, set[float], set[float]]:
    """Return (claim output, primary candidate, all candidates). Primary renders mean (used for found);
    secondary renders std (used only for matched_candidates and drift)."""
    row, legacy = entry["row"], entry["legacy"]
    run_ids = [str(r) for r in (row.get("run_ids") or [])]
    metric_path = row.get("metric_path")
    claim_text = str(row.get("claim_text", ""))
    if not claim_text.strip():
        warnings: list[str] = ["claim_text is empty"]
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
    settings_by_run: dict[str, dict] = {}  # Group comparison settings (experiment_group/config snapshot).

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
                warnings.append(f"Could not parse meta.json for run {rid}")
        metrics: dict = {}
        metrics_f = run_dir / "metrics.json"
        if metrics_f.is_file():
            try:
                loaded = json.loads(metrics_f.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    metrics = loaded
                else:
                    warnings.append(f"metrics.json for run {rid} is not a JSON object")
            except (OSError, json.JSONDecodeError):
                warnings.append(f"Could not parse metrics.json for run {rid}")
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
        warnings.append(f"Bound runs use mixed methods: {sorted(methods)} (they will be averaged; review this)")
    if len(benchmarks) > 1:
        warnings.append(f"Bound runs use mixed benchmarks: {sorted(benchmarks)} (they will be averaged; review this)")

    values: list[float] = []
    used_rids: list[str] = []  # Runs actually included in the mean; comparability applies to these only.
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
        warnings.append("This row is missing metric_path")
    elif placeholder_runs:
        evidence = "pending"  # Intentional state: run registered as a placeholder; no result yet.
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
            # No comparable values: all runs are pending or failed runs were excluded; fail closed, never verified.
            evidence = "pending"
            if excluded_running and not excluded_failed:
                warnings.append("All bound runs are still running placeholders (no results); there are no values to check")
            else:
                warnings.append("All bound failed/running runs were excluded; there are no values to check "
                                "(include failed runs with --include-failed; check running runs after results are added)")
        else:
            if excluded_failed:
                warnings.append(f"Failed runs excluded from the mean: {excluded_failed} (include with --include-failed)")
            if excluded_running:
                warnings.append(f"Running placeholder runs excluded from the mean: {excluded_running} (no results; not included in statistics)")
            mean = statistics.fmean(values)
            if len(values) >= 2:
                std = statistics.stdev(values)  # Sample standard deviation, ddof=1, consistent with table_gen.
            value_check, claim_number, value_status = check_claim_value(claim_text, mean)
            # F02: runs must share a comparison setup (same config snapshot or explicit experiment group) to be comparable.
            # Mixed settings cannot produce a verified mean; leave needs_review for a person (same rule as table_gen).
            buckets = same_setting_runs(
                [settings_by_run[rid] for rid in used_rids if rid in settings_by_run])
            comparable = len(buckets) <= 1
            if value_status == "verified" and not comparable:
                value_status = "needs_review"
                value_check = ("needs_review (bound runs use different comparison settings (method/benchmark/config), "
                               "so the mean has no comparison basis: "
                               + "；".join(group_label(k, v)
                                          for k, v in sorted(buckets.items(), key=lambda i: str(i[0]))) + "）")
                warnings.append("Bound runs are not comparable (different method/benchmark/config snapshots or missing config). "
                                "Explicit experiment groups cannot cross method/benchmark boundaries; after review, fix the bindings "
                                "or regroup with run_register.py --experiment-group")
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
        support = "unreviewed"  # Do not treat a legacy executor-written status as a human judgment.
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
    """Render draft-check candidates: mean and std at x1/x100, with one to three decimal places."""
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
            # Report one nearest candidate per draft number so one drift does not inflate summary counts.
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
                          "match_scope": "Full-text numeric candidate match: this only means the value occurs somewhere in the draft; "
                                         "it does not prove a sentence is correct or verify the claim."}
    unbacked: list[dict] = []
    for n in draft_numbers:
        if not n["context"]:
            continue
        if any(abs(n["value"] - c) < 1e-9 for c in all_candidates):
            continue
        if n["decimals"] == 0 and float(n["value"]).is_integer() and 1900 <= n["value"] <= 2100:
            continue  # Year.
        unbacked.append({"value": n["value"], "context": n["context"], "line": n["line"]})
    return unbacked


def main() -> None:
    ap = argparse.ArgumentParser(description="Mechanical claim checks (check, do not adjudicate)")
    ap.add_argument("--repo", default=".", help="Project root (claims and runs are under .grad/)")
    ap.add_argument("--draft", default="", help="Draft path (tex/md); also check numeric candidates when supplied")
    ap.add_argument("--include-failed", action="store_true",
                    help="Include failed runs with numeric metrics in the mean (excluded by default, like table_gen)")
    ap.add_argument("--log", action="store_true", help="Append results to .grad/claims_checks.jsonl")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    grad = repo / ".grad"
    claims_path = grad / "claims.jsonl"
    runs_dir = grad / "runs"
    if not claims_path.is_file():
        die("NO_CLAIMS", f"{claims_path} does not exist; register claims with claim_register.py add first")

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
            die("NO_FILE", f"Draft does not exist: {draft_path}; refusing partial checks")
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
        "note": "Mechanical check, not a review verdict. needs_review and unbacked/suspected_drift require human confirmation; "
                "draft.found is only a full-text numeric candidate match, not verification of the claim in the draft.",
        "claims": claims_out,
        "unbacked_candidates": unbacked,
        "summary": summary,
    }
    if args.json:
        print(json.dumps({"ok": True, "data": data}, ensure_ascii=False))
        return
    s = summary
    print(f"# Checked {s['claims']} claims: verified {s['verified']} | value_mismatch {s['value_mismatch']} "
          f"| needs_review {s['needs_review']} "
          f"| metric_missing {s['metric_missing']} | pending {s['pending']} | run_missing {s['run_missing']}")
    for c in claims_out:
        text = c["claim_text"][:36] + ("…" if len(c["claim_text"]) > 36 else "")
        suffix = ""
        if "draft" in c:
            suffix = (f" | draft candidate: {'found' if c['draft']['found'] else 'not found'}"
                      " (full-text numeric match; does not prove the claim)")
            if c["draft"]["suspected_drift"]:
                suffix += f", suspected_drift ×{len(c['draft']['suspected_drift'])}"
        print(f"  {c['claim_id']:<12} evidence={c['evidence']:<15} support={c['support']:<11}"
              f"{' [legacy]' if c['legacy'] else ''} {text}{suffix}")
    for item in unbacked:
        print(f"  ⚠ unbacked candidate: {item['value']} (line {item['line']}, {'+'.join(item['context'])}) — human review required")
    for c in claims_out:
        for warning in c["detail"]["warnings"]:
            print(f"  ⚠ {c['claim_id']}: {warning}")


if __name__ == "__main__":
    main()
