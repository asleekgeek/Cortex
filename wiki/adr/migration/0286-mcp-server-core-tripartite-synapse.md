---
title: "ADR-0286 — mcp_server/core/tripartite_synapse.py rationale"
status: accepted
source: mcp_server/core/tripartite_synapse.py
---

# ADR-0286 — mcp_server/core/tripartite_synapse.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Owns AstrocyteTerritory, territory update orchestration, and serialization.
Calcium dynamics, D-serine modulation, and metabolic computations live in
tripartite_calcium.py (see its docstring for detailed simplification notes).
````

## module — original line 7 (docstring)

````text
Key mechanisms:
  1. Territory coverage: each astrocyte covers a cluster of memories.
     Based on Perea (2009) description of astrocyte functional domains —
     each astrocyte enwraps and modulates a set of nearby synapses.
  2. Calcium dynamics: three regimes from Perea (2009):
     - Quiescent: low Ca2+, no modulation
     - Facilitation: moderate Ca2+, D-serine potentiates LTP
     - Depression: high Ca2+, glutamate causes heterosynaptic depression
  3. Cross-synapse coordination via calcium waves.
  4. Metabolic gating: active territories get more resources.
````

## module — original line 18 (docstring)

````text
References:
    Perea G, Navarrete M, Araque A (2009) Tripartite synapses: astrocytes
        process and control synaptic information. Trends Neurosci 32:421-431
        — Three-regime qualitative model: quiescent/facilitation/depression.
    De Pitta M et al. (2009) Glutamate regulation of calcium and IP3
        oscillating and pulsating dynamics in astrocytes. J Biol Physics
        — Full G-ChI ODE system for calcium dynamics. Our calcium model
        is a simplified saturating-linear/exponential-decay approximation;
        see tripartite_calcium.py for details.
````

## module — original line 28 (docstring)

````text
Pure business logic — no I/O.

````
