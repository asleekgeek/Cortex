---
title: "ADR-0179 — mcp_server/core/extinction.py rationale"
status: accepted
source: mcp_server/core/extinction.py
---

# ADR-0179 — mcp_server/core/extinction.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 4 (docstring)

````text
Cortex already has two ways to *remove* a memory's influence. `active_forgetting`
marks a row ``is_stale`` (a reversible soft-delete that hides the whole memory
from recall) or lowers its heat; `reconsolidation.decide_action` returns an
``"archive"`` verdict on a large retrieval mismatch. Both are subtractive: the
association is taken out of circulation. What neither models is *extinction* in
the learning-theory sense — the association is left fully intact and a NEW,
separately-stored inhibitory association grows over it and competes to suppress
the response. The defining consequence is REVERSIBILITY: because the original
trace was never touched, it returns on its own with the passage of time
(spontaneous recovery) and snaps back in full when the situation that produced
the inhibition is undone (reinstatement). Erasure has no such comeback.
````

## module — original line 16 (docstring)

````text
Neuroscience basis (DOIs verified against Crossref):
  - Bouton (2004), "Context and behavioral processes in extinction,"
    Learning & Memory 11(5):485-494 (doi:10.1101/lm.78804). Extinction does
    not erase the original learning; it is new, context-dependent inhibitory
    learning. The original association survives and re-expresses as spontaneous
    recovery (time), renewal (context shift), and reinstatement (re-exposure to
    the reinforcer) — the direct evidence that extinction is additive
    inhibition, not deletion.
  - Milad & Quirk (2012), "Fear extinction as a model for translational
    neuroscience: ten years of progress," Annual Review of Psychology
    63(1):129-151 (doi:10.1146/annurev.psych.121208.131631). The ventromedial
    prefrontal cortex exerts top-down inhibitory control over the amygdala's
    stored fear association — an inhibitory overlay on a retained trace, the
    anatomical statement of the same "suppress, don't erase" principle.
````

## module — original line 31 (docstring)

````text
Design (pure business logic — no I/O). An extinction *tag* is a single scalar,
``extinction_strength`` in [0, 1], carried alongside the memory (0 = no
extinction, the default; higher = more strongly suppressed). It is the strength
of the competing inhibitory association, NOT a change to the memory's own
stored strength. Retrieval reads an EFFECTIVE strength:
````

## module — original line 37 (docstring)

````text
    effective = base_strength * (1 - extinction_strength)
````

## module — original line 39 (docstring)

````text
so a fully-extinguished memory (tag = 1) is driven to zero *effective* recall
while its ``base_strength`` (heat) is left untouched on the row — which is the
whole point: undo the tag and the original value is exactly what it was.
````

## module — original line 43 (docstring)

````text
Three operations model Bouton's three re-expression routes plus the acquisition
of inhibition:
````

## module — original line 46 (docstring)

````text
  apply_extinction   — grow the inhibitory tag toward 1 (each unreinforced
                       "extinction trial" adds inhibition with diminishing
                       returns; the base strength is never written).
  spontaneous_recovery — the inhibition itself DECAYS with elapsed time, so the
                       suppressed association gradually returns on its own
                       (Bouton 2004: recovery is a property of the inhibitory
                       memory being less retrievable later, not of the original
                       trace strengthening).
  reinstate          — collapse the tag toward 0 in one step, restoring the
                       original association in full (Bouton 2004: reinstatement
                       after re-exposure to the reinforcer).
````

## module — original line 58 (docstring)

