---
title: "ADR-0206 — mcp_server/core/mmr_diversity.py rationale"
status: accepted
source: mcp_server/core/mmr_diversity.py
---

# ADR-0206 — mcp_server/core/mmr_diversity.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Maximal Marginal Relevance (Carbonell & Goldstein, SIGIR 1998):
iteratively selects documents maximizing relevance to query while
minimizing redundancy with already-selected documents.
````

## module — original line 7 (docstring)

````text
Activated only for SUMMARIZATION intent to improve nugget coverage
in BEAM benchmark evaluation.
````

## module — original line 10 (docstring)

````text
Pure business logic — no I/O.
````

## module — original line 12 (docstring)

````text
Citation:
    Carbonell, J. & Goldstein, J. (1998). "The Use of MMR,
    Diversity-Based Reranking for Reordering Documents and
    Producing Summaries." SIGIR 1998, pp. 335-336.

````
