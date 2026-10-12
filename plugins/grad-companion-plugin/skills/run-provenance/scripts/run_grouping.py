# /// script
# requires-python = ">=3.12"
# ///
"""Shared rules for run comparability groups and reproducibility metadata (internal to run-provenance).

table_gen / claim_check / claim_register / run_update reuse the same rules to prevent drift:
- method and benchmark remain hard boundaries; an experiment group cannot override them;
- runs are comparable only when the user explicitly declares the same experiment_group or config snapshot SHA-256 values match;
- missing config / missing SHA / unknown values always form separate groups; never combine them into a "shared config" group.
"""

from __future__ import annotations

STATUS_VALUES = ("running", "success", "failed")
# running is a placeholder status: results are not ready, so exclude it from statistics and checks by default (like failed runs).
UNRESOLVED_STATUSES = ("running",)


def group_key(run: dict) -> tuple:
    """Return the comparison-settings group for a run (runs with the same settings can be averaged).

    Return (kind, method, benchmark, tag). method/benchmark are hard boundaries,
    so an explicit experiment group cannot override them (REV-03: same group name with different methods is still incomparable):
    - kind="explicit": same user-declared experiment_group means same group (tag=group name);
    - kind="config": matching config snapshot SHA-256 means same group (tag=SHA);
    - kind="unresolved": missing config/SHA means each run forms its own group (tag=run_id);
      unknown values are never combined into a "shared config" group.
    """
    method = str(run.get("method") or f"missing-method:{run.get('run_id')}")
    benchmark = str(run.get("benchmark") or f"missing-benchmark:{run.get('run_id')}")
    exp_group = str(run.get("experiment_group") or "").strip()
    if exp_group:
        return ("explicit", method, benchmark, exp_group)
    config = run.get("config")
    sha = config.get("sha256") if isinstance(config, dict) else None
    if isinstance(sha, str) and sha:
        return ("config", method, benchmark, sha)
    return ("unresolved", method, benchmark, str(run.get("run_id")))


def same_setting_runs(runs: list[dict]) -> dict[tuple, list[dict]]:
    """Split runs with the same (method, benchmark) by comparison settings."""
    buckets: dict[tuple, list[dict]] = {}
    for run in runs:
        buckets.setdefault(group_key(run), []).append(run)
    return buckets


def group_label(key: tuple, members: list[dict]) -> str:
    """Create a readable label for a comparison-settings group, shared by table rows, notes, and warnings."""
    kind, _method, _benchmark, tag = key
    if kind == "explicit":
        shas = sorted({str((m.get("config") or {}).get("sha256") or "no-snapshot")[:8] for m in members})
        diff = f"(config differences: {'/'.join(shas)})" if len(shas) > 1 else ""
        return f"Experiment group {tag}{diff}"
    if kind == "config":
        return f"Config {tag[:8]}"
    run_id = tag
    return f"No config snapshot (run {run_id}; not grouped with any other run)"



def mergeable(groups: list[tuple]) -> bool:
    """Check whether a set of runs belongs to at least one comparable settings group."""
    return len(set(groups)) <= 1


def reproducibility_info(meta: dict) -> dict:
    """F06: record reproducibility information; do not claim that reproducibility has been proven.

    New records always use reproducibility_status="not_verified". Complete seed/commit metadata only means
    the information was recorded; no rerun verification was performed. Read the legacy reproducible boolean only for backward compatibility.
    """
    git = meta.get("git") if isinstance(meta.get("git"), dict) else {}
    seed_ok = meta.get("seed") is not None
    commit_ok = bool(git.get("commit"))
    clean = git.get("dirty") is False
    missing: list[str] = []
    if not seed_ok:
        missing.append("seed")
    if not commit_ok:
        missing.append("commit")
    elif not clean:
        missing.append("clean-commit (working tree was dirty at registration)")
    config = meta.get("config") if isinstance(meta.get("config"), dict) else {}
    config_ok = bool(config.get("sha256") or config.get("snapshot"))
    if not config_ok:
        missing.append("config snapshot")
    return {
        "reproducibility_status": "not_verified",
        "repro_registered": {"seed": seed_ok, "commit": commit_ok,
                             "commit_clean": clean, "config": config_ok},
        "repro_missing": missing,
        "note": "Reproducibility metadata is recorded only; no rerun verification was performed, so this does not establish that the experiment is reproducible",
    }
