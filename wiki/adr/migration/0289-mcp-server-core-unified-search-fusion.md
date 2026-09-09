---
title: "ADR-0289 — mcp_server/core/unified_search_fusion.py rationale"
status: accepted
source: mcp_server/core/unified_search_fusion.py
---

# ADR-0289 — mcp_server/core/unified_search_fusion.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 1 (docstring)

````text
Phase 3 (ADR-0046) — Reciprocal Rank Fusion for unified search.
````

## module — original line 3 (docstring)

````text
Merges two (or more) ranked result lists from independent retrievers —
Cortex memory recall and AP code-symbol search — into a single list
ordered by aggregated relevance. RRF is the canonical choice for
fusing heterogeneous retrievers whose scores are not comparable:
````

## module — original line 8 (docstring)

````text
    score(d) = sum_{r in retrievers} 1 / (K + rank_r(d))
````

## module — original line 10 (docstring)

````text
Source: Cormack, Clarke, Büttcher (2009) "Reciprocal Rank Fusion
Outperforms Condorcet and Individual Rank Learning Methods", SIGIR.
````

## module — original line 13 (docstring)

````text
K defaults to 60 per the paper's experimental finding. Cortex already
uses K=60 for WRRF inside ``pg_recall`` (``settings.WRRF_K``), so
Phase 3 is consistent with the rest of the retrieval stack.
````

## module — original line 17 (docstring)

````text
Pure logic — no I/O. Each input list is a list of ``{id, ...}`` dicts,
and the output is a re-ranked list enriched with ``rrf_score`` and
``source_ranks`` (per-retriever rank for transparency).

````

## fuse — original line 47 (docstring)

````text
    ``ranked_lists`` is ``[(source_name, results), ...]``. Each result
    must expose an ``id_key`` field used as the identity for fusion —
    duplicates across lists are collapsed. When a result appears in
    more than one list, the merged record keeps the first-seen body
    but records per-source ranks so the UI can explain *why* it ranked
    where it did.
````

## fuse — original line 54 (docstring)

````text
    Items lacking ``id_key`` are skipped — silently, because a missing
    id means the retriever produced something we can't dedupe safely.
````

## module — original line 26 (comment)

````text
# Matches ``pg_recall`` default; see Cormack (2009) for the empirical
# basis. Increasing K flattens the rank weight so near-top items of
# different retrievers count roughly the same; decreasing K sharpens
# the top-of-list bias.
````
