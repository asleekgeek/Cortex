---
title: "ADR-0850 — benchmarks/longmemeval/run_benchmark.py rationale"
status: accepted
source: benchmarks/longmemeval/run_benchmark.py
---

# ADR-0850 — benchmarks/longmemeval/run_benchmark.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 1 (docstring)

````text
LongMemEval benchmark for Cortex memory system.
````

## module — original line 3 (docstring)

````text
Runs the LongMemEval benchmark (Wu et al., ICLR 2025) against the
production PostgreSQL + pgvector retrieval pipeline. 500 questions
across 6 categories, each embedded in ~50 sessions (~115k tokens).
````

## module — original line 7 (docstring)

````text
Methodology:
  1. For each question, load all haystack sessions into PostgreSQL
     via BenchmarkDB (one memory per session, with full content).
  2. Set timestamps to match the original session dates.
  3. Run production recall_memories() PL/pgSQL + FlashRank reranking.
  4. Check if retrieved results contain the answer session(s).
  5. Compute MRR and Recall@K at session level.
````

## module — original line 15 (docstring)

````text
Run:
    python3 benchmarks/longmemeval/run_benchmark.py [--limit N] [--variant oracle|s]

````

## parse_longmemeval_date — original line 48 (docstring)

````text
Parse LongMemEval date format '2023/04/10 (Mon) 17:50' to ISO 8601.
````

## run_benchmark — original line 156 (docstring)

````text
Run the full LongMemEval benchmark using production PG retrieval.
````

## module — original line 51 (comment)

````text
# noqa DTZ007: the format string has no %z because the source data
# never carries one; the very next line stamps tzinfo=UTC, so the
# value this function returns is always aware.
````

## module — original line 124 (comment)

````text
# ── Main Benchmark ───────────────────────────────────────────────────────────
````

## module — original line 138 (comment)

````text
# Imported lazily so callers that never pass --with-consolidation don't
# incur the import cost (and can't be broken by handler-side changes).
````

## inline — original line 140 (directive-rationale)

````text
# noqa: PLC0415 — documented deferral: only --with-consolidation callers pay the handler-stack import cost
````

## module — original line 199 (comment)

````text
# Capture reproducibility sidecar once at benchmark start.
````

## module — original line 250 (comment)

````text
# Clean up previous question's data, load new haystack
````

## module — original line 276 (comment)

````text
# Consolidation warmup pass (Feynman audit fix). Off by default to
# preserve historical run reproducibility. When ON, exercises the 9
# consolidation-only mechanisms (CASCADE, INTERFERENCE,
# HOMEOSTATIC_PLASTICITY, SYNAPTIC_PLASTICITY, MICROGLIAL_PRUNING,
# TWO_STAGE_MODEL, EMOTIONAL_DECAY, TRIPARTITE_SYNAPSE, SCHEMA_ENGINE)
# so per-mechanism ablation deltas become attributable on LME-S.
# Wall time tracked separately so per-question stats stay clean.
````

## module — original line 504 (comment)

````text
# Export ablation env var BEFORE any handler/store import touches it. The
# consolidate handler imports its sub-modules at call time, but
# mcp_server.core.ablation.is_disabled reads os.environ on every call, so
# setting it here is sufficient as long as we do it before run_benchmark.
````

## Date parser directive explanation

````text
# noqa DTZ007: the format string has no %z because the source data
````
