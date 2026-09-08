"""Core: sleep_phases (F1) — NREM/REM two-phase offline consolidation.

source: ADR-0259"""

from __future__ import annotations

from typing import Any, Iterable

from mcp_server.core.ablation import Mechanism, is_mechanism_disabled
from mcp_server.core.schema_extraction import (
    Schema,
    extract_schema_from_cluster,
    merge_schemas,
    schema_to_dict,
    should_merge_schemas,
)
from mcp_server.core.sleep_compute import run_sleep_compute_streamed
from mcp_server.core.targeted_reactivation import _tokens as _cue_tokens

# ── Phase identifiers ─────────────────────────────────────────────────────────

NREM = "nrem"
REM = "rem"
PHASE_ORDER: tuple[str, str] = (NREM, REM)


# ── NREM: exact-replay consolidation (delegates to the existing single pass) ──


def run_nrem_phase(
    memory_chunks: Iterable[list[dict[str, Any]]],
    clusters: list[dict[str, Any]] | None = None,
    directory: str = "",
    period_label: str = "recent",
    max_replay: int = 50,
    max_reembed: int = 100,
    cue: str | None = None,
) -> dict[str, Any]:
    """NREM-like exact-replay consolidation.

    source: ADR-0259"""
    return run_sleep_compute_streamed(
        memory_chunks,
        clusters=clusters,
        directory=directory,
        period_label=period_label,
        max_replay=max_replay,
        max_reembed=max_reembed,
        cue=cue,
    )


# ── REM: recombination / abstraction (schema formation over clusters) ────────


def _recombine_schemas(schemas: list[Schema]) -> list[Schema]:
    """Merge overlapping newly-formed schemas (the REM recombination step).

    Greedy single pass: each schema is either merged into an existing accepted
    schema whose entity signatures overlap enough (``should_merge_schemas``) or
    accepted as a new one. Reuses ``schema_extraction.merge_schemas`` for the
    weighted merge — no new merge logic here.
    """
    accepted: list[Schema] = []
    for schema in schemas:
        for i, existing in enumerate(accepted):
            if should_merge_schemas(existing, schema):
                accepted[i] = merge_schemas(existing, schema)
                break
        else:
            accepted.append(schema)
    return accepted


def run_rem_phase(
    clusters: list[dict[str, Any]] | None,
    *,
    domain: str = "",
    min_memories: int | None = None,
) -> dict[str, Any]:
    """REM-like recombination/abstraction phase.

    Forms an abstract schema from each cluster's memories via the existing
    ``schema_extraction.extract_schema_from_cluster`` (abstraction), then
    recombines overlapping formed schemas via ``_recombine_schemas``
    (recombination). This is the phase the single pass lacked: it produced only
    a lexical centroid summary per cluster, never an abstract schema.

    Returns a dict with the recombined ``schemas`` (Schema objects), their
    serialized ``schema_dicts``, and counts. Empty/absent clusters yield an
    empty result (the phase is a no-op with nothing to abstract over).
    """
    formed: list[Schema] = []
    cluster_list = clusters or []
    for cluster in cluster_list:
        mems = cluster.get("memories", [])
        if not mems:
            continue
        kwargs: dict[str, Any] = {
            "domain": cluster.get("domain", domain),
            "schema_id": str(cluster.get("cluster_id", "")),
        }
        if min_memories is not None:
            kwargs["min_memories"] = min_memories
        schema = extract_schema_from_cluster(mems, **kwargs)
        if schema is not None:
            formed.append(schema)

    recombined = _recombine_schemas(formed)
    return {
        "schemas": recombined,
        "schema_dicts": [schema_to_dict(s) for s in recombined],
        "clusters_seen": len(cluster_list),
        "formed_count": len(formed),
        "recombined_count": len(recombined),
    }


def _empty_rem_result(clusters_seen: int = 0) -> dict[str, Any]:
    """The REM result when the phase is skipped (ablation) — no abstraction."""
    return {
        "schemas": [],
        "schema_dicts": [],
        "clusters_seen": clusters_seen,
        "formed_count": 0,
        "recombined_count": 0,
    }


# ── Orchestrator: NREM then REM ───────────────────────────────────────────────


def run_two_phase_consolidation(
    memory_chunks: Iterable[list[dict[str, Any]]],
    clusters: list[dict[str, Any]] | None = None,
    directory: str = "",
    period_label: str = "recent",
    max_replay: int = 50,
    max_reembed: int = 100,
    *,
    rem_domain: str = "",
    rem_min_memories: int | None = None,
    cue: str | None = None,
) -> dict[str, Any]:
    """Run the two-phase offline consolidation: NREM (exact replay) then REM
    (recombination/abstraction), in that fixed order.

    source: ADR-0259

        F2 targeted reactivation. An optional ``cue`` (topic / tag / entity /
        free-text) biases which memories preferentially replay in the NREM phase
        (see ``run_nrem_phase`` / ``targeted_reactivation``). The ``sleep_phases``
        block reports the ``cue`` actually applied (``None`` when there is none or
        the mechanism is ablated) under a ``tmr`` sub-block for cortex-viz.

        source: ADR-0259
    """
    tmr_ablated = is_mechanism_disabled(Mechanism.TARGETED_REACTIVATION)
    effective_cue = None if tmr_ablated else cue

    nrem_plan = run_nrem_phase(
        memory_chunks,
        clusters=clusters,
        directory=directory,
        period_label=period_label,
        max_replay=max_replay,
        max_reembed=max_reembed,
        cue=effective_cue,
    )

    clusters_seen = len(clusters or [])
    if is_mechanism_disabled(Mechanism.SLEEP_PHASES):
        rem_result = _empty_rem_result(clusters_seen)
        phase_order: tuple[str, ...] = (NREM,)
    else:
        rem_result = run_rem_phase(
            clusters, domain=rem_domain, min_memories=rem_min_memories
        )
        phase_order = PHASE_ORDER

    # Count how many of the replayed (enriched) memories actually matched the
    # cue — the "cued this cycle" figure cortex-viz surfaces. Zero when there
    # is no effective cue (identity).
    cued_replayed = 0
    if effective_cue and (effective_cue or "").strip():
        replay_updates = nrem_plan.get("replay_updates", [])
        cue_tokens = _cue_tokens(effective_cue)
        for upd in replay_updates:
            text = str(upd.get("enriched_content", "") or "")
            if cue_tokens & _cue_tokens(text):
                cued_replayed += 1

    plan = dict(nrem_plan)
    plan["sleep_phases"] = {
        "phase_order": list(phase_order),
        "nrem": {
            "replayed": len(nrem_plan.get("replay_updates", [])),
            "reembedded": len(nrem_plan.get("stale_embeddings", [])),
            "cluster_summaries": len(nrem_plan.get("cluster_summaries", [])),
        },
        "rem": {
            "schemas_formed": rem_result["formed_count"],
            "schemas_recombined": rem_result["recombined_count"],
            "clusters_seen": rem_result["clusters_seen"],
        },
        "rem_schemas": rem_result["schema_dicts"],
        "tmr": {
            "cue": effective_cue,
            "ablated": tmr_ablated,
            "cued_replayed": cued_replayed,
        },
    }
    return plan
