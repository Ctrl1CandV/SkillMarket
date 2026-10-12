---
name: run-provenance
description: Trace experimental claims to runs. Register experiment runs with Git commit, configuration snapshot, seed, and metrics; keep a two-axis claim ledger with mechanical evidence checks and human support judgments; generate mean ± std LaTeX tables without inventing error bars for n=1; check draft numbers for value_mismatch, suspected_drift, and unbacked candidates; and review evaluation budgets and reproduction packages. Trigger phrases include register a run, record an experiment, experiment ledger, numbers do not match, paper-number provenance, reproducibility, seed, error bar, generate experiment table, and claim judgment. Record and verify only; never run experiments.
license: MIT
---

# run-provenance: Tracing Experimental Claims to Runs

This skill addresses one question: **Are the numbers in your own paper real?** Citation checks ask whether other people's references are genuine; this workflow asks whether each experimental number in your paper can be traced to a specific run.

## First rule: read and record only

**Do not start training, request GPUs, change hyperparameters, delete files, or rerun anything.** Reading Git status is a read-only operation. Changes may be written only under `.grad/`. The `experiment-design` skill covers experimental design (such as seed counts and statistical tests); refer the user to it when available. This skill only registers and checks records.

## Second rule: scripts report; people judge

The claim ledger has two axes (see the data contract): **evidence** is a mechanical check computed by the script, and **support** is a human judgment.

- The agent must not fill in support. The `--by` value must come from an explicit user statement or a user-reported decision. If the user has not expressed a view, leave the claim `unreviewed`.
- `evidence: verified` means one number was compared and clearly matched under the same settings. It **does not mean the claim is true**; a person decides that.
- `needs_review` means evidence exists but a mechanical comparison cannot be completed (multiple or missing numbers, ambiguous units, or incomparable settings). Report it accurately for human review; do not skip it to make the ledger appear “verified.”
- Relay `claim_check` output, especially `unbacked_candidates` and `suspected_drift`, **verbatim** to the user. Do not summarize it as “no problem.” A draft check only finds number candidates across the document; do not claim that a statement was verified in the draft.

## Path placeholder

`{SKILL_DIR}` is the absolute path to this SKILL.md's directory, expanded by the caller. Quote all command paths. On Windows, prefix commands with `PYTHONUTF8=1` if Chinese text is garbled.

## Data contract

`.grad/` contains:

```text
.grad/
├── runs/<run-id>/
│   ├── meta.json      # run_id/method/benchmark/experiment group/seed/status/failure reason/cmd/hardware/cost/Git and config snapshot hashes/timestamps/reproduction-registration status
│   └── metrics.json   # metric JSON, for example {"resolved_rate": 0.712}
├── claims.jsonl         # append-only claim ledger, written by claim_register.py (never edit by hand)
└── claims_checks.jsonl  # audit log (appended by claim_check.py --log)
```

Each row in claims.jsonl looks like:

```json
{"claim_id": "c-001", "claim_text": "AgentFlow reached a 71.1% resolution rate on SWE-bench-Lite",
 "run_ids": ["run-..."], "metric_path": "resolved_rate", "support": "unreviewed",
 "support_by": null, "support_at": null, "recorded_at": "..."}
```

Rules:

- **evidence is derived, not a stored field:** `claim_check.py` computes it each time (six levels below); it is not written back to the ledger.
- **support has four values:** `unreviewed` (default), `supported`, `partial`, and `refuted`. Change it through the `support` subcommand, which appends a new row. For each claim_id, **the last row is current**.
- **Legacy rows** without claim_id are read as independent claims; support is always treated as unreviewed. An old `status: supported` was written by an executor and is not a human judgment. To record a human decision, register a new row with `add`.
- **Comparison grouping is shared** by table_gen, claim_check, claim_register, and run_update. Method and benchmark are hard boundaries. Within those boundaries, combine runs only when the user explicitly declares the same `experiment_group` or configuration snapshot SHA-256 values match exactly. Missing or unknown configuration remains in a separate group; never combine it into a “shared configuration” group.

## Workflow

### 1. Register a run

```bash
uv run --no-project "{SKILL_DIR}/scripts/run_register.py" \
  --method <method> --benchmark <benchmark> [--seed <n>] [--experiment-group <name>] \
  --status <success|failed|running> [--failure-reason "<reason>"] \
  --config <config-file-path> --metrics '{"<metric>": <value>}' \
  --cmd "<actual command>" --hardware "<hardware>" --json
```

