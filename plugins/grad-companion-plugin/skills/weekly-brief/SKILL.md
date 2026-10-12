---
name: weekly-brief
description: Create graduate-research weekly reports and lab-meeting materials by summarizing Git commits, experiment runs, paper reading, and claim changes. Produce a report covering work completed, conclusions, next week's plan, and questions requiring the advisor's decision. Trigger words include weekly report, lab meeting, advisor update, this week's progress, and weekly. Summarize real records only; do not invent progress.
license: MIT
---

# weekly-brief: Weekly Reports and Lab-Meeting Materials

A reliable, mechanical summary each week. Inputs are already structured (Git logs and the `.grad/` ledger). This skill only **collects, translates, and organizes** them; it does not embellish.

## Non-negotiable rules

- **Every progress item must be traceable:** include its source commit hash, run ID, or filename under `.grad/radar/`. Do not include items without a source.
- A failed run is not “no progress.” List OOM, divergence, timeout, and `failure_reason` separately as evidence for next week's risk reduction and advisor decisions; do not present failure as a successful result.
- **Do not invent progress.** If a data source is empty, say so (for example, “No new experiment records this week” when there are no runs). Do not pad the report.
- **An AI-organized note does not mean the user finished reading.** Notes in `radar/digest` are AI-assisted reading artifacts. Count them as “AI organized”; say that the user read a paper only when the user explicitly says so or a reading record has a read status whose source is `user`. If a paper record exists under `.grad/radar/papers/`, use `note.generated_at` for “AI organized” and `reading.status/last_read_at` for “user finished reading,” and count them separately.
- If a data source is missing (for example, a directory does not exist), state at the start of the report which sources are unavailable, then process the rest.

## Data sources (collect in order)

