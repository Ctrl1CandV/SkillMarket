---
description: Register experiment runs, link claims, generate mean ± std tables, or check the consistency of numbers in a paper.
argument-hint: "<register|table|check> [arguments]"
skill: run-provenance
---

Route by intent: for judge-agreement verification, run `judge_agreement.py` (compute κ without drawing conclusions; read `references/judge-protocol.md` first). For a camera-ready reproduction package, run `repro_pack.py` (report MISSING items as missing; do not guess). To register a run, use `run_register.py` (take paths only from the user's own words, use null when the seed is missing, and record failed runs with `--status failed --failure-reason`). To link a claim, run `claim_register.py add` (link every run across multiple seeds instead of selecting the best; use the `support` subcommand for a person's judgment, with `--by` taken from the user's own words; the agent must not fill it in). To make a table, run `table_gen.py` (failed runs are excluded by default, label `n=1` without fabricating error values, and only warn about metric-key drift). To check consistency, run `claim_check.py` (the ledger self-check reports five evidence levels; `--draft` also checks draft numbers and reports `found`, `suspected_drift`, and `unbacked` candidates). These outputs mechanically check evidence; they are not peer reviews. Report findings without editing the manuscript.
