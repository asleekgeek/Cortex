---
title: "ADR-0851 — benchmarks/longmemeval/run_sqlite_fallback_bench.py rationale"
status: accepted
source: benchmarks/longmemeval/run_sqlite_fallback_bench.py
---

# ADR-0851 — benchmarks/longmemeval/run_sqlite_fallback_bench.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 1 (docstring)

````text
Three-way SQLite retrieval benchmark for the #169 zero-download fallback.
````

## module — original line 3 (docstring)

````text
The production ``run_benchmark.py`` harness drives the PostgreSQL + pgvector
pipeline (``BenchmarkDB`` → ``PgMemoryStore``) and has no toggle for the
SQLite fallback path or for the embedding mode. Issue #169 changes exactly that
path, so this harness reuses the production harness's dataset loading and
scoring functions verbatim (``session_to_memory_content``,
``parse_longmemeval_date``, ``compute_heat_with_decay``, ``compute_mrr``,
``recall_at_k_binary``) but drives a fresh in-memory ``SqliteMemoryStore`` in
three embedding modes:
````

## module — original line 12 (docstring)

````text
  (a) no-vector    — memories stored with no embedding; recall uses FTS + heat
      + recency only. The floor #169 must beat.
  (b) fallback     — deterministic algorithmic embeddings (shared.algorithmic_
      embedding), zero download.
  (c) sentence-transformers — the neural encoder, when present.
````

## module — original line 18 (docstring)

````text
Adoption criterion (issue #169): the fallback (b) must beat the no-vector
baseline (a) materially. This harness reports whatever the numbers say.
````

## module — original line 21 (docstring)

````text
Run:
    python3 benchmarks/longmemeval/run_sqlite_fallback_bench.py --limit 30
````

## module — original line 24 (docstring)

````text
Bounded runs are the intended use (the neural path is untouched by #169, so
full floors are not required — see the PR). ``--limit`` and the git sha / date
are recorded in the emitted MANIFEST so the run is reproducible.

````

## _install_engine — original line 62 (docstring)

````text
    For 'fallback' a zero-download engine is forced; for
    'sentence-transformers' the real model is loaded (skipped by the caller if
    absent). Returns the engine so the caller can encode queries with the SAME
    encoder that produced the stored vectors.
    
````

## module — original line 76 (comment)

````text
# Install as the process-wide singleton the store reads for provenance
# stamping / query-space filtering (issue #169 — the singleton lives in the
# factory since the #173 seam split).
````
