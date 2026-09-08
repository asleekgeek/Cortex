---
title: "ADR-0825 — benchmarks/episodic/run_benchmark.py rationale"
status: accepted
source: benchmarks/episodic/run_benchmark.py
---

# ADR-0825 — benchmarks/episodic/run_benchmark.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 1 (docstring)

````text
Episodic Memories Benchmark for Cortex memory system.
````

## module — original line 3 (docstring)

````text
Tests episodic memory recall on synthetic book-like narratives
(Huet et al., ICLR 2025). Each event is a 5-tuple (date, location, entity,
content, content_detail) embedded in narrative prose.
````

## module — original line 7 (docstring)

````text
Metrics:
  - Simple Recall Score: F1 grouped by event count bins {0,1,2,3-5,6+}
  - Chronological Awareness: latest state + temporal ordering (Kendall tau)
````

## module — original line 11 (docstring)

````text
Dataset: Pre-generated from figshare.org/28244480, or generate with the
         episodic-memory-benchmark repo.
````

## module — original line 14 (docstring)

````text
Run:
    python3 benchmarks/episodic/run_benchmark.py [--events 20] [--limit N]

````

## EpisodicRetriever — original line 192 (docstring)

````text
Adapter wrapping shared BenchmarkRetriever for episodic benchmark.
````

## run_benchmark — original line 264 (docstring)

````text
Run episodic memory benchmark.
````

## module — original line 38 (comment)

````text
# source: structural — an event is the 5-tuple
# (date, location, entity, content, content_detail) documented in the module
# docstring; the first four fields are what every question is built from
````

## module — original line 44 (comment)

````text
# source: structural — "latest" and "chronological" questions need at least a
# pair of events to be non-trivial
````

## module — original line 48 (comment)

````text
# Retrieved-text length under which a bin-0 (non-existent entity) answer counts
# as a clean abstention rather than a hallucination.
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## module — original line 54 (comment)

````text
# source: Simple Recall Score bins {0,1,2,3-5,6+} documented in the module
# docstring (Huet et al., ICLR 2025)
````

## module — original line 258 (comment)

````text
# ── Main Benchmark ───────────────────────────────────────────────────────
````
