---
title: "ADR-0159 — mcp_server/core/distillation.py rationale"
status: accepted
source: mcp_server/core/distillation.py
---

# ADR-0159 — mcp_server/core/distillation.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 5 (docstring)

````text
Design doc: ``scratchpad/memoire-qui-comprend-design.md`` §M-D8. Mirrors the
role-split already proven by ``core/auto_curator.py`` (server clusters, the
in-session LLM authors, ``wiki_write``/``remember`` persists) — the only
distillation mechanism in this system that has ever produced anything: 0
rows from ``memify_derive``'s server-only templated synthesis (measured
2026-07-10, ``SELECT count(*) FROM memories WHERE tags @> '"derived"'``)
versus N wiki pages authored through ``curate_wiki``. ``curate_distill``
(handler) assembles three kinds of candidate "dossier" — pre-existing
evidence that a lesson-shaped synthesis is possible — and returns them as
jobs; the session LLM writes the WHY as a normal ``remember`` call
(``write_class='deliberate'``, tags ``lesson`` + ``derived-src:<id>``,
per M-D8 point 2 — NOT ``write_class='derived'``, which stays reserved for
``memify_derive``'s own machine-synthesized inventory facts, M-D8 point 3).
````

## module — original line 19 (docstring)

````text
Pure business logic — no I/O. Every ``build_*_dossiers`` function receives
pre-fetched memory dicts / co-access pairs and returns ``DistillDossier``
objects; the handler (composition root) is the only layer that touches the
store.
````

## module — original line 24 (docstring)

````text
Contract shared by every builder in this module:
  Precondition: inputs are pre-fetched (heads_only, not stale) by the
    caller; this module never queries a store.
  Postcondition: dossiers are capped (bounded-I/O convention, audit
    2026-06-09, mirrored from ``memify_derive.py``); a dossier's
    ``memory_ids`` are deduplicated and sorted ascending on construction
    (``DistillDossier.__post_init__``) because ``marker`` — the
    idempotence key — is a hash of that canonical order.

````

## _parse_iso — original line 75 (mixed-contract-rationale)

````text
    Precondition: none (accepts None/garbage).
    Postcondition: never raises. Mirrors
    ``core/cognitive_map.py::_parse_iso_timestamp`` (kept local rather
    than imported — a single stdlib-wrapping helper is not worth a
    core-to-core import; cognitive_map.py makes the same local-duplication
    choice for its own single call site).
    
````

## dossier_marker_tag — original line 96 (mixed-contract-rationale)

````text
    Precondition: ``memory_ids`` non-empty.
    Postcondition: the same set of ids (any input order, any duplicates)
    always maps to the same tag string. Extends
    ``memify_derive.py``'s ``derived-rel:<a>-<b>-<type>`` marker
    convention (INC6.1b, one marker per *pair*) to the N-member case,
    where a literal id-pair key is impossible — ``simple_hash``
    (``shared/hash.py``, DJB2, already used elsewhere for content
    fingerprinting) hashes the canonical (deduplicated, sorted) id list
    instead of a new hash primitive.
    
````

## build_error_success_dossiers — original line 142 (mixed-contract-rationale)

````text
    Precondition: both lists pre-fetched (any order — this function sorts
    internally); each memory dict carries ``id``, ``content``,
    ``created_at``, ``domain``.
    Postcondition: at most ``max_dossiers`` results, most-recent-error
    first; each dossier has exactly 2 ``memory_ids`` (error id, success
    id); a given success memory is consumed by at most one pairing
    (``used_success_ids``), so two errors never both claim the same fix.
    
````

## build_co_access_dossiers — original line 245 (mixed-contract-rationale)

````text
    Precondition: ``pairs`` is exactly
    ``store.get_temporal_co_access(min_access=_MIN_RECURRING_ACCESS,
    ...)``'s return shape (mem_a, mem_b, proximity) — the PL/pgSQL
    function (``pg_schema.py::GET_TEMPORAL_CO_ACCESS_FN``) already
    filters both endpoints to ``access_count >= min_access`` server-side;
    this function does not re-filter, it only groups. "Recurring" here
    means "both endpoints have been individually revisited >= threshold
    times AND were accessed close together in the same window" — the
    function returns one row per (last_accessed) snapshot, not a
    multi-window repeat count, so this is a proxy for recurrence via
    access_count, not a literal repeated-pairing count. Documented
    precisely to avoid overclaiming what the SQL measures.
    Postcondition: components with >= ``min_cluster_size`` members,
    sorted by (size, avg proximity) descending, each capped at
    ``_MAX_MEMORY_IDS_PER_DOSSIER`` members (highest-proximity edges'
    endpoints kept first); at most ``max_dossiers`` returned.
    
````

## dossier_from_cluster — original line 309 (mixed-contract-rationale)

````text
    Precondition: ``cluster`` was produced by
    ``core.auto_curator.build_clusters`` (entity-cohesive grouping,
    already tested and tuned — MIN_MEMORIES_PER_CLUSTER,
    MIN_AVG_HEAT_FOR_PAGE — reused as-is rather than re-implementing
    entity clustering a second time in this module).
    Postcondition: ``memory_ids`` is capped at
    ``_MAX_MEMORY_IDS_PER_DOSSIER`` — ``build_clusters`` itself does not
    bound cluster size (only its downstream wiki-authoring prompt does,
    via ``MAX_MEMORIES_PER_PROMPT`` — a different, unrelated cap this
    module cannot rely on). Found live on the dev-DB dry-run (INC7.8
    verdict measurement): one real entity_family cluster had 53 members
    before this cap.
    
````

## module — original line 46 (comment)

````text
# ── Bounds (source: bounded-I/O convention, audit 2026-06-09; mirrored
# from memify_derive.py's _CANDIDATE_SCAN_LIMIT / _MAX_DERIVATIONS_PER_RUN
# and auto_curator.py's MAX_MEMORIES_PER_PROMPT) ───────────────────────────
````

## module — original line 57 (comment)

````text
# Error->success search window. Source: reuses the existing system-wide
# maximum co-access window already established in
# handlers/navigate_memory.py's schema (`"maximum": 168.0` hours = 7
# days) as the search cap, rather than inventing a new constant. The
# curate_distill handler's dry-run measures the ACTUAL error->success gap
# distribution on the real corpus and reports it (see M-D9 gate: "VERDICT
# MESURABLE") instead of asserting a tuned default.
````

## module — original line 66 (comment)

````text
# "Recurring" co-access threshold. Source: reuses
# core/curation.py::identify_strengtheneable's existing `min_access: int =
# 5` default — the system's established threshold for "meaningfully
# revisited" — rather than inventing a second one for the same concept.
````

## module — original line 182 (comment)

````text
# succ_id == err_id: a memory tagged BOTH 'error' and
# 'success' would otherwise "pair with itself" (delta=0,
# trivially shares all its own entities) — found live on the
# dev DB dry-run (INC7.8 verdict measurement), not a
# hypothetical edge case.
````

## module — original line 271 (comment)

````text
# Sort edges by proximity descending so the truncation below keeps the
# strongest-linked members first within an oversized component.
````

## module — original line 335 (comment)

````text
# Prompt generation (build_distill_prompt) and the memify_derive usage
# snapshot (summarize_derived_usage) live in distillation_reporting.py —
# split to respect the 300-line file cap (§4.1).
````
