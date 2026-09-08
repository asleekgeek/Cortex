---
title: "ADR-0847 — benchmarks/locomo/rrf_vs_tmm_ablation.py rationale"
status: accepted
source: benchmarks/locomo/rrf_vs_tmm_ablation.py
---

# ADR-0847 — benchmarks/locomo/rrf_vs_tmm_ablation.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Purpose: produce the within-Cortex head-to-head that the paper's fusion
justification needs. Both arms compute IDENTICAL per-signal ranked lists
(reusing the production scoring functions and the all-MiniLM-L6-v2 vector
signal); only the fusion function is swapped:
````

## module — original line 8 (docstring)

````text
  - RRF  : benchmarks.lib.fusion.wrrf_fuse  (Weighted Reciprocal Rank Fusion,
           contribution = w / (k + rank + 1), k=60 -- Cormack 2009)
  - TMM  : theoretical-min-max weighted score fusion mirroring the production
           PL/pgSQL recall_memories() in mcp_server/infrastructure/pg_schema.py
           contribution = w * (raw - m_c) / (max_c - m_c), summed over signals.
````

## module — original line 14 (docstring)

````text
Evaluation reuses the LoCoMo runner's own gold logic: retrieval unit = session,
gold = evidence target sessions, hit = first retrieved session in the gold set,
MRR = 1/rank, R@k = hit within top-k. Reranking is intentionally DISABLED so the
comparison isolates the fusion function (FlashRank blends both arms identically
and would only add noise/latency without changing what is being tested).
````

## module — original line 20 (docstring)

````text
This runs WITHOUT Postgres: signals are computed in-process over the LoCoMo
sessions, exactly as benchmarks/lib/retriever.py does. Absolute numbers will
differ from the production-PG paper figures; the RRF-vs-TMM DELTA is the result.

````

## tmm_fuse — original line 73 (docstring)

````text
Weighted theoretical-min-max score fusion (Bruch 2023 / pg_schema.py).
````

## tmm_fuse — original line 75 (docstring)

````text
    contribution(item, signal) = w * (raw - m) / (max_observed - m)
    fused = sum over signals. Mirrors the production SUM(w*raw/max) with the
    -1 min only for cosine; here all signals are non-negative so m=0.
    
````

## module — original line 40 (comment)

````text
# Import wrrf_fuse directly from the module file to avoid benchmarks.lib.__init__,
# which pulls in bench_db -> pg_store -> psycopg (Postgres, not needed here).
````

## inline — original line 60 (directive-rationale)

````text
# noqa: E501 — absolute dataset path, one token with no whitespace to split on
````

## module — original line 62 (comment)

````text
# source: structural — the K in the reported R@10 metric
````

## module — original line 65 (comment)

````text
# Theoretical minima per signal (mirrors pg_schema.py: cosine in [-1,1] -> m=-1;
# all other signals are already in [0,1] -> m=0). Our vector signal is clamped
# to [0,1] (see _score_vector using max(0.0, sim)), so m_vec=0 here too, which
# matches the effective production behaviour for non-negative cosine.
````

## inline — original line 204 (directive-rationale)

````text
# noqa: PLC0415 — optional dependency (sentence-transformers (multi-second model load)); imported where used so environments without it keep working
````

## inline — original line 245 (directive-rationale)

````text
# noqa: E501 — absolute output path, one token with no whitespace to split on
````
