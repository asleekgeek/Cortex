---
title: "ADR-0236 — mcp_server/core/reconsolidation.py rationale"
status: accepted
source: mcp_server/core/reconsolidation.py
---

# ADR-0236 — mcp_server/core/reconsolidation.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Based on Nader et al. (Nature, 2000) and Osan-Tort-Amaral (PLoS ONE, 2011).
````

## module — original line 5 (docstring)

````text
Three outcomes based on mismatch between stored memory and current context:
  - mismatch < low_threshold: Passive retrieval, no change
  - low <= mismatch < high: RECONSOLIDATE — update memory with current context
  - mismatch >= high: destabilize — archive the old memory (heat-penalty /
    soft-delete regime, ``action == "archive"``)
````

## module — original line 11 (docstring)

````text
E2 reversible extinction (Bouton 2004; Milad & Quirk 2012) is a SEPARATE,
non-erasing route: instead of archiving a high-mismatch memory, a caller may
"deprecate" it by growing a reversible inhibitory tag (``extinction_strength``)
that suppresses its effective retrieval weight without deleting the trace, so it
can spontaneously recover (decay) or be reinstated (cleared). See
``mcp_server.core.extinction`` and ``compute_extinction_action`` below. This is
deliberately distinct from the archive branch above — extinction keeps the
memory fully present.
````

## module — original line 20 (docstring)

````text
Modulation — the qualitative mechanisms trace to cited papers, but every
numeric coefficient below is an engineering default with no published or
measured source (calibration pending). docs/provenance/blend-weight-
calibration.md does NOT cover these coefficients — that pre-registration
calibrates 6 different post-WRRF blend weights (HOPFIELD/HDC/SA/
DENDRITIC/EMOTIONAL_RETRIEVAL/MOOD_CONGRUENT betas in recall_pipeline.py)
and none of them is one of these; it is cited here only as the
PROCEDURAL PRECEDENT this codebase follows to resolve an "engineering
default" placeholder (pre-register a sweep, cite the resulting optimum,
update the comment) — not as an existing calibration of these constants.
Corrected pointer (honesty batch): the original "see docs/provenance/
blend-weight-calibration.md" phrasing at 9d6bc96d implied direct
coverage of these coefficients that was never true. The papers establish
the *direction* of each effect, not the magnitude:
  - Prediction-error gate PE = mismatch * (1 - stability * 0.5): Lee (2009)
    gives only the qualitative trace-strength → lability relationship; the
    0.5 coefficient is ours.
  - Age-dependent threshold: Milekic & Alberini (2002) show only a
    qualitative, temporally-graded age-resistance; the 30-day window and
    0.15 weight are ours.
  - Emotional strength gain: emotionally-loaded memories receive a larger
    reconsolidation update. This is an engineering default and is NOT
    derived from Yonelinas & Ritchey (2015) — see decide_action.
````

## module — original line 44 (docstring)

````text
Pure business logic — no I/O. Decisions are returned to the caller.

````

## ReconsolidationResult — original line 123 (docstring)

````text
Result of reconsolidation decision with emotional modulation.
````

## decide_action — original line 151 (docstring)

````text
    Structural source: Osan, Tort & Amaral (PLoS ONE, 2011) — the three-regime
    structure (no-change / reconsolidate / extinguish on rising mismatch). That
    model's parameters are network-specific (pattern overlap, network size,
    protein-synthesis / degradation levels), NOT normalized cut points on a
    [0, 1] mismatch. The 0.15 / 0.65 thresholds here do NOT come from the
    paper; they are engineering defaults (calibration pending — see
    docs/provenance/blend-weight-calibration.md).
````

## decide_action — original line 159 (docstring)

````text
    Qualitative grounding for the modulation terms (directions only — every
    coefficient is an engineering default):
      - PE falls with trace strength: Lee (Trends Neurosci, 2009).
      - Older memories resist destabilization: Milekic & Alberini (Neuron,
        2002) — temporally-graded, no fixed window prescribed.
      - Emotional memories get a larger update: engineering. The Yonelinas &
        Ritchey (2015) "slow forgetting" result is a FORGETTING-RATE effect,
        not a reconsolidation gain, so it is deliberately NOT cited here.
````

## ReconsolidationOutcome — original line 315 (docstring)