- **Use paths only when supplied by the user.** The user must provide config and metrics file paths; do not infer them from search results or guess.
- `--runs-dir` must be inside the repository's `.grad/` directory (default `.grad/runs`) or the script returns `BAD_ARGS`. This protects run records from being written outside the project-state directory.
- If the user did not provide a seed, the script records null and warns that reproduction information is incomplete. Do not invent one.
- A dirty worktree is recorded accurately (`dirty: true` plus a warning). Record the actual HEAD commit; do not guess.
- Register failures such as OOM, divergence, and timeout too. `--status failed` requires a non-empty `--failure-reason`. For compatibility, an older run without status is treated as successful.
- **When an experiment has started but results are not ready, register a placeholder with `--status running` and no metrics.** Later use run_update.py to add results without creating a new run ID. Running runs are excluded from all statistics, including tables and claim checks.
- **Reproducibility is recorded, not proven (F06).** New records use `reproducibility_status: not_verified`. Even a seed, clean commit, and complete configuration snapshot only mean that reproduction details were recorded. The script has not rerun the experiment on another machine, so never say the experiment is reproducible. The legacy boolean `reproducible` is accepted for reading only.
- Set `--experiment-group` only when the user confirms that runs share comparison settings (for example, a seed is in the config and changes the snapshot hash). **The agent must not guess this value.** Omit it if the user has not said so.

### 1b. Add results later (running → results available)

```bash
uv run --no-project "{SKILL_DIR}/scripts/run_update.py" \
  --run-id <run-id> [--status <success|failed>] [--failure-reason "<reason>"] \
  --metrics '{"<metric>": <value>}' --json
```

- Update only metrics, status, failure_reason, and updated_at for an existing run. **Never change created_at, Git commit, config snapshot, or seed**; do not capture the current HEAD and misrepresent it as the commit used by the experiment.
- A failed run update requires a reason. Validate metrics before saving; if validation fails, reject the update and leave original data readable (atomic replacement and rollback on failure).
- A run without results cannot be changed to success and presented as having results. Empty metrics with success triggers an accurate warning.

### 2. Link claims and record human judgments

Register claims through the script. Hand-editing the ledger is prohibited; the guardrail exists only in the script:

```bash
uv run --no-project "{SKILL_DIR}/scripts/claim_register.py" add \
  --claim "<verbatim paper claim, preserving its number format>" \
  --runs "<run-id1>,<run-id2>,<run-id3>" \
  --metric "<metric key>" --claims-file .grad/claims.jsonl --json
```

- Link **every** run across multiple seeds; do not choose the best one.
- `add` has no `--support` option by design. The script warns if bound runs mix methods or benchmarks.
- Record a verdict only after the user explicitly states it, such as an advisor's decision or the user's own review. The `--by` value must be the user's wording:

```bash
uv run --no-project "{SKILL_DIR}/scripts/claim_register.py" support \
  --id c-001 --verdict <supported|partial|refuted> \
  --by "<person, using the user's words>" --claims-file .grad/claims.jsonl --json
```

### 3. Generate tables

```bash
uv run --no-project "{SKILL_DIR}/scripts/table_gen.py" --runs-dir .grad/runs --json
```

- Compute mean ± sample standard deviation (ddof=1). For **n=1**, output `value (n=1)`; never output ±.
- Add a `% provenance` footer mapping every number to a run ID and commit, so it can be traced during review.
- **Do not silently merge different comparison settings (F02).** For the same method × benchmark, runs with differing or missing configuration hashes appear on separate rows with labels indicating the grouping basis (config hash, explicit experiment group, or missing config), plus a warning. Merge only matching hashes or a user-declared shared `experiment_group`. If explicitly grouped runs have different configs, warn and show the difference.
- Exclude failed and running runs by default. Only when `--include-failed` is explicitly passed may failed runs with numeric metrics enter the statistics. Running runs are always excluded because results are unavailable. Report loaded/included/skipped counts.
- Warn about repeated seeds within a group (best-of-N risk) and include all runs in the calculation; **a person decides whether to exclude them**.
- If a group contains suspected metric-key drift such as `acc` vs `acc.`, warn and list run IDs; do not merge automatically.
- The script does not rank performance: do not bold or label a best result.

### 4. Check consistency while revising a paper

```bash
# Ledger self-check: compute evidence for each claim, stopping at the strictest matching level
uv run --no-project "{SKILL_DIR}/scripts/claim_check.py" --repo . --json
# Draft number check: compare numbers extracted from a TeX/Markdown draft with the ledger
uv run --no-project "{SKILL_DIR}/scripts/claim_check.py" --repo . --draft <draft-path> --json
```

