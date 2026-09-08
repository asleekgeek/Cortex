# ADR-0355: mcp_server/handlers/consolidation/decay.py implementation decisions

Status: accepted; preserved from the existing implementation during issue #514.

These are historical implementation records, not new algorithm or threshold choices.
Source: `mcp_server/handlers/consolidation/decay.py`; original SHA-256 `8a18f79ba611ca623fbb95f5758e24f146677079137a5628b2a4c6f2b27edd15`.

## Original docstring, lines 1–12

````text
"""Decay cycle: entity heat decay only.

**A3 lazy-heat**: memory heat decay is computed at read time by
``effective_heat()`` in ``recall_memories()``. This eliminates the
per-row memory UPDATE that dominated consolidate runtime in darval's
v3.12.0 report. What remains here is *entity* decay (the
``entities.heat`` column still stores eager state until the D2
program lands) and metabolic-modulation observability on astrocyte
territories.

Source: docs/program/phase-3-a3-migration-design.md §6.
"""
````

## Original docstring, lines 36–41

````text
"""Decay entities and run metabolic observability.

    Memory heat decay is lazy — computed by ``effective_heat()`` on read.
    ``memories`` is kept in the signature for caller symmetry with
    pre-A3 but is only used to compute per-domain metabolic state.
    """
````

