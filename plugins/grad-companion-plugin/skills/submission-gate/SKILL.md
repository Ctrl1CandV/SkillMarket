---
name: submission-gate
description: Mechanically check submission requirements and build a reverse deadline schedule. Check page limits, checklist, Limitations, anonymity, related-work placement, and LLM-use disclosure; count down to ICLR/NeurIPS/ICML/ACL deadlines and detect conflicts; classify rebuttal comments as invalid criticism (ARR H1–H17) or substantive weakness (M/T/R/G). Does not write reviews or choose a venue for the user.
license: MIT
---

# submission-gate: Mechanical Pre-Submission Checks

The cost of a violation can be total (desk reject or rejection without review), and the rules can be checked explicitly. This skill is a checker: **show the material used for a decision; people decide.**

## Boundaries (what it does not do)

- **Does not write reviewer comments.** AI review can cause a hivemind effect and can be manipulated; ARR states that LLM-generated reviews may lead to desk rejection of reviewers' own submissions. This skill is for authors.
- **Does not choose a venue for the user.** Provide evidence and acceptance-rate references; the user chooses.
- **Does not compile PDFs or edit the manuscript.** Report issues; the user decides whether to fix them.
- Rebuttal **writing methods** belong to the academic-writing skill, which has a rebuttal mode. If available, refer the user to it. This skill handles the prior **classification and prioritization** only.

## Path placeholder

`{SKILL_DIR}` is the absolute path to the directory containing this SKILL.md, expanded by the caller. Quote all command paths. On Windows, prefix commands with `PYTHONUTF8=1` if Chinese text is garbled.

## Workflow

### 1. Identify the venue and rules

Use the venue supplied by the user. **Read `{SKILL_DIR}/references/venues.md` first**, including its rules table and itemized checklist. If the venue is not listed, state that it is not covered and ask for an official CFP link; do not guess the rules.

### 2. Deadline and reverse schedule

```bash
uv run --no-project "{SKILL_DIR}/scripts/ddl_fetch.py" --venues "ICLR,ACL,NeurIPS" --json
```

- Cache under .grad/cache/ccfddl/ with a seven-day TTL; do not fetch more often.
- Output includes each conference and year's abstract/full-paper deadlines, countdown in days, and timezone.
- Preserve each track/round in JSON timelines. The name comes from the original comment, or a stable timeline-N fallback when missing. Top-level abstract/full fields are summaries for compatibility with the first item; they do not represent the full lifecycle. Do not guess that a comment describes rebuttal or camera-ready.
- **Reverse schedule:** Work backward from the target timeline deadline and check T-14 days for experiment freeze, T-7 for complete draft, T-3 for itemized checks, and T-1 for upload test in the submission system. Mark a conflict only when the data source gives the corresponding window; record missing details as unknown.
- Rules change: **within two weeks of the deadline, remind the user to verify the current CFP on the official site.**

### 3. Mechanical checks (when a manuscript is provided)

When the user provides a PDF, LaTeX source, or directory, check each of the eight items in venues.md. Give each item one of three statuses:

- ✅ **Checked automatically** (include evidence, such as page count or matching text).
- ⚠️ **Needs human confirmation** (state what is missing and how to check it; for example, compare margins with the official template).
- ❌ **Violation** (include the supporting rule text).

Do not guess page counts that cannot be computed. If a checklist item is not found, say so; do not assume it exists. PDF metadata, including the author field, is part of the anonymity check.

### 3.5. Judge disclosure and agreement verification (when the paper uses an LLM as judge)

Agent papers often use a judge. Check each item:

- ⚠️ **Needs human confirmation:** Was judge agreement reported (κ/agreement rate/comparison protocol with human ratings)? ARR lists an unvalidated LLM-as-judge as its first methodological weakness; an unsupported agreement claim may be challenged in rebuttal.
- Prepare evidence using run-provenance (judge_agreement.py and references/judge-protocol.md). This skill checks only whether it was reported; calculation and judgment are out of scope.

### 4. Classify rebuttal comments (when the user has reviews)

**Read `{SKILL_DIR}/references/arr-h-list.md` first.** Classify each reviewer comment as:

- **Invalid criticism that can be rebutted** (matches H1–H17): respond using the substance of the guideline.
- **Substantive weakness requiring evidence** (matches M/T/R/G): provide data, add an experiment, or commit to a revision.
- Neutral suggestion: acknowledge and address it politely.

Prioritize under the rule “ACs read only the first two comments in each thread”: put the strongest response first. For R5 (error bars) and R1 (best-of-N), if the project has runs registered through run-provenance in .grad/runs/, cite the mean ± std table.

### 5. Venue strategy references (when asked where to submit)

Provide the acceptance-rate data at the end of venues.md, the Findings fallback mechanism, and any reciprocal-reviewing exemption for newcomers. State clearly, “This is a reference, not a recommendation.” Describe matches between the topic and venue only as facts (for example, the ACL 2026 topic list includes AI/LLM agents).

## Error contract

When a script returns `{"ok": false, ...}`, relay error and detail accurately. For a `NETWORK` failure, say that the cache at .grad/cache/ccfddl/ may contain previous data and can be used with its date clearly labeled.
