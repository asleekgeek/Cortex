---
title: "ADR-0848 — benchmarks/locomo/run_benchmark.py rationale"
status: accepted
source: benchmarks/locomo/run_benchmark.py
---

# ADR-0848 — benchmarks/locomo/run_benchmark.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 1 (docstring)

````text
LoCoMo benchmark runner for Cortex memory system.
````

## module — original line 3 (docstring)

````text
LoCoMo (Maharana et al., ACL 2024): 10 conversations, 1,986 QA pairs, 5 categories.
Uses the production PostgreSQL + pgvector retrieval pipeline.
````

## module — original line 6 (docstring)

````text
Run:
    python3 benchmarks/locomo/run_benchmark.py [--limit N] [--verbose]
                                               [--with-consolidation]
                                               [--ablate MECH]
                                               [--results-out PATH]

````

## run_benchmark — original line 179 (docstring)

````text
Run the LoCoMo benchmark using production PG retrieval.
````

## module — original line 41 (comment)

````text
# source: structural — the K in the reported R@5 / R@10 metrics (the "top 10"
# the missed-question listing reports is the same cutoff)
````

## module — original line 207 (comment)

````text
# Capture reproducibility sidecar once at benchmark start.
````

## module — original line 233 (comment)

````text
# Clean up previous conversation, load new sessions
````

## module — original line 247 (comment)

````text
# Consolidation pass between session-load and QA. Off by default
# to preserve historical reproducibility. ON exercises the
# consolidation-only mechanisms (CASCADE, INTERFERENCE,
# HOMEOSTATIC_PLASTICITY, SYNAPTIC_PLASTICITY,
# MICROGLIAL_PRUNING, TWO_STAGE_MODEL, EMOTIONAL_DECAY,
# TRIPARTITE_SYNAPSE, SCHEMA_ENGINE) so per-mechanism ablation
# deltas become attributable on the longitudinal benchmark.
````

## module — original line 431 (comment)

````text
# Export ablation env var BEFORE any handler/store import touches it. The
# ablation.is_disabled reads os.environ on every call, so setting it here
# is sufficient as long as we do it before run_benchmark.
````
