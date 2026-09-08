---
title: "ADR-0319 — mcp_server/core/write_gate.py rationale"
status: accepted
source: mcp_server/core/write_gate.py
---

# ADR-0319 — mcp_server/core/write_gate.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## determine_bypass — original line 121 (docstring)

````text
Determine if write gate should be bypassed and why.
````

## determine_bypass — original line 123 (docstring)

````text
    ``origin`` (issue #365) is the CHANNEL the content arrived through, from
    ``core/capture_origin.classify_capture_origin`` — never inferred from the
    content. Content-derived bypasses (``bypass_error`` / ``bypass_decision``)
    are refused when the origin may not claim them, because those two are read
    out of the content itself and are therefore exactly what off-machine text
    would forge to install itself in durable, cross-session memory. ``force``
    and a ``deliberate`` write class are out-of-band human signals and stay
    valid at any origin. Defaults to ``ORIGIN_UNKNOWN``, which is permissive,
    so existing callers are unaffected; the untrusted path passes its real
    origin explicitly.
````

## determine_bypass — original line 134 (docstring)

````text
    ``write_class`` (M-D2, issue #147): a resolved ``deliberate`` write is
    NEVER rejected by the novelty gate — this is the tool's documented
    contract (near-duplicates are still merged/linked/superseded by
    ``try_curation`` afterward; bypassing the gate here only skips the
    REJECT verdict, it does not skip curation, which reads ``force``
    independently). ``write_class`` defaults to ``""`` (no bypass) so the
    unit tests exercising the content/tag/force bypass paths in isolation
    are unaffected; the real call site (``remember_helpers._observed_decision``)
    always passes the already-resolved class (never ``""`` — see
    ``core/write_class.classify_write_class``'s postcondition: the return
    value is always one of ``ALL_WRITE_CLASSES``).
````

## determine_bypass — original line 146 (docstring)

````text
    Checked LAST (after the more specific content/tag bypasses): most
    ``remember`` calls resolve to ``deliberate`` by default (any source not
    in the auto/derived/mechanical sets — see ``write_class`` module
    docstring), so checking it first would mask every content-based
    ``bypass_error``/``bypass_decision``/``bypass_important_tag`` reason
    behind the generic ``bypass_write_class_deliberate`` one. Ordering it
    last preserves the more informative diagnostic reason where one
    applies, while still guaranteeing every deliberate write bypasses
    (falling through to the deliberate check when none of the more
    specific conditions matched).
    
````

## apply_goal_maintenance — original line 409 (docstring)

````text
    While a goal/task-set is active (promoted from the store's active
    prospective triggers via ``read_active_goal``), a goal-relevant input has
    its novelty scaled up by a small multiplicative gain
    (``goal_maintenance.goal_write_gain`` = ``1 + weight·relevance``) so it
    clears the write threshold slightly more easily — the Miller & Cohen (2001)
    task-set biasing processing toward goal-relevant information. Returns
    ``(modulated_novelty, outcome_dict)``; ``outcome_dict`` is None when the
    mechanism is ablated, no goal is active, or the pass fails.
````

## apply_goal_maintenance — original line 418 (docstring)

````text
    Behavior-preserving by default: with no active goal the gain is exactly 1.0,
    so ``novelty_score`` is returned unchanged and existing callers are
    unaffected. An off-task input under an active goal (relevance 0) is likewise
    unchanged — only genuinely goal-relevant inputs are favored.
````

## apply_goal_maintenance — original line 426 (docstring)

````text
    DESIGN INFERENCE: the goal-match is a deterministic keyword/entity/directory
    overlap re-weight promoted from the prospective trigger surface, not a
    learned PFC task-set controller (see goal_maintenance module docstring).
    
````

## apply_habituation — original line 479 (docstring)

````text
    Progressively suppresses repeated low-salience identical inputs (the
    exponential response decrement of Rankin 2009) and transiently sensitizes
    the gate for related inputs just after a salient event. Returns
    ``(modulated_novelty, outcome_dict)``; ``outcome_dict`` is None when the
    mechanism is ablated or the pass fails.
````

## apply_habituation — original line 485 (docstring)

````text
    Behavior-preserving by default: a first-seen signature (repeat_count 0) and
    no recent salient event yield a combined gain of 1.0, so ``novelty_score``
    is returned unchanged and existing callers are unaffected unless the repeat
    pattern actually triggers.
````

## module — original line 84 (comment)

````text
# Temporal novelty asks "have we seen this in MY system
# recently?" — that is elapsed-since-ingest, not
# elapsed-since-the-original-event. Use ingested_at and fall
# back to created_at for legacy rows.
# Source: docs/benchmarks/e1-v3-locomo-smoke-finding.md.
````

## module — original line 157 (comment)

````text
# A deliberate write class is an out-of-band signal a human supplied, and
# such a write bypasses regardless (the `write_class == "deliberate"` arm
# below). Refusing it the SPECIFIC content reason would therefore change no
# outcome — only the diagnostic, masking bypass_error behind the generic
# bypass_write_class_deliberate and undoing the ordering issue #147
# deliberately chose. So the origin allowlist governs whether content may
# BUY a bypass it would not otherwise get, not how an already-granted one
# is labelled.
````

## inline — original line 231 (directive-rationale)

````text
# noqa: BLE001 — mechanism boundary — failure is observable via silent_failure ("write_gate.oscillatory_context")
````

## module — original line 249 (comment)

````text
# Language-aware success cue (issue #158) — same coverage rules as
# the decision/error detectors; see content_cues module docstring.
````

## inline — original line 268 (directive-rationale)

````text
# noqa: BLE001 — mechanism boundary — failure is observable via silent_failure ("write_gate.neuromodulation")
````

## inline — original line 287 (directive-rationale)

````text
# noqa: BLE001 — mechanism boundary — failure is observable via silent_failure ("write_gate.emotional_tagging")
````

## module — original line 308 (comment)

````text
# Only a separation that actually moved the embedding (index above this
# epsilon) replaces the original vector.
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## inline — original line 343 (directive-rationale)

````text
# noqa: BLE001 — mechanism boundary — failure is observable via silent_failure ("write_gate.pattern_separation")
````

## inline — original line 366 (directive-rationale)

````text
# noqa: BLE001 — mechanism boundary — failure is observable via silent_failure ("write_gate.schema_match")
````

## inline — original line 389 (directive-rationale)

````text
# noqa: BLE001 — mechanism boundary — failure is observable via silent_failure ("write_gate.active_goal_read")
````

## inline — original line 394 (directive-rationale)

````text
# noqa: BLE001 — mechanism boundary — failure is observable via silent_failure ("write_gate.active_goal_build")
````

## inline — original line 435 (directive-rationale)

````text
# noqa: BLE001 — preserve the existing non-fatal modulation boundary
````

## inline — original line 466 (directive-rationale)

````text
# noqa: BLE001 — mechanism boundary; errors preserve identity and remain observable
````

## inline — original line 497 (directive-rationale)

````text
# noqa: BLE001 — preserve the existing non-fatal modulation boundary
````

## module — original line 516 (comment)

````text
# source: habituate_novelty returns its unclipped combined_gain;
# this unit input is an observation probe, not a measured novelty.
````

## inline — original line 529 (directive-rationale)

````text
# noqa: BLE001 — mechanism boundary; errors preserve identity and remain observable
````
