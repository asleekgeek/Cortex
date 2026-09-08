---
title: "ADR-0189 — mcp_server/core/hierarchical_predictive_coding.py rationale"
status: accepted
source: mcp_server/core/hierarchical_predictive_coding.py
---

# ADR-0189 — mcp_server/core/hierarchical_predictive_coding.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Orchestrates the 3-level predictive hierarchy (sensory, entity, schema)
and computes combined free energy as the novelty signal for the write gate.
````

## module — original line 6 (docstring)

````text
This module composes signals from predictive_coding_signals and gate logic
from predictive_coding_gate. All public names are re-exported here for
backward compatibility.
````

## module — original line 10 (docstring)

````text
References:
    Friston K (2005) A theory of cortical responses.
        Phil Trans R Soc B 360:815-836
    Friston K, Kiebel S (2009) Predictive coding under the free-energy
        principle. Phil Trans R Soc B 364:1211-1221
    Feldman H, Friston K (2010) Attention, uncertainty, and free-energy.
        Front Hum Neurosci 4:215
    Yu AJ, Dayan P (2005) Uncertainty, neuromodulation, and attention.
        Neuron 46:681-692
````

## module — original line 20 (docstring)

````text
Pure business logic -- no I/O.

````

## _level_precisions — original line 93 (docstring)

````text
    Friston: each level's contribution to total free energy is scaled by its
    precision (inverse variance), not a fixed prior. Falls back to unit
    precision when no domain precision-error history exists.
    
````

## _aggregate_novelty — original line 142 (docstring)

````text
    Total free energy is the precision-weighted sum F = Sum_i pi_i * F_i
    (Friston 2005 eq. 7; Friston & Kiebel 2009) -- additive across levels, each
    weighted by its cross-level precision pi_i. No fixed cross-level prior is
    used; NE amplifies all precisions and ACh shifts the bottom-up/top-down
    ratio via ``neuromodulate_precisions``.
    
````

## _forward_model_error — original line 170 (docstring)

````text
    Treats the mean sensory-feature activation of the recent memories as a
    scalar *trajectory*, builds the one-step forward model over it
    (forward_model.run_forward_model), and returns |residual| of the new
    content's own mean activation against that model's one-step prediction — a
    non-negative "the dynamics did not predict this step" surplus. Zero when
    there is no history or the step fell within the model's deadband.
````

## compute_hierarchical_novelty — original line 208 (docstring)

````text
    ``include_forward_model`` (B3, default False → behaviour byte-identical to
    the pre-B3 scorer) opts in to adding a small cerebellar forward-model
    corrective-error term to total free energy before the novelty sigmoid. Even
    when opted in, the term is suppressed to 0.0 under
    ``CORTEX_ABLATE_FORWARD_MODEL=1`` (Mechanism.FORWARD_MODEL), so the ablation
    condition reproduces the include_forward_model=False score exactly.
    
````

## module — original line 66 (comment)

````text
# -- Precision-weighted level combination --------------------------------------
#
# Friston's free energy is the precision-weighted sum of squared prediction
# errors across the hierarchy: F = Sum_i pi_i * eps_i^2 (Friston 2005;
# Friston & Kiebel 2009). Cross-level contributions are weighted by PRECISION
# (inverse variance, encoded as the synaptic gain on error units --
# Feldman & Friston 2010), NOT by a fixed prior. Precision is neuromodulated
# by NE (global gain) and ACh (bottom-up vs top-down ratio -- Yu & Dayan 2005)
# inside ``neuromodulate_precisions``. There are therefore deliberately no free
# cross-level weight constants in this module: the combination is derived
# entirely from the precision values. (Earlier revisions used a fixed prior
# [0.30, 0.35, 0.35] plus a duplicate ACh-weight transform; both were ungrounded
# borrowings of the Friston label and have been removed in favour of the
# precision-derived sum.)
````

## module — original line 81 (comment)

````text
# source: PrecisionState default (predictive_coding_gate.py) -- unit precision
# (variance 1.0) for a domain with no observed prediction-error history.
````

## module — original line 148 (comment)

````text
# strict=True: exactly one precision per level -- a length mismatch would
# silently drop a level's free energy from the total, corrupting the gate.
````

## module — original line 154 (comment)

````text
# source: engineering (logistic squash of unbounded free energy -> [0,1] so
# the gate sees a comparable novelty score); NOT from Friston. Steepness 3.0
# and midpoint 0.5 are uncalibrated defaults -- calibration pending
# (benchmarks/gate_precision/run_benchmark.py). The additive precision-
# weighted free-energy aggregation above is the Fristonian part; this
# mapping is a presentation transform only.
````
