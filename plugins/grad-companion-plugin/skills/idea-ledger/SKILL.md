---
name: idea-ledger
description: A ledger of research ideas and abandoned paths. Record candidate research directions, select or reject them (a killed status requires a method-level reason and environment-related failures trigger a warning), make why-not-selected ranking rationales explicit, and count research-direction stagnation. Trigger phrases include “record an idea,” “idea ledger,” “we tried this direction,” “research-topic record,” “rejected direction,” and “stagnation check.” Record only; people decide whether to kill an idea.
license: MIT
---

# idea-ledger: Research Ideas and Abandoned Paths

Six months later, “why didn't we choose it?” and “what was disproved?” can be more valuable than “what did we accomplish?” This skill records that information in an **append-only ledger** to help avoid repeating dead ends.

## Non-negotiable rules

- **Record, do not decide.** People decide whether a direction should be abandoned. The script only records and counts; it never says “give up.”
- A record with `status=killed` must have a non-empty `--reason` explaining why the idea itself is methodologically invalid. Switching tools or fixing configuration is an environment issue, not a reason to kill an idea.
- **Prevent memory poisoning:** Do not store negative capability claims such as “tool X cannot do Y” in `text`; later sessions may load and repeat them as fact. Record a workaround or requirement instead.

## Path placeholder

`{SKILL_DIR}` is the absolute path to the directory containing this SKILL.md, expanded by the caller. Quote all command paths. On Windows, set `PYTHONUTF8=1` first if Chinese text is garbled.

## Data contract

`.grad/ideas.jsonl` is append-only, with one record per line:

```json
{"idea_id": "i-001", "text": "<one-sentence idea>", "status": "candidate",
 "source": null, "why_not_selected": null, "killed_reason": null, "recorded_at": "..."}
```

For the same idea_id, **the last row is the current state** (latest wins). Switching from killed back to selected is valid: history is retained, and a reversal is useful information. Executors must not edit this file by hand.

## Workflow

```bash
# Add an idea (text required; source is an arXiv ID or one sentence; state the ranking rationale)
uv run --no-project "{SKILL_DIR}/scripts/idea_ledger.py" add \
  --text "<one-sentence direction>" [--source "<arXiv ID or one sentence>"] \
  [--why-not-selected "<why it was not chosen first>"] --json

# Change status (reason required for killed; --note can record a transition such as the new direction)
uv run --no-project "{SKILL_DIR}/scripts/idea_ledger.py" update \
  --id i-001 --status <candidate|selected|killed> [--reason "<...>"] --json

uv run --no-project "{SKILL_DIR}/scripts/idea_ledger.py" list [--json]
```

- When `add` detects duplicate text for an unresolved entry (candidate/selected), it warns. It also warns about “cannot do X” capability claims.
- When a `killed` reason matches an environment-failure pattern, `update` warns but does not block the change. The original wording remains in the record; a person decides whether to uphold the rejection.

### Stagnation count (detect-only; consumed by weekly-brief)

```bash
uv run --no-project "{SKILL_DIR}/scripts/idea_ledger.py" stagnation --repo . --json
```

This count-only output reports the number of unresolved entries, the age in weeks of the oldest open item, days since the last claim event, days since the last run, and three boolean signals for a window (three weeks by default). **It reports numbers only and makes no decision.** When there is a signal, weekly-brief includes one “research-direction stagnation” line in the report.

## Error contract

When the script returns `{"ok": false, ...}`, relay `error` and `detail` accurately. `NOT_FOUND` lists known idea IDs. `BAD_ARGS` indicates invalid input (empty text or a killed status without a reason); fix it and rerun. The workflow works offline.