Evidence has six levels, checked from strictest to broadest:

| evidence | Meaning | Common case |
|---|---|---|
| `run_missing` | Bound run directory does not exist | Mistyped run ID or run recorded in another repository |
| `pending` | No numeric result can be checked | Placeholder has no result (including running) or all runs were excluded |
| `metric_missing` | Metric key is absent from a run's metrics.json | Key drift (detail may include edit-distance suggestions) |
| `needs_review` | Evidence exists, but numbers cannot be compared unambiguously | Multiple or no numbers in claim, ambiguous units, or incomparable run configurations; preserve available values for a person to inspect |
| `value_mismatch` | A single number was compared with run mean and clearly differs | Draft number changed but ledger did not, or vice versa |
| `verified` | A single number clearly matches and bound runs share comparison settings | The number exists and matches; this still does not establish that the claim is true |

- **Threshold for verified:** only a completed numeric comparison with a clear match qualifies. Mechanical status never upgrades human support.
- `--draft` adds results that are **candidate number matches across the document**, not proof that a particular statement is correct: `found` (number occurs somewhere in draft), `matched_candidates` (candidate rendered values that matched), `suspected_drift` (last-digit differences), and `unbacked_candidates` (numbers in table, ±, or percentage contexts without claim support; **a person must filter this candidate list**).
- `--include-failed` may include failed runs with numeric metrics in means; default behavior matches table_gen and excludes them.
- Mismatch, missing, or needs_review findings still return `ok: true`. Findings are data, not execution failures.
- **Report only; do not edit the paper.** The user decides whether and how to change it.
- Use `--log` to append results to `.grad/claims_checks.jsonl` for review history (which date the check passed and when drift first appeared).

### 5. Check agreement between judges

If a paper uses an LLM as a judge, evidence of agreement is required to claim it was validated. Follow two steps:

1. **Follow the protocol:** Read `{SKILL_DIR}/references/judge-protocol.md` first. Observe the minimum sample size, fixed temperature and prompt version, swapped A/B positions on repeat evaluation, and human adjudication of disagreements.
2. **Compute mechanically:**

```bash
uv run --no-project "{SKILL_DIR}/scripts/judge_agreement.py" \
  --a <human-scores.json> --b <judge-scores.json> --json
```

Report sample size (paired intersection; excluded samples are counted, not interpolated), exact agreement rate, Cohen's κ, and confusion matrix. **A person decides what κ is good enough**; the script only computes it. If κ cannot be calculated, report null and the reason (for example, degenerate marginals); this is not an execution failure. Register the agreement experiment as a run using section 1.

### 6. Prepare a reproducibility package before camera-ready

```bash
uv run --no-project "{SKILL_DIR}/scripts/repro_pack.py" --runs-dir .grad/runs \
  [--claims .grad/claims.jsonl] [--out REPRODUCING.md] --json
```

Generate `REPRODUCING.md` from the ledger: a seed table (mark missing seed/cmd/hardware as MISSING and count them; do not guess), registered reproduction commands (worded as “recorded, not verified by rerunning”), a reproduction-information status section (per-run recorded/missing fields and overall `reproducibility_status=not_verified`—**the package has never verified a rerun on another machine, so do not claim experimental reproducibility**), a paper-number-to-run mapping with support status preserved, and two of the five checks in budget.md filled automatically as ✅/❌. Transfer ledger facts only: run no commands and do not generate requirements files.

### 7. Budget and benchmark citation caveats

For evaluation budget design, read `{SKILL_DIR}/references/budget.md` (HAL's $40,000 / 21,730 rollout scale as an anchor and the statistical risks of reducing sample counts). Before citing public benchmark scores, consult `{SKILL_DIR}/references/benchmark-caveats.md`, a living document whose verified items (such as SWE-bench solution leakage and τ-bench name confusion) include primary sources. During ledger checks, matches append a `benchmark_caveats` warning automatically. It is a mechanical reminder; a person decides whether and how to describe it.

## Error contract

When a script returns `{"ok": false, ...}`, relay it accurately. `NO_CLAIMS` means no ledger exists; register a claim with `claim_register.py add` first. `NOT_FOUND` means the claim ID does not exist and the script will list known IDs. `NO_FILE` means the draft path is invalid; correct and retry without downgrading the check. All checks can fall back to reading local JSON when offline; no network is needed.
