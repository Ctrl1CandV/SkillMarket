---
name: orchestrator
description: Organize development when starting a project, feature, or bug fix. Scale clarification, planning, challenge, implementation, review, repair, verification, and delivery to the risks. Supports sequential work by a single agent.
---

# Development Workflow Coordination

Read the [shared workflow contract](references/process.md) first. Its permissions, handoffs, and completion gates apply to every stage.

## Inputs and preparation

Receive the user's goal, current code state, and existing evidence. Read applicable AGENTS.md, CLAUDE.md, and project conventions; inspect the worktree and task scope. If materials are missing, inspect available files instead of inventing a document structure. Determine which read, edit, test, and host-agent capabilities are actually available.

## Execution

1. Assess scale and risk, then tell the user whether you will use a streamlined or full workflow. Even a small bug fix retains brief clarification, boundary challenge, self-review, and verification.
2. Apply the methods in this plugin's [project-planner](../project-planner/SKILL.md), [adversary](../adversary/SKILL.md), [code-developer](../code-developer/SKILL.md), and [reviewer](../reviewer/SKILL.md) in sequence. The same executor may perform them; spawning agents is not required. When the coordinator takes on a specific stage, state its current role and do not stop at routing with nobody implementing.
3. Maintain the handoff fields in the shared contract and check each stage's entry and return conditions. Implement clear user requirements; pause only for decisions that genuinely belong to the user.
4. If the reviewer rejects the work, return local implementation issues to code-developer and route plan or contract issues to project-planner, repeating adversary when needed. Review again after repairs, then verify the final version.
5. If the same issue fails repeatedly or the direction becomes confused, use [untangler](../untangler/SKILL.md) to locate the cause instead of making blind changes in a loop.
6. Once gates pass, use [memory-keeper](../memory-keeper/SKILL.md) to check necessary records and deliver. If no records need maintenance, summarize directly in the conversation.

## Output and stopping

Report current scale, sequence, actual artifacts, review mode, verification evidence, unresolved questions, and the next responsible role. If no host agent is available, explicitly call it “self-review”; do not claim an independent review. When permissions are insufficient, a user decision is pending, hard constraints conflict, or required verification is missing, mark the work blocked or awaiting verification. Do not commit or deploy automatically, and do not treat an archive as proof of completion.
