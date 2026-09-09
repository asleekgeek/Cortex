---
title: "ADR-0849 — benchmarks/locomo/run_benchmark_agents.py rationale"
status: accepted
source: benchmarks/locomo/run_benchmark_agents.py
---

# ADR-0849 — benchmarks/locomo/run_benchmark_agents.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 1 (docstring)

````text
LoCoMo agent-topic benchmark — validates agent-scoped memory retrieval.
````

## module — original line 3 (docstring)

````text
Same as run_benchmark.py but assigns agent_topics to memories based on
content classification, then uses scoped recall. Compares scoped vs
unscoped retrieval to measure whether agent_topic improves precision.
````

## module — original line 7 (docstring)

````text
NOT an official benchmark — validates the agent_topic architecture.
````

## module — original line 9 (docstring)

````text
Run:
    python3 benchmarks/locomo/run_benchmark_agents.py [--limit N]

````
