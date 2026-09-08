---
title: "ADR-0276 — mcp_server/core/synaptic_plasticity_hebbian.py rationale"
status: accepted
source: mcp_server/core/synaptic_plasticity_hebbian.py
---

# ADR-0276 — mcp_server/core/synaptic_plasticity_hebbian.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
BCM theory (Bienenstock, Cooper & Munro 1982, "Theory for the development
of neuron selectivity", J Neuroscience 2:32-48):
  phi(c, theta_m) = c * (c - theta_m)
  dw/dt = phi(c, theta_m) * d
  theta_m = E[c^2]  (sliding threshold)
````

## module — original line 9 (docstring)

````text
  When c > theta_m: phi > 0 → LTP
  When 0 < c < theta_m: phi < 0 → LTD
  theta_m slides up with high activity, down with low activity.
````

## module — original line 13 (docstring)

````text
STDP (Bi & Poo 1998, "Synaptic modifications in cultured hippocampal
neurons", J Neuroscience 18:10464-10472):
  Pre-before-post (dt > 0): delta_w = A+ * exp(-dt/tau+)
  Post-before-pre (dt < 0): delta_w = -A- * exp(dt/tau-)
  With A+ > A-, tau+ ≈ 17ms, tau- ≈ 34ms (biological).
  Adapted to hours timescale: tau+ = tau- = 24h.
````

## module — original line 20 (docstring)

````text
Constants: _LTP_RATE, _LTD_RATE are overall scaling factors (hand-tuned).
STDP amplitudes A+/A- maintain the A+ > A- asymmetry from Bi & Poo.
Time constants are adapted from ms to hours (documented adaptation).
````

## module — original line 24 (docstring)

````text
Pure business logic — no I/O.

````

## compute_bcm_phi — original line 58 (docstring)

````text
    Bienenstock, Cooper & Munro (1982), Eq. 3.
    Returns positive for LTP (c > theta_m), negative for LTD (0 < c < theta_m).
    
````

## compute_ltp — original line 75 (docstring)

````text
    phi(c, theta_m) = c * (c - theta_m) — quadratic, per BCM 1982.
    Only applies potentiation (phi > 0); use compute_ltd for depression.
    
````

## compute_ltd — original line 95 (docstring)

````text
    Two mechanisms:
    1. Activity-based (BCM 1982): phi(c, theta_m) < 0 when 0 < c < theta_m.
       dw = ltd_rate * phi(c, theta_m).
    2. Inactivity-based (fallback): logarithmic decay for edges with no
       recent co-access. This is engineering heuristic, not from BCM —
       BCM requires postsynaptic activity for LTD.
    
````

## update_bcm_threshold — original line 120 (docstring)

````text
BCM sliding threshold: theta_m = E[c^2] (BCM 1982, Eq. 5).
````

## module — original line 45 (comment)

````text
# Coincidence window: |dt| below this many hours is treated as simultaneous,
# so STDP neither potentiates nor depresses.
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## module — original line 176 (comment)

````text
# No-op identity: zero weight change but the result-shape contract
# (every dict carries `action`, `weight`, `delta`) must hold so
# downstream `_apply_updates` in handlers/consolidation/plasticity.py
# doesn't KeyError. Pre-fix returned raw edges, which broke the
# cycle silently with a logged WARNING and dropped the row's
# plasticity contribution.
````
