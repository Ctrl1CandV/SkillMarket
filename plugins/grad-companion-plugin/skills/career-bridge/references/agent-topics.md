# Interview Topics for Agent Roles (career-bridge)

> Source: interview reports for Agent roles at major technology companies, compiled from public sources in early 2026.
> Coverage: the full collection mentions 14 “Agent fundamentals” areas. This file includes **7 verified areas**; the remaining areas are omitted because no supporting evidence was found. Add new user-provided interview reports as they become available; this is a living document.

Conclusion first: in autumn 2026 recruiting, algorithm roles at ByteDance, Alibaba, Tencent, and vertical AI companies routinely ask about Agents. Interviews increasingly test **system design, task decomposition, memory, and context management**, not just Transformer fundamentals. These topics overlap strongly with research areas, which can be an advantage if you can explain “why.”

## 1. LangChain vs. LangGraph

- Core distinction: implicit control flow vs. explicit state machine. In one sentence: “LangChain lets the LLM improvise; LangGraph gives it a track to follow.”
- Likely follow-up: When is a graph necessary? For long workflows, or when rollback, branching, or human intervention is required; a chain wrapper can bury retry logic in the prompt.

## 2. MCP vs. function calling

- Core distinction: an ecosystem of external services vs. capabilities built into the model.
- Likely follow-up: production trade-offs—where to handle tool governance, authentication, and version management; MCP adds a protocol layer but decouples vendor changes.

## 3. Task decomposition granularity

- MECE; **3–6 steps is a useful range**. Too coarse means a high failure rate per step; too fine accumulates errors and expands context.
- Likely follow-up: How do you decide whether to split a task or switch models?

## 4. Multi-agent consistency

- Three essentials: **state machine + idempotency + event sourcing**.
- Likely follow-up: What if two agents write the same record at once? Use idempotency keys, version numbers or optimistic locking, and event replay for recovery.

## 5. GPU memory optimization (common in SFT/fine-tuning interviews)

Three main sources of GPU memory for SFT of a 7B model (approximate scale figures often used in interviews):

| Source | Approximate size |
|---|---|
| Parameters (FP16) | ~14 GB |
| AdamW optimizer state (FP32 momentum + variance + master parameters) | ~56 GB |
| Activations | 20+ GB (increases with sequence length) |

Techniques: ZeRO stages 1/2/3, gradient checkpointing, AMP mixed precision, and length-based bucketing.

**Reported interview example (“What would you change if you did it again?” from a ByteDance second round):** They started with ZeRO-3 and later found that **ZeRO-2 + gradient checkpointing had less communication and higher throughput on 8 GPUs**. They should have compared throughput/memory curves for stages 1/2/3 first. Lesson: “Do not assume the mainstream approach is optimal, especially when resources are constrained.”

## 6. Memory management

- Short-term (context-window strategies: truncation, compression, summarization) vs. long-term (external storage: vector databases, structured records).
- Likely follow-up: When can memory hurt? Stale information can contaminate decisions, and retrieval can add noise.

## 7. Reward design

- Reward-shaping traps with sparse rewards; process reward vs. outcome reward; common forms of reward hacking.
- Likely follow-up: How can you verify that the reward function itself has no bug? Use sampled human review and adversarial tests.

## How to use this list (step 4 of the career-bridge workflow)

Self-assess each area: can explain it for two minutes without notes and handle one follow-up = ✅; can explain it but cannot handle a follow-up = ⚠️ needs work; cannot explain it = ❌ gap.
Turn ⚠️ and ❌ items into an “interview fundamentals gap list,” prioritizing ⚠️ items because they are closest to the required level.