````text
    Fields:
      action: from `decide_action` — "none" / "update" / "archive".
      heat_delta: signed change to apply to the memory's heat_base.
        Positive on successful retrieval (Nader 2000 — re-storage
        strengthens), negative on archive (extinction regime).
      valence_delta: signed change to emotional_valence; non-zero only
        when the query carries a Bower-style affective load and the
        action is "update".
      update_last_accessed: whether the store should refresh
        last_accessed (typically True on any non-no-op outcome).
      mismatch: the multi-signal mismatch in [0, 1] for diagnostics.
      prediction_error: PE-gated mismatch from `decide_action`.
    
````

## compute_reconsolidation_action — original line 387 (docstring)

````text
    Source: Nader, Schafe & LeDoux (2000), Nature 406(6797). Retrieval
    triggers a labile window during which the memory is re-stored with
    modifications. Bower (1981) Am. Psychologist 36(2): mood-congruent
    re-storage. The emotional-arousal gain on the update is an engineering
    default (see decide_action — NOT Yonelinas & Ritchey 2015, whose result
    is a forgetting-rate effect, not a reconsolidation gain).
````

## compute_reconsolidation_action — original line 394 (docstring)

````text
    Honors `CORTEX_ABLATE_RECONSOLIDATION=1` via `decide_action`'s
    internal gate (returns action="none"). The stage-level guard in
    `recall_pipeline.reconsolidation_apply` short-circuits earlier so this
    function is not even called when ablated, but the deeper guard means
    direct callers (e.g. tests) also see the no-op behavior.
    
````

## compute_extinction_action — original line 503 (docstring)

````text
    Pure: reads the memory's current ``extinction_strength`` (defaulting to 0
    for un-migrated rows / new memories) and returns a ReconsolidationOutcome
    whose ``extinction_strength`` field is the new tag to persist. The memory's
    heat / content are NOT touched — extinction suppresses the effective
    retrieval weight without erasing the trace (Bouton 2004), so:
````

## compute_extinction_action — original line 517 (docstring)

````text
    Honors ``CORTEX_ABLATE_EXTINCTION=1`` via `extinction.deprecate` (for the
    deprecate path) and a direct guard here (for recover/reinstate): when
    ablated the tag is returned unchanged and ``extinction_strength`` is None so
    the store leaves the column untouched (behaviour-preserving no-op).
````

## module — original line 131 (comment)

````text
# Above this plasticity a memory counts as recently accessed and its
# destabilization thresholds are lowered.
# source: engineering default (calibration pending) — see module docstring
# "Modulation" note: every numeric coefficient here is an engineering default.
````

## inline — original line 146 (comment)

````text
# engineering default (calibration pending)
````

## inline — original line 147 (comment)

````text
# engineering default (calibration pending)
````

## module — original line 178 (comment)

````text
# Prediction-error gate: stable memories dampen PE. Lee (2009) gives the
# qualitative trace-strength → lability relationship only; the 0.5
# coefficient is an engineering default (calibration pending).
````

## module — original line 183 (comment)

````text
# Age-dependent threshold: older memories require larger PE to destabilize.
# Milekic & Alberini (2002) show only a qualitative, temporally-graded
# age-resistance — no 30-day window, no 0.15 weight. Both are engineering
# defaults (calibration pending).
````

## module — original line 205 (comment)

````text
# Reconsolidation regime — emotionally-loaded memories receive a larger
# update (≤1.8x at full arousal). Engineering default (calibration
# pending). NOT derived from Yonelinas & Ritchey (2015): their result is a
# slower FORGETTING RATE for emotional memories (a decay-side effect), not
# a reconsolidation GAIN. Equating the two would be a category error, so no
# paper is cited for this coefficient.
````

## module — original line 222 (comment)

````text
# source: merge_content docstring — over-length merges keep the first 500 +
# last 500 characters of the old content.
````

## module — original line 262 (comment)

````text
# Above this access count, repeated non-useful retrievals start eroding
# stability.
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## module — original line 286 (comment)

