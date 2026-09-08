---
title: "ADR-0232 — mcp_server/core/query_decomposition.py rationale"
status: accepted
source: mcp_server/core/query_decomposition.py
---

# ADR-0232 — mcp_server/core/query_decomposition.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Routes classified queries to retrieval strategies and decomposes complex
queries into sub-queries via regex entity extraction.
````

## module — original line 6 (docstring)

````text
NOTE: Previously cited IRCoT (ACL 2023) and HippoRAG (NeurIPS 2024).
IRCoT decomposes queries via iterative LLM chain-of-thought reasoning.
HippoRAG uses personalized PageRank over a knowledge graph. This module
does neither — it uses regex to extract CamelCase identifiers, file
paths, backtick-quoted terms, and multi-word proper nouns. Citations
removed per zetetic standard.
````

## module — original line 13 (docstring)

````text
The intent-based routing (route_query) is useful engineering but not from
any specific paper. Entity extraction and sub-query generation are regex
heuristics. Stop word list and sub-query limit of 6 are hand-tuned.
````

## module — original line 17 (docstring)

````text
Pure business logic — no I/O.

````

## generate_sub_queries — original line 199 (docstring)

````text
    For multi-entity queries, creates per-entity sub-queries.
    For complex queries, extracts quoted phrases and keyword combinations.
    This is regex heuristic extraction, not LLM-based decomposition.
    
````

## module — original line 151 (comment)

````text
# Keywords of length <= 2 are ignored as noise.
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## module — original line 156 (comment)

````text
# Number of leading keywords combined into a fallback sub-query.
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````
