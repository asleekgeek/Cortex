# ADR-0351: mcp_server/handlers/consolidation/cls.py implementation decisions

Status: accepted; preserved from the existing implementation during issue #514.

These are historical implementation records, not new algorithm or threshold choices.
Source: `mcp_server/handlers/consolidation/cls.py`; original SHA-256 `6fbc70f99ec328d36d236325626b85b6c2357c940a36e93cc5a54e8ea33f1b29`.

## Original comment, lines 32–35

````text
# Source: issue #13 — previous cap of 500 saw ~2% of a 25k-episodic
# store and produced 0 patterns by construction. 2000 matches plasticity
# sampling and keeps PC algorithm's O(E^2) worst case tractable on a
# 10k-entity vocabulary.
````

## Original comment, lines 44–44

````text
# source: structural — a cluster is at least a pair of memories
````

## Original docstring, lines 92–115

````text
"""Run CLS consolidation: episodic -> semantic pattern extraction.

    Verification ablation hook: when ``CORTEX_CONSOLIDATION_DISABLED=1``
    is set (E2 N-scan condition `cortex_flat`), this returns the zero
    state immediately. No episodic-to-semantic abstraction runs; the
    flat-importance store is never enriched with patterns. Source:
    docs/provenance/verification-protocol.md E2; benchmarks/lib/n_scan_runner.py.

    Pattern extraction (`plan_cls_consolidation`) and causal-edge
    discovery (`_discover_causal_edges`) sample up to 2000 episodic
    memories each -- raised from 500 after Feynman's audit of darval's
    66K run in issue #13 showed 500 sampled 2% of the episodic store
    and produced 0 patterns by construction.

    Postcondition (issue #14 P2): the returned dict always carries the
    6 numeric counters (`patterns_found`, `new_semantics_created`,
    `skipped_inconsistent`, `skipped_duplicate`, `causal_edges_found`,
    `episodic_scanned`). When every *mutational* counter is zero (all
    except `episodic_scanned`), an additive ``reason_for_zero`` key
    classifies the early-return path: one of ``empty_episodic_scan``,
    ``below_min_pattern_size``, ``insufficient_pairs``,
    ``no_qualifying_entities``, ``passed_through``. When any mutational
    counter is non-zero, ``reason_for_zero`` is omitted.
    """
````

## Original docstring, lines 265–272

````text
"""Emit an INFO log when the stage finished as a genuine no-op.

    Issue #14 P2 (darval): operators need to grep
    ``stage=<name> reason=passed_through`` to distinguish "quiet store"
    runs from early-return runs. Only fires when the classified reason
    is ``passed_through`` on either field (``reason_for_zero`` or
    ``reason_for_inaction``).
    """
````

## Original comment, lines 368–369

````text
# mem_id is not needed here: provenance is embedded in `tags`
            # above, written atomically with the row at insert time.
````

## Original docstring, lines 396–418

````text
"""Append source-episodic provenance tags to a to-be-created semantic memory.

    Precondition: `tags` is the tag list about to be written on a NEW row
    (semantic memory not yet inserted); `source_ids` are the episodic memory
    ids the CLS cluster crystallized from (may contain None from incomplete
    pattern rows — filtered out).
    Postcondition: returns `tags` plus one `cls-derived` category tag and one
    `derived-src:<memory_id>` pointer per non-null source id (append-only,
    order-preserving, no dedup needed — each call builds one fresh row).

    Tags, not a `relationships` row: `relationships.source_entity_id` /
    `target_entity_id` are `NOT NULL REFERENCES entities(id)`, so they cannot
    address a memory id. The prior implementation
    (`_link_source_memories`, removed here) looped `source_ids` into
    `store.insert_relationship({"source_entity_id": source_id, ...})` inside a
    bare `except Exception: pass` — every call raised the FK violation and was
    silently swallowed, so no source→semantic link was ever persisted since
    this code's introduction. Fixed at the source (this function), not by
    guarding the throw site: provenance is now embedded in the row's own
    tags at insert time, reusing the `derived-src:<memory_id>` convention
    already established and live-proven by
    `handlers/consolidation/memify_derive.py` (INC6.1b).
    """
````

## Original docstring, lines 432–449

````text
"""Discover causal edges from entity co-occurrences (PC algorithm).

    Gates on minimum signal before running the O(E²) independence tests:
    the PC algorithm needs at least `min_observations` mentions per
    entity in the sample to distinguish correlation from chance, so if
    fewer than `_MIN_ENTITIES_FOR_PC` entities clear that threshold,
    skip the analysis entirely (issue #13 Phase D).

    Returns
    -------
    (edges_stored, qualifying_count)
        edges_stored — number of causal/correlation edges persisted.
        qualifying_count — number of entities whose mention count
        reached ``_PC_MIN_OBSERVATIONS``. Surfaced for issue #14 P2
        diagnostics so the handler can distinguish "no entities mentioned
        enough" (``insufficient_pairs``) from "a few qualify but below
        ``_MIN_ENTITIES_FOR_PC``" (``no_qualifying_entities``).
    """
````

## Original comment, lines 479–481

````text
# Source: PC algorithm lower bound — need ≥3 observations per variable
# to distinguish dependence from sampling noise; need ≥5 active variables
# for the independence tests to produce any non-trivial edge.
````

## Reviewed remaining docstring (mcp_server/handlers/consolidation/cls.py, interim lines 1–8)

````text
CLS cycle: episodic -> semantic pattern extraction.

Includes causal edge discovery from entity co-occurrences via the PC algorithm.

Returns include a diagnostic ``reason_for_zero`` field when the cycle
produces no mutations (all mutational counters zero), distinguishing
early-return from a genuine "nothing to do" pass (issue #14 P2, darval).
````

## Reviewed remaining docstring (mcp_server/handlers/consolidation/cls.py, interim lines 89–101)

````text
Run CLS consolidation: episodic -> semantic pattern extraction.

    Postcondition (issue #14 P2): the returned dict always carries the
    6 numeric counters (`patterns_found`, `new_semantics_created`,
    `skipped_inconsistent`, `skipped_duplicate`, `causal_edges_found`,
    `episodic_scanned`). When every *mutational* counter is zero (all
    except `episodic_scanned`), an additive ``reason_for_zero`` key
    classifies the early-return path: one of ``empty_episodic_scan``,
    ``below_min_pattern_size``, ``insufficient_pairs``,
    ``no_qualifying_entities``, ``passed_through``. When any mutational
    counter is non-zero, ``reason_for_zero`` is omitted.

source: ADR-0351
````

## Reviewed remaining docstring (mcp_server/handlers/consolidation/cls.py, interim lines 400–412)

````text
Discover causal edges from entity co-occurrences (PC algorithm).

    Returns
    -------
    (edges_stored, qualifying_count)
        edges_stored — number of causal/correlation edges persisted.
        qualifying_count — number of entities whose mention count
        reached ``_PC_MIN_OBSERVATIONS``. Surfaced for issue #14 P2
        diagnostics so the handler can distinguish "no entities mentioned
        enough" (``insufficient_pairs``) from "a few qualify but below
        ``_MIN_ENTITIES_FOR_PC``" (``no_qualifying_entities``).

source: ADR-0351
````

