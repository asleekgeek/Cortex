---
title: "ADR-0220 — mcp_server/core/pg_recall_stages.py rationale"
status: accepted
source: mcp_server/core/pg_recall_stages.py
---

# ADR-0220 — mcp_server/core/pg_recall_stages.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Split from pg_recall.py (continuing the two documented seams cut at #368 —
pg_recall_weights.py / pg_recall_assembly.py — with two more:
pg_recall_context.py and this file) to bring pg_recall.py under this
repo's local 300-line file cap and 40-line method cap
(docs/agent-guidance.md § Code Style; a tightening of coding-standards.md
§4.1/§4.2). Every value moved unchanged — this re-homes code, it retunes nothing.
````

## module — original line 10 (docstring)

````text
Every stage function takes exactly ``(candidates, ctx: RecallContext)`` —
see pg_recall_context.py for why the call-site invariants are bundled into
one object rather than passed as 8-13 positional parameters
(coding-standards.md §4.4, Introduce Parameter Object).

````

## _chronological_rerank — original line 49 (docstring)

````text
    ChronoRAG (Chen et al., arxiv 2508.18748, 2025): for event ordering
    queries, chronological position matters as much as semantic relevance.
    Blends each candidate's relevance rank with its chronological rank via
    Reciprocal Rank Fusion (Cormack et al., SIGIR 2009).
````

## _chronological_rerank — original line 47 (mixed-contract-rationale)

````text
    Args:
        candidates: Results ordered by relevance score.
        beta: Weight for chronological rank (0=pure relevance, 1=pure chrono).
        k: RRF constant (Cormack et al., 2009). Default 60.
````

## apply_recollection_pipeline — original line 82 (docstring)

````text
Post-WRRF paper-mechanism recollection chain (stages 4a-4g).
````

## apply_recollection_pipeline — original line 84 (docstring)

````text
    Each stage is gated by ``CORTEX_ABLATE_<MECH>=1`` (returns input
    unchanged when ablated). Order: HOPFIELD (Ramsauer 2021 attention),
    HDC (Kanerva 2009 bipolar algebra), SPREADING_ACTIVATION (Collins &
    Loftus 1975 BFS over the entity graph — AUGMENT mode only, may inject
    NEW candidates), DENDRITIC_CLUSTERS (Poirazi 2003 multiplicative
    modulation), EMOTIONAL_RETRIEVAL (Bower 1981 mood-congruent recall on
    the query's inferred valence), MOOD_CONGRUENT_RERANK (Bower 1981 on the
    user's session mood), RECONSOLIDATION (Nader, Schafe & LeDoux 2000,
    Nature 406(6797) — MUST be last so the mutation reflects the final
    ranking the user will see).
    
````

## apply_rerank_nudges — original line 120 (docstring)

````text
    FlashRank (client-side) reorders by content relevance. Then, in order:
    VALUE_PRIORITY (B2, weight 0.15, never overrides a strong content
    match), CONFLICT_MONITOR (A2 — Botvinick 2001; Miller & Cohen 2001 —
    demotes the losing memory of the most-contradictory pair),
    GOAL_MAINTENANCE (A3 — Miller & Cohen 2001, scales by goal relevance),
    ATTENTIONAL_CONTROL (A1 read-side — Baddeley 2003; Posner & Petersen
    1990; Cowan 2001, a soft re-weight over the full candidate set, not a
    truncation). Each stage no-ops (gain 1.0 / identity) absent its signal.
    
````

## apply_final_stages — original line 196 (docstring)

````text
    Order matters: chronological rerank only for EVENT_ORDER queries
    (ChronoRAG, Chen et al. 2025), then Titans test-time learning (Behrouz
    et al., NeurIPS 2025 — updates M/S via the paper's exact equations),
    then the TAIL mode SA fill LAST (ADR-0054 addendum) so an appended
    candidate can never be picked up and moved by an earlier stage. Tail
    fill only runs when fewer than ``top_k`` candidates were returned —
    zero store calls once the pipeline already filled ``top_k``.
    
````

## run_recall_pipeline — original line 237 (docstring)

````text
    Kept out of ``pg_recall.recall()`` itself so that function stays a
    stable, thin public-API wrapper (docstring + signature + one context
    construction) regardless of how many stages this pipeline grows — see
    pg_recall_context.py's ``RecallContext``/``fetch_and_triage`` for the
    per-parameter rationale and citations.
    
````

## module — original line 149 (comment)

````text
# Per-type pool guarantee for instruction/preference queries. ENGRAM
# (arxiv 2511.12960): typed memory pools prevent instruction/preference
# memories from being drowned out by episodic memories. Reserves 2 slots
# for tag-matched memories when intent matches (validated — BEAM 0.546
# overall, see README ablation log).
````

## module — original line 183 (comment)

````text
# Abstention gate (cortex-beam-abstain) and MMR diversity reranking are both
# DISABLED after ablation — v0.1 abstention regresses BEAM by -0.191 MRR
# (see mcp_server/core/abstention_gate.py, ERA001/#239); MMR (Carbonell &
# Goldstein, SIGIR 1998) trades precision for coverage, which our MRR-based
# BEAM evaluation penalizes (lambda=0.5: summarization 0.391->0.367). Both
# modules stay in the tree for when full QA/coverage evaluation is added;
# no call site is wired here between the typed-pool and final stages,
# matching their position in pg_recall.py before the #368-family split.
````