````text
Honesty note (zetetic standard, matching attentional_control.py /
source_monitoring.py / habituation.py): this is a deterministic, reversible
suppressing OVERLAY — a single scalar masking factor — not a learned inhibitory
circuit and not a second stored memory trace. "Extinction" here is an analogy to
the inhibitory-learning account (Bouton 2004; Milad & Quirk 2012): the module
reproduces the *directions* those papers establish — suppression that spares the
original trace, time-driven spontaneous recovery, and one-step reinstatement —
but the numbers are fixed engineering constants, not parameters fit to
behavioural extinction curves (no source supplies rate laws at this store's
timescale). It is deliberately DISTINCT from active_forgetting: forgetting
removes a memory from circulation (is_stale / heat drop); extinction leaves the
memory fully present and only lowers its *effective* retrieval weight through a
factor that can be decayed (recovery) or cleared (reinstatement). No tag
(extinction_strength = 0) means no behaviour change at all — the effective
strength equals the base strength. This module reads no clock and touches no
store; elapsed time is supplied by the caller as hours.

````

## apply_extinction — original line 121 (docstring)

````text
    Each trial adds inhibition with diminishing returns toward MAX_EXTINCTION:
    ``new = old + gain * (MAX_EXTINCTION - old)`` per trial. This strengthens
    the competing inhibitory association (Bouton 2004); it does NOT modify the
    memory's base strength. Idempotent in the limit — repeated trials approach
    but never exceed MAX_EXTINCTION.
````

## spontaneous_recovery — original line 146 (docstring)

````text
    Spontaneous recovery (Bouton 2004): with no further extinction trials, the
    inhibitory memory becomes less retrievable over time, so the suppressed
    association gradually re-expresses. Modelled as exponential decay of the tag
    with ``half_life_hours``. Below RECOVERY_FLOOR the tag snaps to 0 (recovery
    complete). Note this decays the INHIBITION, never the base strength — the
    original trace was never altered.
````

## reinstate — original line 170 (docstring)

````text
    Reinstatement (Bouton 2004): re-exposure to the reinforcer abolishes the
    extinction and the original responding returns in full. Because the base
    strength was never touched, clearing the tag (default ``residual = 0``)
    restores the exact pre-extinction effective strength. A small non-zero
    ``residual`` can be passed to model extinction "savings" (faster
    re-extinction), but the default is a full restore.
````

## deprecate — original line 239 (docstring)

````text
    The reversible counterpart to active_forgetting's delete/archive — the
    memory stays fully present; only its inhibitory tag grows. Honors
    ``CORTEX_ABLATE_EXTINCTION=1`` (and ``Mechanism.EXTINCTION``): when ablated
    the tag is left unchanged and the effective strength equals the base
    strength (behaviour-preserving no-op), so a store with the mechanism lesioned
    behaves exactly as one that never deprecated anything.
````

## module — original line 81 (comment)

````text
# ── Constants (fixed engineering values — see the honesty note) ───────────────
````

## module — original line 83 (comment)

````text
# One unreinforced "extinction trial" adds this much inhibition, with
# diminishing returns toward the ceiling (see apply_extinction). 0.35 makes a
# single deprecation clearly suppressive (~0.35) without one-shot silencing, so
# repeated deprecation is needed to fully extinguish — the graded acquisition
# Bouton describes.
````

## module — original line 94 (comment)

````text
# Spontaneous-recovery half-life (hours): the inhibitory tag loses half its
# strength every this-many hours with no further extinction, so a suppressed
# association returns on its own over days (Bouton 2004). 72h ≈ 3 days to half
# recovery — slow enough that deprecation is durable, fast enough that an
# un-refreshed suppression does not become a permanent silencing.
````

## module — original line 101 (comment)

````text
# Below this residual, spontaneous recovery is treated as complete and the tag
# snaps to 0 (avoids an asymptotic tail that never clears).
````

## module — original line 105 (comment)

````text
# Reinstatement is a single-step near-collapse of the tag (Bouton 2004: the
# original responding returns in full). Left as a small residual rather than a
# hard 0 so a reinstated-then-re-extinguished memory re-acquires inhibition
# faster (savings), matching the faster re-extinction extinction shows; set to
# 0.0 for an exact restore. Default clears it.
````
