---
name: memory-keeper
description: At stage handoffs or completion, reconcile existing records with facts from code, review, and verification, and maintain only necessary memory. Does not require a document template or replace decisions and completion gates.
---

# Record Reconciliation and Delivery Summary

Read the [shared workflow contract](../orchestrator/references/process.md) first. Follow existing AGENTS.md, CLAUDE.md, and project record practices; do not turn this plugin's format into a project-wide rule.

## Inputs and checks

Read the task goal, current effective plan, implementation, review and final-verification evidence, user decisions, and relevant existing documents. Do not create an empty scaffold for a missing document; a conversation summary is enough for a small task.

1. Reconcile facts, status, links, and the single current effective plan. Trace conflicts to code, command results, or decisions; do not fill gaps from memory.
2. Correct factual errors, broken links, or duplicated content only within the authorized scope. Explain the evidence and retain failure and revision history. Add only information that is useful long-term and not self-evident; do not copy full logs into memory.
3. Route conflicting requirement, architecture, or risk decisions to planner or the user; send code issues to developer and review gaps to reviewer. Do not rewrite a real defect as a new acceptance requirement.
4. Prepare a completion summary only when all completion gates pass. Preserve blockers, unverified work, pending independent review, deferrals, and cancellations accurately. Cancellation requires an explicit decision; do not infer it from three failed rounds or mark work complete.

## Output and boundaries

Report the scope reviewed, differences, factual corrections and their basis, and the responsible role for unresolved items. The final summary should state changes, review mode, verification level and result, remaining risks, and the user's next step. If no document needed an update, say “conversation delivery only; no new record.”

Do not make code or architecture decisions, change a review verdict, remove evidence to shorten a record, replace the entire documentation system, or commit, push, or publish automatically. Organizing records does not prove that a feature ran in reality; report simulations and static checks only at their actual verification level.
