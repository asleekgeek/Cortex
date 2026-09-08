---
title: "ADR-0259 — mcp_server/core/sleep_phases.py rationale"
status: accepted
source: mcp_server/core/sleep_phases.py
---

# ADR-0259 — mcp_server/core/sleep_phases.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
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
````

## module — original line 16 (docstring)

````text
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
````

## module — original line 35 (docstring)

````text
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
````

## module — original line 53 (docstring)

````text
Ablation guard. When ``CORTEX_ABLATE_SLEEP_PHASES=1`` (Mechanism.SLEEP_PHASES),
the orchestrator SKIPS the REM phase and returns exactly the single-pass NREM
plan — the behavior-preserving fallback to the pre-split pass. With the
mechanism enabled (default), NREM still produces at least the consolidation the
single pass did (it *is* the single pass) and REM adds the explicit abstraction
on top; the split therefore never regresses existing consolidation outcomes.
````

## module — original line 60 (docstring)

````text
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

````

## run_nrem_phase — original line 109 (docstring)

````text
    Thin, behavior-preserving delegation to the existing single consolidation
    pass (``sleep_compute.run_sleep_compute_streamed``): dream replay of the
    hottest memories, cluster summarization, stale re-embedding, and
    auto-narration. Nothing here is reimplemented — the returned plan is
    identical to what the single pass produced, so callers that consume
    ``replay_updates`` / ``stale_embeddings`` / ``cluster_summaries`` /
    ``narration`` keep working unchanged.
````

## run_nrem_phase — original line 117 (docstring)

````text
    F2 targeted reactivation. An optional ``cue`` biases *which* memories enter
    the bounded replay set: ``sleep_compute`` ranks the replay heap by
    ``heat + cue_boost * cue_match_score`` so cue-related memories are
    preferentially replayed. With no cue (the default, and whenever
    Mechanism.TARGETED_REACTIVATION is ablated) the selection is exactly the
    pre-F2 heat-based one — identity.
    
````

## run_two_phase_consolidation — original line 227 (docstring)

````text
Run the two-phase offline consolidation: NREM (exact replay) then REM
    (recombination/abstraction), in that fixed order.
````

## run_two_phase_consolidation — original line 230 (docstring)

````text
    The returned plan preserves every top-level key of the single-pass NREM
    plan (``replay_updates``, ``stale_embeddings``, ``cluster_summaries``,
    ``narration``) so existing consolidation callers are unaffected, and adds a
    ``sleep_phases`` block with per-phase counts and the phase order actually
    run.
````

## run_two_phase_consolidation — original line 242 (docstring)

````text
    Ablation:
      - ``CORTEX_ABLATE_SLEEP_PHASES=1`` skips the REM phase and returns the
        single-pass NREM plan (``phase_order`` ``["nrem"]``, empty REM counts) —
        the behavior-preserving fallback to the pre-split pass.
      - ``CORTEX_ABLATE_TARGETED_REACTIVATION=1`` forces ``cue=None`` into the
        NREM replay selection, so replay is chosen purely by heat as it was
        pre-F2 — the behavior-preserving fallback for the cue bias.
    
````
