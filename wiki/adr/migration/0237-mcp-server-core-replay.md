---
title: "ADR-0237 — mcp_server/core/replay.py rationale"
status: accepted
source: mcp_server/core/replay.py
---

# ADR-0237 — mcp_server/core/replay.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Two modes of operation:
````

## module — original line 5 (docstring)

````text
1. **Context restoration** (original): Format checkpoint + hot memories for
   post-compaction injection. This is the "macro-replay" after Claude Code context
   compaction.
````

## module — original line 9 (docstring)

````text
2. **SWR replay** (new): During consolidation, generate replay sequences from
   memory traces ordered by temporal/causal chains. Forward replay projects
   sequences forward (what happened after X?). Reverse replay traces backward
   from outcomes to causes (what led to Y?). Replay-dependent plasticity updates
   edge weights via STDP.
````

## module — original line 15 (docstring)

````text
SWR replay is gated by the oscillatory clock — replay only fires during
sharp-wave ripple events, not on every consolidation call. Replay prioritizes
sequences with high dopamine-modulated priority scores (see replay_selection.py).
````

## module — original line 19 (docstring)

````text
Biological adaptation note:
    Biological SWR replay uses population burst dynamics where place cell
    sequences are reactivated in compressed time (Ecker et al. 2022, eLife).
    This code approximates replay by building sequences from entity-overlap
    and temporal ordering, not from population-level burst detection. The
    compression ratio (~20x, Davidson et al. 2009) is applied to STDP timing
    in replay_execution.py.
````

## module — original line 27 (docstring)

````text
References:
    Foster DJ, Wilson MA (2006) Reverse replay of behavioural sequences
        in hippocampal place cells during the awake state. Nature 440:680-683
    Diba K, Buzsaki G (2007) Forward and reverse hippocampal place-cell
        sequences during ripples. Nature Neurosci 10:1241-1242
    Davidson TJ, Kloosterman F, Wilson MA (2009) Hippocampal replay of
        extended experience. Neuron 63:497-507
    Ecker A et al. (2022) Hippocampal sharp wave-ripples and the associated
        sequence replay emerge from structured synaptic interactions. eLife
    Nelli S et al. (2025) Large SWRs promote hippocampo-cortical reactivation.
        Neuron (in press)
````

## module — original line 39 (docstring)

````text
This module is the public API. Implementation is split across:
    - replay_types.py — Data types (ReplayDirection, ReplayEvent, etc.)
    - replay_formatting.py — Context restoration and micro-checkpoint detection
    - replay_execution.py — Sequence building and STDP pair extraction
    - replay_selection.py — Priority scoring and sequence selection
````

## module — original line 45 (docstring)

````text
Pure business logic — no I/O. Storage operations are handled by the caller.

````

## module — original line 75 (comment)

````text
# Sequences above this priority emit a schema-extraction signal.
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````
