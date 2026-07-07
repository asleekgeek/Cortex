---
name: why
description: Resolve the ⟦rcpt:id⟧ injection markers in context into presence-in-context evidence (blame path)
---

Deterministic entry point for the blame path (decision 4255039, correction 6 — natural-language routing to the tool is not guaranteed; this command is).

1. Scan the conversation context for `⟦rcpt:N⟧` markers. They sit in the header line of every memory injection block (session-start banner, auto-recall block, agent briefing, recall responses' `receipt_id` field).
2. **Exclude the marker that arrived with THIS prompt's own memory-injection block** (the auto-recall block directly attached to the current user message). That receipt records what was injected for the current question — including it would blame the question's own context (self-pollution guard, correction 4).
3. If the user is questioning a specific earlier answer, keep only markers that were already in context **before** that answer was produced.
4. Call the `why` tool with the collected ids: `why(receipt_ids=[...])`.
5. Present the evidence with the locked lexicon:
   - Say the memories were **present in context** ("présence-en-contexte") at the recorded instants and ranks. **Never** say a memory *caused* the answer — the receipts are Pearl-rung-1 evidence of presence, nothing more.
   - Order as returned (emitted_at DESC, receipt id DESC as deterministic tiebreak, then persisted rank) — recorded facts only.
   - Flag rows where `superseded_by_id` is set (already corrected) and rows with `memory_missing: true` (hard-forgotten after injection; the receipt remains valid presence evidence).
6. If the user identifies a wrong memory among the evidence, offer to store a correcting memory with `remember` (the write path supersedes near-duplicates; the explicit atomic correction flow lands in tranche 4).

If no `⟦rcpt:N⟧` marker is visible in context, say so honestly: no receipt in scope means no presence evidence to resolve — do not guess or reconstruct ids.
