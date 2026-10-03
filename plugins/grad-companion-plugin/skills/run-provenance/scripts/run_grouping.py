# /// script
# requires-python = ">=3.12"
# ///
"""run 可比性分组与复现信息的共享规则（run-provenance 内部模块）。

table_gen / claim_check / claim_register / run_update 复用同一套判定，避免两处规则漂移：
- 保留 method 与 benchmark 两个硬边界，实验组不能绕过；
- 只有用户明确声明的 experiment_group 一致，或 config 快照 sha256 明确一致，才视为同一比较设置；
- 缺配置 / sha 缺失 / unknown 永远各自成组（保守分列），不并成「共同配置组」。
"""

from __future__ import annotations

STATUS_VALUES = ("running", "success", "failed")
# running 是占位状态：结果未出，任何统计/核对默认排除（与 failed 一样不参与均值）
UNRESOLVED_STATUSES = ("running",)


def group_key(run: dict) -> tuple:
    """一个 run 所属的比较设置组（同设置=可合并求均值）。

    返回 (kind, method, benchmark, tag)——method/benchmark 是硬边界的一部分，
    显式实验组不能绕过（REV-03：同组名不同方法也不可比）：
    - kind="explicit"：用户声明的 experiment_group 一致 → 同组（tag=组名）；
    - kind="config"：config 快照 sha256 明确一致 → 同组（tag=sha）；
    - kind="unresolved"：缺配置/sha 缺失 → 每个 run 各自成组（tag=run_id），
      unknown 永远不并成「共同配置组」。
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
    """按比较设置切分同一 (method, benchmark) 下的 run。"""
    buckets: dict[tuple, list[dict]] = {}
    for run in runs:
        buckets.setdefault(group_key(run), []).append(run)
    return buckets


def group_label(key: tuple, members: list[dict]) -> str:
    """给一个比较设置组生成可读标签（表内行/注释与告警共用）。"""
    kind, _method, _benchmark, tag = key
    if kind == "explicit":
        shas = sorted({str((m.get("config") or {}).get("sha256") or "无快照")[:8] for m in members})
        diff = f"（配置差异：{'/'.join(shas)}）" if len(shas) > 1 else ""
        return f"实验组 {tag}{diff}"
    if kind == "config":
        return f"配置 {tag[:8]}"
    run_id = tag
    return f"缺配置快照（run {run_id}，不与其他 run 合并）"



def mergeable(groups: list[tuple]) -> bool:
    """若干 run 是否同属一个可比设置（至少 1 个组）。"""
    return len(set(groups)) <= 1


def reproducibility_info(meta: dict) -> dict:
    """F06：可复现信息只登记、不证明。

    新记录一律 reproducibility_status="not_verified"——seed/commit 齐全也只说明
    登记信息完整，未执行过重跑验证。legacy 的 `reproducible` 布尔只作旧字段兼容读取。
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
        missing.append("clean-commit（登记时工作区为脏）")
    config = meta.get("config") if isinstance(meta.get("config"), dict) else {}
    config_ok = bool(config.get("sha256") or config.get("snapshot"))
    if not config_ok:
        missing.append("config 快照")
    return {
        "reproducibility_status": "not_verified",
        "repro_registered": {"seed": seed_ok, "commit": commit_ok,
                             "commit_clean": clean, "config": config_ok},
        "repro_missing": missing,
        "note": "复现信息仅为登记状态；未执行复现验证，不能据此宣称实验可复现",
    }