The default window is the most recent seven days (**current period**: the host's local date and the previous six days). Follow a user-specified number of weeks or dates.

**Step 0 — Reconcile commitments:** If `.grad/briefs/` contains a previous brief, first run the mechanical extractor. **Calculate and pass the current reporting window explicitly.** The previous brief supplies only plans and questions to check; the script no longer derives the current period from its heading:

```bash
uv run --no-project "{SKILL_DIR}/scripts/brief_reconcile.py" --prev <path-to-previous-brief> --repo . \
  --since <first-day-YYYY-MM-DD> --until <last-day-YYYY-MM-DD> --json
```

The result includes `plan_items`, `pending_decisions`, `evidence{commits, new_runs, updated_runs, new_claims}`, `evidence_status{per_source, overall}`, and `period{since, until, timezone}`. **evidence_status records the reliability of every source:** `ok` means it was read successfully and its list is trustworthy; `not_present` means the record source does not exist; `unavailable` means it could not be read; `partial` means some damaged entries were skipped. Choose wording accordingly: mark affected items “unverifiable” when the source is unavailable, not “not done”; when `overall=partial`, the report must say the evidence pool is incomplete and identify unread entries; only when status is `ok/complete` may “no completion evidence found” be used. Without `--since/--until`, the current period defaults to today and the previous six days. The previous report describes an old period; do not use its dates for this report. Report the returned period and actual timezone truthfully so the user can see the search window.

Then reconcile each item using exactly one of four outcomes:

- **Completed:** Check it and attach a pointer only when evidence directly covers the commitment. A commit that only sets up the environment does not fulfill “complete three comparison experiments.”
- **Partially completed:** Evidence covers only part of the commitment (for example, one of three experiments). State what is covered and what remains.
- **No completion evidence found:** No evidence in the window can be linked to fulfillment. This reports missing evidence; it does not judge whether the user did the work.
- **Unverifiable:** The source itself cannot be read (for example, this is not a Git directory or a ledger is missing). State this; it **does not prove the user did not do the work**.

For last week's pending decisions, mark an item “decided/resolved” **only when an actual decision record exists** (such as the user's report of an advisor's decision or meeting minutes). A related code commit does not prove the advisor made a decision. Without a new decision record, mark it as still pending.

```bash
# 1. Code progress: git log --since="<window-start>" --pretty=format:"%h %ad %s" --date=short
#    Include a git diff --stat overview of the change scope.
# 2. Experiment records: list runs added under .grad/runs/ during the window and runs whose results were added this period
#    (new_runs/updated_runs from the reconciliation script). Read the meta.json summary
#    (method/benchmark/seed/status/result or failure reason). Describe updated_runs as “results completed this period”;
#    created_at and the commit still refer to the original experiment and must not be presented as new work.
# 3. Literature: read .grad/radar/*.md from the window. Prefer tier/arxiv_id/path in frontmatter papers[]
#    (must_read/skim/archive); for older files without frontmatter, fall back to the body and mark them legacy.
#    If .grad/radar/papers/ contains primary records, link by paper_id:
#    “discovered this week” = entries in this period's brief; “AI organized” = notes with note.generated_at in the window;
#    “user finished reading” = reading.status/last_read_at based on an explicit user statement. Count these separately.
#    Count multiple note updates for one paper in the same week as one paper. Old drafts in digest/history/
#    and *.user.md annotations are not new papers and belong in none of these categories.
# 4. Claim changes: new rows in .grad/claims.jsonl during the window (links between paper claims and runs).
#    Read support/support_by. Legacy rows have only an old status; a supported value written by an executor is not
#    confirmation from a person.
# 5. Idea-ledger stagnation count:
#    uv run --no-project "{SKILL_DIR}/../idea-ledger/scripts/idea_ledger.py" stagnation --repo . --json
#    This is detect-only counting. When any_signal=false, skip this item and produce no paragraph for it.
```

`brief_reconcile.py` and idea_ledger perform mechanical extraction; the agent summarizes and writes the report using the rules above.

## Four-part report structure (output file)

Write to `.grad/briefs/YYYY-MM-DD.md`. If the file already exists, report a conflict instead of silently overwriting it. Include the full report in the reply as well.

```markdown
# Weekly Report · YYYY-MM-DD ~ YYYY-MM-DD

## 0. Reconcile the previous report
<!-- Include this first when a previous brief exists. If every item was fulfilled, this section may be omitted, but state at the beginning that all previous plans were fulfilled. -->
- ✅ <plan item> — completed (evidence covers commitment): <short commit hash / run ID / claim ID>
- ◐ <plan item> — partially completed: <covered part + evidence>; remaining: <uncovered part>
- ❌ <plan item> — no completion evidence found (state the reason; do not dress it up or infer that the user did nothing)
- ⚠️ <plan item> — unverifiable: <specific reason the source could not be read>; this does not mean it was not done
- ⏳ <decision question> — still pending (only an actual decision record counts as decided; a code commit is not an advisor decision)

## Optional: Research-direction stagnation
<!-- Include only when stagnation.any_signal=true. Copy the numbers as reported (open count, age of oldest open item in weeks, days since last claim/run); describe facts only. A person decides whether to change direction. -->
- The oldest unresolved direction is <N> weeks old; <N> days since the last new claim event; <N> days since the last run.

## 1. What happened this week
- <item> (source: <short commit hash> / <run ID> / <radar file>)
...

## 2. What are the conclusions?
- List conclusions supported by this week's runs or reading and cite the basis for each. If there is no clear conclusion, write “This week focused on research and environment setup; there is no stage-level conclusion yet.”
- List new human claim judgments this week (supported/partial/refuted, with support_by and time) separately. Decisions made by the advisor matter more than code commits in this report.

## 3. Plan for next week
- Derive the plan from unfinished work and advisor feedback; do not invent new goals.

## 4. Questions requiring the advisor's decision
<!-- This section is the most valuable part of the report; follow the rules below. -->
```

## How to write “Questions requiring the advisor's decision”

The advisor may not work in the Agent field, so **assume they have no technical background**. Translate technical choices into decision language:

1. Find genuine decision points from this week's work: technical choices with at least two reasonable paths, resource requests, or choices about direction.
2. For each question, write: **one-sentence context that a non-specialist can understand → 2–3 options → cost of each option (time/compute/risk) → which option you prefer and why**.
3. Include 2–3 questions. If there is no real decision point, write “No decisions require approval this week.” Do not invent one.

✅ “Benchmark choice: (a) Full SWE-bench — strongest conclusion, but about X GPU-hours; (b) Lite subset — six times faster, but reviewers may question coverage. I prefer (b) and will explain it in Limitations. What do you recommend?”

❌ “How many Transformer layers should we use?” (No options or costs; this is not a decision question.)

## Optional: Lab-meeting slide outline

When the user requests lab-meeting materials, add a Markdown outline based on the report, with one section per slide and key numbers as bullets. Render it to PPT using a document-processing skill available on the local machine; if none is available, provide only the outline.

## Error contract

If `brief_reconcile.py` returns `{"ok": false, ...}`, report the error accurately. `NO_PREV` means no previous report exists; this is normal for a first report, so write “First weekly report; nothing to reconcile” and do not count it as an error. `BAD_ARGS` means the date is invalid or the window is reversed (until precedes since); correct it and rerun. The current reporting period no longer depends on the previous brief's date heading. A missing date in the previous brief affects only the display of `prev_date`, not the reconciliation window.

## Boundaries

- Do not invent or exaggerate; “it ran successfully” requires a corresponding run record.
- Do not make commitments to the advisor on the user's behalf. Label next week's items as plans and state confidence.
- Do not render the PPT itself or send email.