````text
# ── Recall-time reconsolidation action ─────────────────────────────────
#
# Recall-time bridge between the retrieval candidate dict (heat, content,
# emotional_valence, last_accessed) and the labile-rewrite decision logic
# (compute_mismatch + decide_action). This is the function the post-WRRF
# RECONSOLIDATION stage in `recall_pipeline.py` calls per top-K candidate.
#
# Source: Nader, Schafe & LeDoux (2000) Nature 406(6797): retrieval renders
# a memory labile for a window during which it can be re-stored with
# modifications. Bower (1981) Am. Psychologist 36(2): retrieval context's
# affective valence biases the re-stored emotional tag.
#
# Engineering defaults — heat / valence step magnitudes are not paper-
# prescribed (the papers establish the *qualitative* mechanism, not numeric
# step sizes for a tag-and-vector memory store). source: none — engineering
# default, calibration pending, per the source-discipline rule (CLAUDE.md
# §8). docs/provenance/blend-weight-calibration.md does NOT calibrate these
# constants (that sweep covers 6 different post-WRRF blend weights in
# recall_pipeline.py) — cited only as the procedural precedent for how this
# codebase resolves an "engineering default" placeholder (pre-register a
# sweep, cite the resulting optimum, update this comment). Corrected
# pointer (honesty batch); the prior phrasing here implied direct coverage
# that was never true.
````

## module — original line 335 (comment)

````text
# E2 fear extinction / inhibitory learning (Bouton 2004; Milad & Quirk 2012).
# When set (not None), the store should write this value to the memory's
# ``extinction_strength`` column — a REVERSIBLE inhibitory tag that suppresses
# the effective retrieval weight WITHOUT deleting the trace, so the
# association can spontaneously recover (decay) or be reinstated (cleared).
# None (the default) means "leave the extinction tag untouched" — no
# behaviour change. This is distinct from ``action == "archive"`` (the
# erasure-style heat penalty / soft-delete regime): extinction keeps the
# memory fully present.
````

## module — original line 347 (comment)

````text
# source: none — engineering default, calibration pending. Bounded so the
# recall-time bump can never dominate the thermodynamic decay signal that
# drives the heat WRRF weight; these are tie-breakers, not filters. Same
# unsourced-+0.05-magnitude family as the entity Hebbian bump
# (infrastructure/pg_store_relationships.py:181) and the wiki citation
# bump (pg_schema.py WIKI_TRIGGERS_DDL, cfd8e4c3) — internally consistent
# but not independently derived. See docs/provenance/blend-weight-
# calibration.md for the procedural precedent this codebase follows to
# graduate an "engineering default" to a cited, measured value (that doc
# itself does NOT cover this constant — see the module-docstring note
# above for the corrected pointer).
````

## module — original line 440 (comment)

````text
# Re-storage in the labile window. Heat bump scaled by
# emotional_multiplier (engineering default, see decide_action) so
# emotionally-loaded memories receive a proportionally larger
# reconsolidation gain (≤ 1.8x at full arousal).
````

## module — original line 451 (comment)

````text
# Bower (1981): the retrieval context's affective load shifts
# the re-stored emotional tag toward the current mood. Step
# bounded so a single retrieval cannot flip valence sign.
````

## module — original line 465 (comment)

````text
# action == "none" — passive retrieval, small thermodynamic touch.
# Below mismatch threshold the memory is not re-stored, but the
# retrieval event still updates last_accessed (Nader 2000 implies
# access tracking even without re-storage, since the labile window
# opens regardless).
````

## module — original line 480 (comment)

````text
# ── E2 reversible extinction (Bouton 2004; Milad & Quirk 2012) ─────────────
#
# A reversible, non-erasing alternative to the "archive" destabilization
# regime. Where `active_forgetting` deletes/soft-deletes a memory and the
# reconsolidation "archive" branch applies an erasure-style heat penalty,
# extinction grows a REVERSIBLE inhibitory tag that suppresses the effective
# retrieval weight while leaving the trace fully intact. The original
# association returns on its own over time (spontaneous_recovery) and is
# restored in full on reinstatement. Delegates all tag arithmetic to
# `mcp_server.core.extinction`; this bridge only maps a memory dict +
# operation to a ReconsolidationOutcome the caller persists via
# `store.update_memory_extinction`.
````

## module — original line 540 (comment)

````text
# _deprecate already applies the ablation guard: when ablated it returns
# operation="noop" with the tag unchanged. Surface None so the store
# leaves the column untouched in that case.
````
