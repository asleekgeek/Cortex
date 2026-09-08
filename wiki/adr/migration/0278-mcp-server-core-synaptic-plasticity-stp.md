---
title: "ADR-0278 — mcp_server/core/synaptic_plasticity_stp.py rationale"
status: accepted
source: mcp_server/core/synaptic_plasticity_stp.py
---

# ADR-0278 — mcp_server/core/synaptic_plasticity_stp.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Tsodyks-Markram short-term plasticity (Tsodyks & Markram 1997, "The neural
code between neocortical pyramidal neurons depends on neurotransmitter
release probability", PNAS 94:719-723; Markram et al. 1998):
````

## module — original line 7 (docstring)

````text
  At each spike event:
    u_eff = u + U * (1 - u)        (facilitation: residual Ca2+ boost)
    x_new = x - u_eff * x          (depression: vesicle depletion)
````

## module — original line 11 (docstring)

````text
  Between spikes (continuous recovery):
    du/dt = -u / tau_F              (facilitation decays, tau_F ~ 530ms)
    dx/dt = (1 - x) / tau_D        (vesicles recover, tau_D ~ 130ms)
````

## module — original line 15 (docstring)

````text
  Effective release = u_eff * x (utilization * available resources)
````

## module — original line 17 (docstring)

````text
  Timescale adaptation: biological tau_F ~ 530ms, tau_D ~ 130ms
  (tau_F/tau_D ~ 4.08). Adapted to hours: tau_F = 0.5h (30min
  facilitation), tau_D = 2.0h (2h vesicle recovery), i.e. tau_F/tau_D =
  0.25 — this INVERTS the biological ordering (facilitation now shorter
  than recovery). A deliberate modeling choice for the hours-timescale
  regime (short-lived facilitation, stretched vesicle recovery), NOT a
  ratio-preserving rescale.
````

## module — original line 25 (docstring)

````text
Phase-gated plasticity: LTP/LTD magnitude is modulated by theta phase
(Hasselmo 2005). Encoding phase amplifies LTP; retrieval phase suppresses it.
````

## module — original line 28 (docstring)

````text
Leaf module: imports stdlib only. The Hebbian/STDP and stochastic modules
depend on the state, bounds, and helpers defined here; keeping this file free
of sibling imports is what makes that dependency acyclic (issue #233).
The public facade is ``mcp_server.core.synaptic_plasticity``.
````

## module — original line 33 (docstring)

````text
Pure business logic — no I/O.

````

## compute_effective_release_probability — original line 89 (docstring)

````text
Effective release: u_eff * x (Tsodyks-Markram 1997).
````

## update_short_term_dynamics — original line 121 (docstring)

````text
Tsodyks-Markram STP update (Tsodyks & Markram 1997).
````

## _recover_between_spikes — original line 156 (docstring)

````text
    Tsodyks-Markram 1997, between-spike analytical solution:
      u(t) = u0 * exp(-t / tau_F)
      x(t) = 1 - (1 - x0) * exp(-t / tau_D)
    
````

## _apply_spike — original line 175 (docstring)

````text
    Tsodyks-Markram 1997:
      u_new = u + U * (1 - u)    (residual Ca2+ increment)
      x_new = x - u_new * x      (release depletes available resources)
    
````

## phase_modulate_plasticity — original line 216 (docstring)

````text
Modulate plasticity magnitude by theta phase (Hasselmo 2005).
````

## module — original line 44 (comment)

````text
# U: baseline utilization increment per spike (Tsodyks & Markram 1997)
# Biological range: 0.15-0.5 depending on synapse type
````

## module — original line 48 (comment)

````text
# tau_F: facilitation time constant. Biological: ~530ms.
# Adapted to hours: 0.5h (30min) — residual Ca2+ decays over ~30 min.
````

## module — original line 52 (comment)

````text
# tau_D: depression recovery time constant. Biological: ~130ms.
# Adapted to hours: 2.0h — vesicle replenishment takes ~2h.
````

## module — original line 208 (comment)

````text
# -- Phase-Gated Plasticity (Hasselmo 2005) ------------------------------------
````
