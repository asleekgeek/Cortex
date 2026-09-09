---
title: "ADR-0154 — mcp_server/core/coupled_neuromodulation.py rationale"
status: accepted
source: mcp_server/core/coupled_neuromodulation.py
---

# ADR-0154 — mcp_server/core/coupled_neuromodulation.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Orchestrates the 4-channel neuromodulatory system where channels influence each
other and gate downstream mechanisms. Individual channel computations live in
neuromodulation_channels.py; this module owns NeuromodulatoryState, the update
orchestrator, downstream modulation functions, and serialization.
````

## module — original line 8 (docstring)

````text
Downstream gating (engineering design, not from Doya 2002):
  DA -> gates cascade.py stage advancement (protein synthesis proxy)
  DA -> modulates LTP rate (reward-dependent learning — qualitatively from Schultz)
  NE -> modulates write gate threshold (arousal -> lower bar)
  ACh -> driven by theta phase (encoding/retrieval — from Hasselmo 2005)
  5-HT -> modulates spreading breadth (exploration — loosely inspired by Dayan)
````

## module — original line 15 (docstring)

````text
NOTE: Doya (2002) maps DA→discount factor, NE→inverse temperature,
ACh→learning rate, 5-HT→time horizon. Our downstream mapping is different.
See neuromodulation_channels.py for detailed departure documentation.
````

## module — original line 19 (docstring)

````text
Composite modulation uses Dawes (1979) equal-weight combination: all four
channels averaged with weight 1/4. Dawes showed equal weights match or beat
optimized regression weights when k < 10 predictors and training data is
limited — one of the most replicated findings in decision science.
````

## module — original line 24 (docstring)

````text
Downstream modulation functions use proportional gain: base * (channel / baseline),
where baseline = 1.0. This is standard gain modulation — output scales linearly
with the modulatory signal relative to its resting state.
````

## module — original line 28 (docstring)

````text
References:
    Dawes RM (1979) The robust beauty of improper linear models in decision
        making. American Psychologist 34(7):571-582
````

## module — original line 32 (docstring)

````text
Pure business logic — no I/O.

````

## NeuromodulatoryState — original line 57 (docstring)

````text
    DA in [0, 3] (asymmetric per Schultz 1997: burst ~4-6x baseline).
    NE, ACh, 5-HT in [0, 2] with 1.0 = baseline (no modulation).
    
````

## compute_cascade_gate — original line 195 (docstring)

````text
DA gates consolidation advancement. Threshold 0.7 is hand-tuned.
````

## compute_composite_modulation — original line 203 (docstring)

````text
Compute composite modulation via Dawes (1979) equal-weight combination.
````

## compute_composite_modulation — original line 205 (docstring)

````text
    Dawes showed equal weights match or beat optimized regression weights when
    k < 10 predictors and training data is limited. DA is in [0, 3], the other
    three channels in [0, 2] (all with 1.0 = baseline). DA's wider range gives
    it up to ~1.5x the swing of the other channels in the equal-weight average.
    
````

## module — original line 190 (comment)

````text
# source: hand-tuned threshold documented in compute_cascade_gate docstring
````

## module — original line 217 (comment)

````text
# Dawes (1979): equal weights for k=4 channels
````
