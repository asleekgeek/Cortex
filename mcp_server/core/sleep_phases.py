"""Core: sleep_phases (F1) — NREM/REM two-phase offline consolidation.

Cortex already runs a single offline consolidation pass (``sleep_compute.py``):
dream replay of hot memories, textual cluster summarization, re-embedding, and
auto-narration. Active-systems-consolidation theory, however, describes sleep
as *two* functionally distinct stages, not one: NREM slow-wave sleep drives
exact hippocampal→cortical replay that transfers and stabilizes recent traces,
while REM sleep supports integration, recombination, and schema abstraction.
The single pass conflated these: it did the NREM-like exact replay, but its
only "abstraction" was a lexical centroid sentence per cluster — it never
formed the abstract *schemas* that the schema engine (``schema_engine.py`` /
``schema_extraction.py``) already knows how to build. F1 splits the single pass
into two named, ordered phases and makes the REM-like abstraction phase
explicit by routing it through the existing schema-formation logic.

Neuroscience basis (DOIs verified against Crossref in-session):
  - Diekelmann & Born (2010), "The memory function of sleep," Nature Reviews
    Neuroscience 11:114-126 (doi:10.1038/nrn2762). Active systems
    consolidation: NREM slow-wave replay transfers hippocampal traces to
    neocortex; REM supports integration, schema, and emotional processing —
    the two-stage division this module operationalises as NREM-then-REM.
  - McClelland, McNaughton & O'Reilly (1995), "Why there are complementary
    learning systems in the hippocampus and neocortex...," Psychological Review
    102:419-457 (doi:10.1037/0033-295X.102.3.419). The complementary-learning-
    systems rationale for offline replay driving fast (hippocampal) → slow
    (neocortical, schema-level) transfer — the reason a distinct abstraction
    phase is warranted rather than replay alone.
  - van de Ven, Siegelmann & Tolias (2020), "Brain-inspired replay for
    continual learning with artificial neural networks," Nature Communications
    11, art. 4069 (doi:10.1038/s41467-020-17866-2). Computational precedent
    that an offline replay phase in an artificial system prevents catastrophic
    forgetting — the AI-feasibility anchor for a scheduled replay+abstraction
    consolidation stage.

Design (pure business logic — no I/O; all storage stays with the caller):
  - ``run_nrem_phase`` — the NREM-like exact-replay consolidation. It delegates
    verbatim to ``sleep_compute.run_sleep_compute_streamed``; the replay,
    re-embedding, cluster summarization, and narration logic is REUSED, not
    reimplemented. Its output dict is byte-for-byte the single pass's output.
  - ``run_rem_phase`` — the REM-like recombination/abstraction phase. It forms
    an abstract schema from each cluster via
    ``schema_extraction.extract_schema_from_cluster`` and then RECOMBINES
    overlapping newly-formed schemas via ``schema_extraction.should_merge_schemas``
    / ``schema_extraction.merge_schemas`` — the same schema-formation and
    schema-merge logic the schema engine (``schema_engine.py``) orchestrates at
    encoding time, now invoked as an explicit consolidation-phase step. This is
    the step the single pass lacked — abstraction beyond a lexical summary.
  - ``run_two_phase_consolidation`` — the orchestrator. Runs NREM then REM in
    that fixed order and returns the NREM plan (top-level keys preserved so
    existing consolidation callers keep working) plus a ``sleep_phases`` block
    carrying per-phase counts and the phase order.

Ablation guard. When ``CORTEX_ABLATE_SLEEP_PHASES=1`` (Mechanism.SLEEP_PHASES),
the orchestrator SKIPS the REM phase and returns exactly the single-pass NREM
plan — the behavior-preserving fallback to the pre-split pass. With the
mechanism enabled (default), NREM still produces at least the consolidation the
single pass did (it *is* the single pass) and REM adds the explicit abstraction
on top; the split therefore never regresses existing consolidation outcomes.

Honesty note (zetetic standard, matching attentional_control.py /
source_monitoring.py / habituation.py): this is a phase-LABELING and ORDERING
refactor over the existing consolidation and schema logic, not a biophysical
model of sleep. "NREM" and "REM" are functional analogies for two computations
Cortex already contains (exact replay; schema abstraction) — there are no
sleep-stage oscillations, no spindle/slow-wave dynamics, and no learned stage
transitions. The split is deterministic scheduling (always NREM then REM), not
a learned or stochastic sleep architecture. The only NEW behavior over the
prior single pass is that the schema-abstraction phase is now invoked as an
explicit, named consolidation step; the replay/re-embedding/narration path is
unchanged and its results are identical.
"""

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

    Thin, behavior-preserving delegation to the existing single consolidation
    pass (``sleep_compute.run_sleep_compute_streamed``): dream replay of the
    hottest memories, cluster summarization, stale re-embedding, and
    auto-narration. Nothing here is reimplemented — the returned plan is
    identical to what the single pass produced, so callers that consume
    ``replay_updates`` / ``stale_embeddings`` / ``cluster_summaries`` /
    ``narration`` keep working unchanged.

    F2 targeted reactivation. An optional ``cue`` biases *which* memories enter
    the bounded replay set: ``sleep_compute`` ranks the replay heap by
    ``heat + cue_boost * cue_match_score`` so cue-related memories are
    preferentially replayed. With no cue (the default, and whenever
    Mechanism.TARGETED_REACTIVATION is ablated) the selection is exactly the
    pre-F2 heat-based one — identity.
    """
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

    The returned plan preserves every top-level key of the single-pass NREM
    plan (``replay_updates``, ``stale_embeddings``, ``cluster_summaries``,
    ``narration``) so existing consolidation callers are unaffected, and adds a
    ``sleep_phases`` block with per-phase counts and the phase order actually
    run.

    F2 targeted reactivation. An optional ``cue`` (topic / tag / entity /
    free-text) biases which memories preferentially replay in the NREM phase
    (see ``run_nrem_phase`` / ``targeted_reactivation``). The ``sleep_phases``
    block reports the ``cue`` actually applied (``None`` when there is none or
    the mechanism is ablated) under a ``tmr`` sub-block for cortex-viz.

    Ablation:
      - ``CORTEX_ABLATE_SLEEP_PHASES=1`` skips the REM phase and returns the
        single-pass NREM plan (``phase_order`` ``["nrem"]``, empty REM counts) —
        the behavior-preserving fallback to the pre-split pass.
      - ``CORTEX_ABLATE_TARGETED_REACTIVATION=1`` forces ``cue=None`` into the
        NREM replay selection, so replay is chosen purely by heat as it was
        pre-F2 — the behavior-preserving fallback for the cue bias.
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
