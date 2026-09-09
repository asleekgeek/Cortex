---
title: "ADR-0118 — mcp_server/core/cascade_stages.py rationale"
status: accepted
source: mcp_server/core/cascade_stages.py
---

# ADR-0118 — mcp_server/core/cascade_stages.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Models the biochemical cascade that transforms a labile memory trace into a
stable, cortically integrated engram. Memories progress through stages with
different properties at each stage:
````

## module — original line 7 (docstring)

````text
Stages:
  LABILE (0-1h)         — Just encoded. Highly vulnerable to interference.
  EARLY_LTP (1-6h)      — Synaptic tag set (Frey & Morris 1997).
  LATE_LTP (6-24h)      — Protein synthesis complete. CREB-dependent.
  CONSOLIDATED (>24h)   — Systems consolidation underway.
  RECONSOLIDATING       — Retrieval-triggered lability (Nader et al. 2000).
````

## module — original line 14 (docstring)

````text
Each stage has:
  - A decay rate multiplier (labile decays fast, consolidated decays slow)
  - An interference vulnerability (labile = high, consolidated = low)
  - A plasticity level (how modifiable the trace is)
  - A minimum dwell time (can't skip stages)
  - Transition requirements (what must be true to advance)
````

## module — original line 21 (docstring)

````text
References:
    Kandel ER (2001) The molecular biology of memory storage.
    Dudai Y (2012) The restless engram: consolidations never end.
    Frey U, Morris RGM (1997) Synaptic tagging and LTP. Nature 385:533-536
    Nader K et al. (2000) Fear memories require protein synthesis in the
        amygdala for reconsolidation after retrieval. Nature 406:722-726
````

## module — original line 28 (docstring)

````text
Pure business logic — no I/O.

````

## StageProperties — original line 52 (mixed-contract-rationale)

````text
    Attributes:
        decay_multiplier: Multiplied into decay rate. >1 = faster decay, <1 = slower.
        interference_vulnerability: How susceptible to interference [0, 1].
        plasticity: How modifiable the memory is [0, 1].
        min_dwell_hours: Minimum time in this stage before advancement.
        max_dwell_hours: Maximum time before forced transition (or decay).
        heat_floor: Minimum heat for this stage. Consolidated memories never
            decay below this floor. Based on Bahrick (1984) permastore effect
            and Benna & Fusi (2016) cascade retention floors.
    
````

## get_heat_floor — original line 148 (docstring)

````text
Get minimum heat for a consolidation stage (Bahrick 1984 permastore).
````

## get_heat_floor — original line 150 (docstring)

````text
    Consolidated memories never decay below this floor. The structural
    substrate (new synapses, enlarged spines — Kandel 2001) persists
    even without rehearsal.
    
````

## module — original line 74 (comment)

````text
# LABILE: No structural substrate yet. Fully vulnerable to decay.
# Biological: post-translational modifications only (minutes).
````

## module — original line 84 (comment)

````text
# EARLY_LTP: Synaptic tag set but protein synthesis not yet complete.
# Biological: PKA/CaMKII activation (1-6h). Reversible.
````

## module — original line 94 (comment)

````text
# LATE_LTP: CREB-dependent protein synthesis complete. Structural changes
# beginning. Blocked by anisomycin only if applied within first 1-3h window.
# Biological: new protein synthesis, initial synapse growth (6-24h).
````

## module — original line 105 (comment)

````text
# CONSOLIDATED: Structural consolidation complete (Kandel 2001: at 72h,
# blocking protein synthesis has NO effect — synaptic changes are permanent).
# Bahrick (1984): permastore — retained for 30+ years without rehearsal.
# Benna & Fusi (2016): deepest cascade levels provide irreversible storage.
````

## inline — original line 115 (comment)

````text
# Permastore: always retrievable (Bahrick 1984)
````

## module — original line 117 (comment)

````text
# RECONSOLIDATING: Retrieved memory becomes labile again (Nader 2000).
# Needs re-stabilization via protein synthesis.
````
