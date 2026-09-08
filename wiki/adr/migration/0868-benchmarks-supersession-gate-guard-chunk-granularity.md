---
title: "ADR-0868 — benchmarks/supersession_gate/guard_chunk_granularity.py rationale"
status: accepted
source: benchmarks/supersession_gate/guard_chunk_granularity.py
---

# ADR-0868 — benchmarks/supersession_gate/guard_chunk_granularity.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 1 (docstring)

````text
REGRESSION GUARD A1 (read-only): the committed supersede gate forms ZERO
edges on LME-S KU *after structure-aware decomposition* into chunks.
````

## module — original line 4 (docstring)

````text
Promoted from /tmp probe 2026-06-13 (investigation session fba48610). Locks the
second falsification layer of the CLOSED KU-via-supersession thread.
````

## module — original line 7 (docstring)

````text
Candidate A premise (Mem0 arxiv 2504.19413 / Supermemory): the jaccard>0.5 gate
is calibrated for atomic facts, not whole 50-turn sessions. The session-level
guard proved 0 edges; this re-runs the EXACT same gate over the production
decomposer's chunks (memory_decomposer.decompose_memory, turn-pair chunks)
instead of whole sessions, to rule out that decomposition alone unlocks edges.
````

## module — original line 13 (docstring)

````text
Gate (identical to remember_helpers.py:344-360):
    cosine sim >= 0.85 (curation.MERGE_THRESHOLD)
    AND jaccard word-overlap > 0.5
    AND curation.detect_contradictions(new, [cand]) non-empty
````

## module — original line 18 (docstring)

````text
Cross-session pairs only (KU supersession updates a fact across sessions).
No DB writes, no recall change.
````

## module — original line 21 (docstring)

````text
PASS criterion (proven 2026-06-13, finding 4197880): full_gate == 0.
Exit 0 on PASS, 1 on regression (any edge forms).
````

## module — original line 24 (docstring)

````text
Run: Cortex/.venv/bin/python3 benchmarks/supersession_gate/guard_chunk_granularity.py

````

## module — original line 42 (comment)

````text
# source: structural — an edge needs a pair of chunks to compare
````

## module — original line 45 (comment)

````text
# Cap on the worked examples printed for a regression.
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## module — original line 170 (comment)

````text
# Regression gate: proven finding is full_gate == 0.
````
