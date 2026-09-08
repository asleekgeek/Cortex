---
title: "ADR-0136 — mcp_server/core/consolidation_engine.py rationale"
status: accepted
source: mcp_server/core/consolidation_engine.py
---

# ADR-0136 — mcp_server/core/consolidation_engine.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Orchestrates the full consolidation cycle:
  1. Pattern detection in episodic memories (Go-CLS clustering)
  2. Consistency checking (contradiction detection)
  3. Schema abstraction (generalized knowledge extraction)
  4. Duplicate detection (avoid redundant semantics)
````

## module — original line 9 (docstring)

````text
Pure business logic — receives data, returns actions to take.
The caller (handler/infrastructure) executes the I/O.

````

## stress_scaled_min_occurrences — original line 65 (docstring)

````text
    Stress-hormone modulation (D1) scales how strongly/broadly the offline pass
    consolidates along an inverted-U (Roozendaal & McGaugh 2011; McGaugh 2000):
    moderate session stress ENHANCES consolidation, extreme stress IMPAIRS it.
    Here "consolidation scope" is the recurrence bar a pattern must clear to be
    abstracted into a semantic memory: dividing it by the gain means
````

## stress_scaled_min_occurrences — original line 71 (docstring)

````text
      - moderate stress (gain > 1) => LOWER effective threshold => more patterns
        qualify => broader/stronger consolidation (the enhancement lobe);
      - extreme stress (gain < 1) => HIGHER effective threshold => fewer patterns
        qualify => weaker consolidation (the impairment lobe);
      - neutral stress OR ablated (gain == 1.0) => threshold UNCHANGED — exact
        identity, so existing callers that pass no stress are unaffected.
````

## stress_scaled_min_occurrences — original line 82 (docstring)

````text
    This is a DESIGN INFERENCE — a deterministic one-parameter modulation of the
    consolidation scope, not a validated glucocorticoid model; see
    stress_modulation.py's honesty note.
    
````

## plan_cls_consolidation — original line 114 (docstring)

````text
    D1 stress-hormone modulation. ``session_stress`` (a scalar in [0, 1] from
    ``stress_modulation.compute_session_stress`` / ``assess_session_stress``)
    scales the consolidation SCOPE along the inverted-U: it modulates the
    effective ``min_occurrences`` via ``stress_scaled_min_occurrences``. The
    default ``session_stress=0.0`` yields gain 1.0 and leaves ``min_occurrences``
    unchanged — behavior-preserving identity for every existing caller. When
    Mechanism.STRESS_MODULATION is ablated the gain is forced to 1.0, so this is
    likewise a no-op.
    
````

## _try_abstract_pattern — original line 154 (docstring)

````text
    C1 read-side enforcement (source/reality monitoring). Before returning the
    abstraction, the confabulation gate
    (``source_monitoring.promotion_confabulation_risk``) checks whether the
    cluster being crystallized into a semantic FACT is internally generated
    (INFERRED) with zero perceptual grounding — Johnson & Raye's (1981)
    reality-monitoring failure, a confabulation being promoted to knowledge. The
    result carries a ``confabulation_risk`` boolean so the caller (and the
    downstream semantic-memory writer) can flag it. This is NON-FATAL and
    behavior-preserving: a flagged cluster is STILL abstracted and STILL
    eligible for promotion; the gate annotates, it does not drop. When
    ``Mechanism.CONFABULATION_GATE`` is ablated
    (``CORTEX_ABLATE_CONFABULATION_GATE=1``) the check is skipped and the flag is
    left False — identical set of returned abstractions either way.
    
````

## _process_patterns — original line 197 (docstring)

````text
    ``confabulation_risk_promotions`` counts the abstractions the C1 gate flagged
    as a confabulation being crystallized as a semantic fact (INFERRED cluster,
    zero perceptual grounding). These are STILL promoted (non-fatal flag), so the
    count is an audit signal, not a drop count; it is 0 when the gate is ablated.
    
````

## find_near_duplicates — original line 271 (docstring)

````text
    Rationale: a fresh correction of a stale fact has low heat (just stored)
    but a newer created_at.  The old stale duplicate has high heat from
    prior accesses.  Keeping by heat would discard the correction.
    Keeping by recency ensures the supersession is respected.
````

## module — original line 321 (comment)

````text
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## module — original line 364 (comment)

````text
# source: graduation conditions documented in the should_reclassify
# docstring ("Accessed >= 5 times", ">= 3 related semantic memories");  # noqa: ERA001
# tuning provenance not recorded
````
