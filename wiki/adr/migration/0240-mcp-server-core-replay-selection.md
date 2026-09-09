---
title: "ADR-0240 — mcp_server/core/replay_selection.py rationale"
status: accepted
source: mcp_server/core/replay_selection.py
---

# ADR-0240 — mcp_server/core/replay_selection.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Selects which replay sequences fire during an SWR burst based on a
priority score. Higher-priority sequences are replayed first.
````

## module — original line 6 (docstring)

````text
Priority formula: (avg_heat * 0.4 + sqrt(heat_variance) * 0.6) * DA_level.
This is a hand-tuned heuristic combining importance (heat) and surprise
(variance), amplified by dopamine level. No paper — engineering decision.
````

## module — original line 10 (docstring)

````text
The DA modulation captures Schultz's qualitative finding that dopamine
amplifies replay of rewarding experiences, but the specific formula is
not the Schultz/Rescorla-Wagner RPE equation.
````

## module — original line 14 (docstring)

````text
All constants (0.4/0.6 weights, threshold 0.3, max 5) are hand-tuned.
````

## module — original line 16 (docstring)

````text
Pure business logic — no I/O.

````

## compute_sequence_priority — original line 47 (docstring)

````text
    Formula: (avg_heat * 0.4 + sqrt(heat_variance) * 0.6) * DA_level.
    Heuristic combining importance (heat) and surprise (variance),
    amplified by dopamine. Weights are hand-tuned — no paper.
````

## select_replay_sequences — original line 79 (docstring)

````text
    Filters by priority threshold, then ranks by priority score. Ensures
    at least one forward and one reverse sequence if available.
    
````

## module — original line 33 (comment)

````text
# source: structural — heat variance is degenerate on fewer than two events,
# so shorter sequences score 0.0.
````
