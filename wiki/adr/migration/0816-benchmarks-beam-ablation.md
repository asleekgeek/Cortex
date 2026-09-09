---
title: "ADR-0816 — benchmarks/beam/ablation.py rationale"
status: accepted
source: benchmarks/beam/ablation.py
---

# ADR-0816 — benchmarks/beam/ablation.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 1 (docstring)

````text
BEAM ablation study for engineering constants.
````

## module — original line 3 (docstring)

````text
Tests parameter variations on the BEAM benchmark to find empirically
justified values for constants that currently lack paper backing.
````

## module — original line 6 (docstring)

````text
Parameters under test:
  1. rerank_alpha: CE vs first-stage blend weight (completed: 0.70 optimal)
  2. signal_weights: fts, heat, ngram weight combinations
  3. gate_threshold: CE confidence gate for abstention
````

## module — original line 11 (docstring)

````text
Each ablation runs on the full BEAM 100K split (20 conversations, 395 Qs).
Results are printed as a table and written to ablation_results.json.

````

## module — original line 41 (comment)

````text
# Minimum turn length for a turn to seed an 80-char prefix match key.
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## module — original line 46 (comment)

````text
# Top-1 retrieval score below which the system counts as having found nothing
# confident (abstention success).
# source: engineering heuristic documented at benchmarks/beam/run_benchmark.py
# — "BEAM paper uses LLM-as-judge to evaluate abstention quality. We approximate
# by checking if top retrieval score is low"
````

## module — original line 53 (comment)

````text
# Minimum answer length for an answer substring match to carry signal.
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## module — original line 58 (comment)

````text
# source: structural — the K in the reported Recall@5 / Recall@10 metrics
````

## module — original line 233 (comment)

````text
# The recall function computes weights internally via compute_pg_weights().
# We can't override weights directly through the recall() API — the weights
# are computed from intent classification. Instead, we'll test with rerank
# disabled to isolate the PG fusion signal, then with rerank enabled.
````
