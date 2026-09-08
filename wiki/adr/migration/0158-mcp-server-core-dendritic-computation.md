---
title: "ADR-0158 — mcp_server/core/dendritic_computation.py rationale"
status: accepted
source: mcp_server/core/dendritic_computation.py
---

# ADR-0158 — mcp_server/core/dendritic_computation.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 1 (docstring)

````text
Dendritic computation — two-layer neuron model after Poirazi, Brannon & Mel (2003).
````

## module — original line 3 (docstring)

````text
Implements the pyramidal neuron as a two-layer network:
````

## module — original line 5 (docstring)

````text
  Layer 1 — Dendritic branch subunit function:
    s(n) = 1 / (1 + exp((3.6 - n) / 2)) + 0.30*n + 0.0114*n^2
````

## module — original line 8 (docstring)

````text
    where n = number of active synapses on the branch.
    Half-activation at n = 3.6 synapses, slope factor 2.0.
    Sigmoid + linear + quadratic terms capture the full nonlinearity
    (NMDA plateau + cooperative unblocking + voltage-gated amplification).
````

## module — original line 13 (docstring)

````text
  Layer 2 — Soma output nonlinearity:
    g(x) = 0.96 * x / (1 + 1509 * exp(-0.26 * x))
````

## module — original line 16 (docstring)

````text
    where x = weighted sum of branch outputs.
    Effective threshold emerges around x ~ 20-30.
````

## module — original line 19 (docstring)

````text
Constants 3.6, 2.0, 0.30, 0.0114, 0.96, 1509, 0.26 are all from
Poirazi P, Brannon T, Mel BW (2003) "Pyramidal Neuron as a Two-Layer
Neural Network." Neuron 37:989-999, Figure 3 and Equation fits.
````

## module — original line 23 (docstring)

````text
Branch clustering (dendritic_clusters.py) and cluster priming are
engineering heuristics inspired by Kastellakis (2015) but not direct
implementations of any specific paper equation.
````

## module — original line 27 (docstring)

````text
Pure business logic — no I/O.

````

## branch_subunit — original line 110 (docstring)

````text
Poirazi (2003) dendritic branch subunit function.
````

## branch_subunit — original line 110 (mixed-contract-rationale)

````text
    Args:
        n: Number of active synapses on the branch. In our system this
           is the number of co-retrieved memories on the branch.
        half_activation: Sigmoid midpoint (paper: 3.6).
        slope: Sigmoid slope factor (paper: 2.0).
        linear_coeff: Linear term coefficient (paper: 0.30).
        quadratic_coeff: Quadratic term coefficient (paper: 0.0114).
````

## soma_output — original line 145 (docstring)

````text
Poirazi (2003) soma output nonlinearity.
````

## soma_output — original line 145 (mixed-contract-rationale)

````text
    Args:
        x: Weighted sum of branch subunit outputs.
        scale: Output scaling (paper: 0.96).
        steepness: Exponential steepness (paper: 0.26).
        offset: Exponential offset controlling threshold (paper: 1509).
````

## compute_dendritic_integration — original line 179 (docstring)

````text
Two-layer dendritic integration after Poirazi, Brannon & Mel (2003).
````

## compute_cluster_priming — original line 237 (docstring)

````text
    Engineering heuristic, not from Poirazi (2003). Inspired by the general
    principle that co-localized synapses prime each other (Kastellakis 2015),
    but the exponential decay with list-position distance is a practical
    approximation, not a biological model.
````

## _apply_plasticity_events — original line 276 (docstring)

````text
    Engineering heuristic for branch-specific plasticity modulation.
    The concept of branch-specific plasticity is supported by Kastellakis
    (2015) and Losonczy et al. (2008), but the specific boost/reduction
    constants are hand-tuned, not from any paper.
    
````

## update_branch_plasticity — original line 300 (docstring)

````text
    Engineering heuristic. LTP increases plasticity; LTD decreases it.
    Passive decay toward 0.5 (homeostatic baseline).
````

## module — original line 35 (comment)

````text
# ── Poirazi (2003) Constants ─────────────────────────────────────────────
# All from Neuron 37:989-999, Figure 3 subunit fit and soma nonlinearity.
````

## module — original line 54 (comment)

````text
# ── Engineering Constants (no paper) ─────────────────────────────────────
````

## module — original line 60 (comment)

````text
# Guard for math.exp arguments.
# source: structural — IEEE 754 double exp() underflows to 0.0 below
# ≈ -745; -500 is a conservative pre-existing cutoff, extracted unchanged
# (#197 family 3)
````

## module — original line 66 (comment)

````text
# source: structural — a sigmoid crosses 0.5 exactly at its
# half-activation point, so >0.5 means n > SUBUNIT_HALF_ACTIVATION
````

## module — original line 99 (comment)

````text
# ── Layer 1: Dendritic Branch Subunit — Poirazi (2003) Eq. ──────────────
````

## module — original line 135 (comment)

````text
# ── Layer 2: Soma Output Nonlinearity — Poirazi (2003) Eq. ──────────────
````

## module — original line 162 (comment)

````text
# Guard against overflow in exp for very negative arguments.
# When x is large, exp(-0.26*x) -> 0 and denominator -> 1.
````

## module — original line 209 (comment)

````text
# Weight by mean retrieval score so higher-quality retrievals
# produce stronger branch output.
````

## module — original line 226 (comment)

````text
# ── Cluster Priming (Engineering Heuristic) ─────────────────────────────
````

## module — original line 264 (comment)

````text
# ── Branch-Specific Plasticity (Engineering Heuristic) ──────────────────
````
