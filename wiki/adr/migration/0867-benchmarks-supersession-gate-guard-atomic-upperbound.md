---
title: "ADR-0867 — benchmarks/supersession_gate/guard_atomic_upperbound.py rationale"
status: accepted
source: benchmarks/supersession_gate/guard_atomic_upperbound.py
---

# ADR-0867 — benchmarks/supersession_gate/guard_atomic_upperbound.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 1 (docstring)

````text
REGRESSION GUARD A2 (read-only): UPPER BOUND on supersede-gate firing over
ATOMIC facts cleanly extracted from the genuine KU update pairs.
````

## module — original line 4 (docstring)

````text
Promoted from /tmp probe 2026-06-13 (investigation session fba48610). Locks the
third (decisive-mechanism) falsification layer of the CLOSED
KU-via-supersession thread.
````

## module — original line 8 (docstring)

````text
These 12 (old, new) pairs are the atomic facts a Mem0/Supermemory-style LLM
extractor would pull from each KU question's two answer sessions — hand-extracted
faithfully (the agent acting as the A2 extractor, which IS the A2 mechanism:
non-deterministic LLM fact extraction). This is the UPPER BOUND on A2: the real
update pair, cleanly extracted, with all session noise removed.
````

## module — original line 14 (docstring)

````text
Gate (identical to remember_helpers.py):
    cosine sim >= 0.85 (curation.MERGE_THRESHOLD)
    AND curation.compute_textual_overlap > 0.5      (jaccard)
    AND curation.detect_contradictions non-empty
````

## module — original line 19 (docstring)

````text
Proven finding (2026-06-13, finding 4197901): even at this clean upper bound the
jaccard sub-gate is SOLVED (6/12 pass sim+overlap) but detect_contradictions is
BLIND to numeric/value swaps ("three" -> "four", "27:12" -> "25:50"), so 0/12
fire the full gate. The contradiction detector — not the embedding or jaccard —
is the binding constraint that makes supersession a no-op.
````

## module — original line 25 (docstring)

````text
PASS criterion: fired == 0  (contradiction detector remains blind to value swaps;
matches the proven upper bound). A NON-zero result is NOT necessarily a bug — it
means detect_contradictions gained value-swap sensitivity, which would re-open
the A2 path. Either way a maintainer must look: exit 0 on PASS (fired==0),
1 on deviation.
````

## module — original line 31 (docstring)

````text
Run: Cortex/.venv/bin/python3 benchmarks/supersession_gate/guard_atomic_upperbound.py

````

## module — original line 159 (comment)

````text
# Regression gate: proven upper bound is fired == 0 (contradiction detector
# blind to value swaps). Any deviation means the binding constraint changed.
````
