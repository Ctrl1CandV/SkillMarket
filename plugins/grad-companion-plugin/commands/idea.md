---
description: Add candidate directions to the research-idea ledger, update their status (selected or rejected), or view the stagnation count.
argument-hint: "<add|list|select|reject|stagnation> [text or ID]"
skill: idea-ledger
---

Route by intent: for a new entry, run `idea_ledger.py add` (provide a one-sentence `--text`, an arXiv ID or one-sentence source, and make the ranking rationale explicit with `--why-not-selected`). To select, reject, or switch an idea back, run `update`. A rejection requires the user to provide a method-level reason; an environment-related failure triggers a warning that must be relayed truthfully for the user to confirm. Run `list` or `stagnation` for the corresponding view; stagnation is a count-only reminder and does not make a decision. The ledger is append-only; the latest row for an ID is its current state.
