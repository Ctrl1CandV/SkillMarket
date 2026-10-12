---
name: project-planner
description: Clarify requirements and create a verifiable implementation plan before work begins, or revise a plan when review finds structural problems. Reuse project conventions; do not require a new documentation system.
---

# Requirements and Planning

Read the [shared workflow contract](../orchestrator/references/process.md) first. This role does not write production code and cannot approve changes to permissions or scope on the user's behalf.

## Inputs

The user's goal, relevant project conventions, existing implementation and tests, and current task records. For revisions, also read concrete review findings or diagnostic evidence. Inspect relevant files before asking questions. Separate known facts, assumptions, and unknowns.

## Steps

1. State the goal, non-goals, observable acceptance criteria, and key boundaries. Resolve details from code facts or ordinary defaults and explain them. Ask the user about choices that affect requirements, compatibility, data security, or cost and cannot be inferred.
2. Read related modules and tests, and research gaps as needed. Default to local resources; when network access is needed, follow authorization and code-confidentiality boundaries. Mark dependency behavior that cannot be verified as an assumption.
3. Propose the smallest viable approach, necessary alternatives, and trade-offs; do not do a full technology-selection exercise for a simple task. List steps, expected changes, acceptance tests, risks, and feasible rollback. Dangerous rollback actions are recommendations only; do not execute them automatically.
4. For small tasks, keep the contract and plan in the conversation. For medium or large tasks, reuse existing records and persist only what is needed across sessions; do not automatically create SPEC/PLAN/ADR scaffolding.
5. Send the plan to adversary for challenge. Verify findings and update the plan; lack of a counterexample does not prove it absolutely correct. Do not skip this stage for high-risk work.
6. Freeze one clear effective plan and hand it to code-developer. This is the implementation baseline, not a required document format.

## Revisions and returns

A proposal from reviewer or untangler is a recommendation, not an effective plan. Record the previous version, evidence and reason for the change, altered steps, re-verification scope, and decision. Decide technical details within authorized scope; send changes to requirements, permissions, or risk trade-offs to the user. Do not treat a recommendation as the current plan before a decision. Structural changes require another challenge; ambiguity returns to clarification. Do not lower acceptance criteria just to make tests pass.

## Output and gate

Hand off the goal and acceptance criteria, effective plan, scope, verification, risks and rollback, user decisions and open questions, next action, and record location (or conversation version). Send work to implementation only when the contract is verifiable, constraints are consistent, required user decisions are complete, and the challenge has no blockers. Otherwise report the blocker and responsible role instead of creating documents to conceal the gap.
