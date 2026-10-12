---
name: career-bridge
description: Turn research outputs into job-search materials: create résumé project cards from experiment runs (problem context, technical challenges, quantified results); generate probing interview questions about rationale, alternatives, what to change, and which ablation to run first; identify gaps in standard Agent interview topics; and check application timelines against paper deadlines. Trigger phrases include résumé, project experience, interview prep, deep-dive questions, mock interview, standard interview topics, new-grad hiring, internship, and Agent interview. Use real experiment records only; do not invent numbers.
license: MIT
---

# career-bridge: From Research Results to Job-Search Materials

A core part of ByteDance-style interviews is **deep project questioning**: a chain of questions such as “Why did you do this?”, “Was there a better approach?”, and “What would you change if starting over?” A second-round interview may continue for nearly 100 minutes. Memorizing question banks is not enough, but .grad/runs/ contains real configuration comparisons, ablations, and seed records—the primary material for answering in depth. Static collections of interview notes cannot provide this.

## Non-negotiable rules

- **Every quantified result must be traceable:** include a run ID or commit hash. Do not include or invent numbers absent from the run records.
- Explicitly mark missing material as “To be supplied — source material missing.” This is itself an action item, not a defect.
- Do not submit applications for the user, drill questions on their behalf, or promise an outcome.

## Workflow

### 1. Collect material

Read .grad/runs/ (method × benchmark × seed × status × config differences × cost), .grad/claims.jsonl (claim ledger; read support/support_by, and include only supported claims as confirmed résumé statements), Git log (engineering work), and .grad/radar/digest/ (evidence of technical breadth). For papers, use only the current primary note; old snapshots in digest/history/ and user annotations in *.user.md are not new papers or materials. Use primary records in .grad/radar/papers/ to confirm identity and reading status. If all sources are empty, say so: accumulate run records first; this skill does not invent project experience. Failed runs do not count as quantified achievements, but their failure_reason can support a truthful interview discussion of what failed, how it was diagnosed, and how to reduce risk next time.

### 2. Project cards (three parts)

For each project, provide:

```markdown
### <Project> (<period>; source: <repository>)
- **Problem context:** In one sentence, explain what problem was solved and for whom, in terms a non-technical reader can understand.
- **Technical challenges:** Give 2–3 real challenges from dirty work in the run records (for example, configuration did not converge, evaluation was unstable, or cost exploded). Avoid empty claims such as “high concurrency.”
- **Quantified results:** Include only numbers in runs, in the format “metric (mean ± std, n=<number of seeds>),” with run IDs.
```

For n=1, write “(n=1).” Honesty is more valuable than appearances when an interviewer asks about variance.

### 3. Reverse-engineered deep-dive practice (core output)

Generate **at least 10 chained questions** per project card, with at least two questions in each category:

1. **Why this approach?** Why choose A over B? Use configuration comparisons in the run records: what was tried, what was dropped, and what the data showed.
2. **Was there a better approach?** Ask what was not tried and why (time, compute, or knowledge), then how the candidate sees it now.
3. **What would you change if starting over?** Use a real example of a throughput–memory trade-off, such as ZeRO-3 versus ZeRO-2 with gradient checkpointing. Find an analogous story in the user's run records.
4. **Which ablation would you run first?** Ask for priorities and reasoning when resources are limited.

Attach an “answer material pointer” to every question (run ID, commit, or configuration snapshot path). A refuted claim is strong interview material: “We tried X, disproved it, and found reason Y” is more credible than an invented story. Mark the support status when a project card cites a claim. **Mark questions without source material as “To be supplied.”** Prioritize them during mock interview practice.

### 4. Gaps in standard interview topics

**Read `{SKILL_DIR}/references/agent-topics.md`**, which contains seven dimensions verified from first-hand 2026 interview notes. Ask the user to self-rate each item (✅/⚠️/❌) and summarize the gaps. Prioritize ⚠️.

### 5. Application timeline and paper-deadline conflicts

Read `.grad/cache/ccfddl/allconf.yml`, the submission-gate deadline cache. If it is missing, first run its ddl_fetch. Put the target application window and paper deadlines, including rebuttal periods, on one timeline. Explicitly mark overlaps and offer options (for example, “Avoid the mid-to-late September early-application rush during the ICLR crunch”). This is a reference, not a decision for the user.

## Boundaries

Do not provide question-bank drills, simulate general technical trivia unrelated to the user's material, or generate “guaranteed pass” language. People decide: the cards and question list are source material; the user decides which roles to apply for and how to answer.
