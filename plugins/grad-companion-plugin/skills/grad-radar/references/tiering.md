# Tiering Rules (Daily Discovery: Screening)

> **This document is heuristic, not authoritative.** The result is “heuristic ranking, not a quality judgment.” It reflects relevance to the current learning goal, not overall paper quality. Include this statement with every result.

## Keep these two concepts separate

- **Recommendation tier:** `must_read` / `skim` / `archive` — the display level for this brief. Follow the current request's quantity first, then `daily_caps` from `.grad/config.json`; if neither exists, use must_read 1 / skim 2. A limit of 0 means do not assign that tier. For the user, display “priority reading / quick look / other candidates” to avoid making it feel like a required task.
- **Importance:** core / relevant / peripheral — a relationship between the paper and the learning goal, stored in the primary single-paper record's classification.

Tier ≠ importance. must_read does not automatically mean importance=core (a paper may be relevant because a deadline is close today). A core paper need not appear in today's brief (it may already be registered as in progress). Archiving a paper does not mean it is unimportant; it means only that no time is allocated to it now.

## Current scope and standard workflow

Use the current request and the same task's conversation to establish topic, question, focus, and timing. Ask a short question if scope is missing; do not apply a preset topic. Do not automatically turn saved keywords, reading background, old briefs, or the seen ledger into current interests. Read an old configured scope only when the user explicitly requests it, and do not update long-term preferences as a result.

The standard workflow remains: convert the current scope to actual queries → retrieve metadata → screen and tier for the task → extract the question, approach, and findings supported by the available abstract for a small number of priority/quick-look items → send user-selected work to single-paper reading. Metadata alone does not prove body quality. For general paper/review recommendations, use the context priorities in selection-protocol to verify source, year, citations, and key body sections. If the user requires recent top venues or high impact, check every criterion; a must_read tier does not make a preprint formally accepted or a recent paper highly cited. Read directly specified papers as requested.

Daily queries usually find recent arXiv candidates; choose categories and keywords based on the current question. A classic source may explain or complement the topic but must not be presented as a new submission in today's window. Label date, source, and scope separately.

## Three tiers

| Tier | Limit | Meaning | Deliverable |
|---|---|---|---|
| **must_read** (priority reading) | Current must_read limit | Directly relevant to the current goal and worth investing time in today or over the next few days | Briefly state the question, approach, and findings supported by the available material; selected papers continue to single-paper reading. |
| **skim** (quick look) | Current skim limit | Offers complementary value but has lower priority for time investment now | Quick card or one sentence; expand only if the user selects it. |
| **archive** (other candidates) | No limit | Everything else | **Short index: ID + title + one traceable reason.** Do not generate long summaries for these papers. |

Do not exceed current limits in the body and do not pad a short list. Suggest continuing existing reading instead when useful. If results exceed the limits, rank by fit to the current question and put the rest in the short index. Ranking and quantity do not prove quality.

## Interpret signals by task

Use signals to explain relevance to the current question, not to award points mechanically for the number of matches. A shared keyword alone does not imply fit; one precise match may matter more than several broad matches.

| Current goal | Content worth prioritizing |
|---|---|
| Beginner entry or a map of the field | A clearly defined review covering key approaches; foundational concepts or representative methods for current reading |
| Improve a method or explore a research question | Competing work on the same question, mechanism changes, key assumptions, negative results, or counterexamples |
| Application or deployment | Work matching the actual task, environment, data, and resource limits, especially new constraints and transferable lessons |
| Evaluation or reproduction | Benchmarks and protocols with matching settings, reproduction analyses, failures, and non-comparable conditions |
| Theory learning | Definitions, assumptions, theorems, proofs, or links to the current mechanism |

A review, application, theory paper, robotics, games, hardware, or other field does not determine its tier; any can be priority reading when directly relevant. The foundational role of classic work does not disappear with age, and unknown impact for a recent preprint does not imply poor quality.

Use skim for candidates with concrete complementary value that do not need deeper attention now. Use archive for items that touch the scope but do not answer the current question, have unsuitable settings, unresolved identity, or duplicate another result. State the specific gap. Verify duplicate identity; do not merge solely by similar titles. A paper seen under another topic may still deserve priority for the current question.

## Required rationale

For every paper and every tier, state a reason containing **the current question + what the actual metadata/abstract supports + the trade-off**. Use your own words; quotations are not required. Each reason must be falsifiable and show its evidence. A venue name or “relevant” alone is not an explanation.

- ✅ “Priority reading: You are checking how evaluation depends on execution environment; the abstract reports failures across environments for the same tool, so the setup is worth checking.”
- ❌ “Must read: seems relevant.” / “Top-conference paper; read closely.” (The venue name is not a relevance signal.)

## User feedback loop

When the user disagrees with a tier:

1. Update the current question, query, or ranking according to the correction. Search further only within rate limits and budget. Do not save one correction to config or plugin rules.
2. When this period's brief was authorized for saving, include a short reason for the adjustment. It is a record for this period only, not an automatically reused preference.
3. If the feedback concerns a single paper's importance/difficulty and record maintenance is authorized, use update-context and state the reason. Do not turn the record into a daily-interest setting.
