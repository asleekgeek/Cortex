---
title: "ADR-0212 — mcp_server/core/oscillatory_phases.py rationale"
status: accepted
source: mcp_server/core/oscillatory_phases.py
---

# ADR-0212 — mcp_server/core/oscillatory_phases.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Theta gating implements Hasselmo's piecewise model (2002) via sigmoid:
  gate(phase) = 1 / (1 + exp(-k * (phase - 0.5)))
  enc(phase)  = 1.0 - gate(phase) * X       (EC->CA1 gain)
  ret(phase)  = (1-X) + gate(phase) * X     (CA3->CA1 gain)
  ach(phase)  = 1.0 - gate(phase) * (1 - ach_baseline)
````

## module — original line 9 (docstring)

````text
X=0.7 from Hasselmo 2002 Table 1; k=20 for sharp differentiable transition.
At k->inf this recovers the paper's discrete piecewise switch.
enc + ret = 2 - X = 1.3 at all phases (zero-sum tradeoff).
````

## module — original line 13 (docstring)

````text
Gamma: 7-item binding per theta cycle (Lisman & Jensen 2013).
SWR: consolidation windows for replay-driven plasticity (Buzsaki 2015).
````

## module — original line 16 (docstring)

````text
References:
    Hasselmo, Bodelon & Wyble (2002) Neural Computation 14:793-817
    Hasselmo (2005) Hippocampus 15:936-949
    Lisman & Jensen (2013) Neuron 77:1002-1016
    Buzsaki (2015) Hippocampus 25:1073-1188
    Olafsdottir et al. (2018) Curr Biol 28:R37-R50
````

## module — original line 23 (docstring)

````text
Pure business logic -- no I/O.

````

## _sigmoid_gate — original line 141 (docstring)

````text
    At k->inf recovers Hasselmo 2002 piecewise step function.
    
````

## compute_encoding_strength — original line 177 (docstring)

````text
    Hasselmo 2002: enc(phase) = 1.0 - gate(phase) * X.
    
````

## compute_retrieval_strength — original line 187 (docstring)

````text
    Hasselmo 2002: ret(phase) = (1-X) + gate(phase) * X.
    Complementary: enc + ret = 2 - X = 1.3 at all phases.
    
````

## compute_ach_from_phase — original line 198 (docstring)

````text
    Hasselmo 2005: ach(phase) = 1.0 - gate(phase) * (1 - ach_baseline).
    
````

## _compute_swr_probability — original line 240 (docstring)

````text
    Combines operation count, importance accumulation, and time pressure
    into a weighted probability score. Weights and scaling factors are
    hand-tuned engineering choices.
    
````

## should_generate_swr — original line 261 (docstring)

````text
    Deterministic threshold (no randomness). Thresholds are hand-tuned.
    
````

## compute_replay_priority — original line 295 (docstring)

````text
    Prioritizes: high importance, moderate heat, high surprise,
    low access count (under-rehearsed), and recent memories.
    Based on Olafsdottir et al. (2018).
````

## module — original line 56 (comment)

````text
# -- Hasselmo Piecewise Gating Parameters -------------------------------------
````

## module — original line 58 (comment)

````text
# Suppression magnitude X: fraction of transmission reduction in the
# suppressed pathway. X=0.7 means 70% suppression of CA3->CA1 during
# encoding (or EC->CA1 during retrieval). Derived from Hasselmo, Bodelon
# & Wyble (2002), Table 1, which reports best performance at high
# cholinergic suppression levels.
````

## module — original line 65 (comment)

````text
# Sigmoid steepness for the encoding/retrieval transition. Higher values
# approach Hasselmo's ideal piecewise (step function) switch. k=20 gives
# a sharp transition where gate(0.25) < 0.01 and gate(0.75) > 0.99,
# making the plateau regions effectively flat as in the piecewise model.
````

## module — original line 71 (comment)

````text
# Tonic ACh floor during retrieval phase (Hasselmo 2005). During encoding,
# ACh is near 1.0; during retrieval it drops to this baseline.
````

## module — original line 78 (comment)

````text
# Gamma capacity per theta cycle (Lisman & Jensen 2013: ~7 items)
````

## module — original line 81 (comment)

````text
# -- SWR Constants (engineering choices, not from any specific paper) ----------
# These control the discrete SWR state machine for consolidation scheduling.
# No published paper provides these specific values; they are tuned for
# reasonable behavior in a memory system operating at hours/days timescale.
````

## module — original line 98 (comment)

````text
# Minimum operations since the last SWR before another may trigger.
# source: hand-tuned (see should_generate_swr docstring: "Thresholds are
# hand-tuned")
````

## module — original line 103 (comment)

````text
# Clamp for math.exp arguments to avoid overflow.
# source: structural — IEEE 754 double exp() overflows above ≈ 709 and
# underflows below ≈ -745; ±500 is a conservative pre-existing cutoff,
# extracted unchanged (#197 family 3)
````

## module — original line 109 (comment)

````text
# source: structural — half of the normalized theta cycle; encoding is
# [0, 0.5) and retrieval [0.5, 1.0) per classify_theta_phase docstring
````

## module — original line 135 (comment)

````text
# -- Sigmoid Gate (Hasselmo piecewise model) -----------------------------------
````

## module — original line 144 (comment)

````text
# Clamp to avoid overflow in exp()
````
