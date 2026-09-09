---
title: "ADR-0173 — mcp_server/core/emotional_tagging.py rationale"
status: accepted
source: mcp_server/core/emotional_tagging.py
---

# ADR-0173 — mcp_server/core/emotional_tagging.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Detects emotional markers in content using VADER compound sentiment
(Hutto & Gilbert 2014) combined with domain-specific keyword co-occurrence.
Emotionally tagged memories get higher importance and resist decay,
consistent with the general finding that emotional memories consolidate
better (McGaugh 2004, "The amygdala modulates the consolidation of
memories of emotionally arousing experiences", Annual Review of
Neuroscience).
````

## module — original line 11 (docstring)

````text
Arousal inverted-U: implemented as a * arousal * exp(-b * arousal),
peak at arousal ≈ 1/b. The arousal-performance tradeoff is usually
credited to Yerkes & Dodson (1908), but that study measured optimal
stimulus intensity vs. task difficulty in mice and never plotted an
inverted-U against arousal; the arousal inverted-U ("Hebb's curve") is
Hebb (1955). This smooth c*a*exp(-b*a) parameterization is a modern
functional form, not from either paper.
````

## module — original line 19 (docstring)

````text
Emotion detection uses VADER compound score (Hutto & Gilbert 2014) to
derive five emotion categories from compound polarity + domain keyword
co-occurrence. Constants (thresholds, scaling factors) are hand-tuned.
````

## module — original line 23 (docstring)

````text
Pure business logic — no I/O.

````

## detect_emotions — original line 85 (docstring)

````text
VADER-derived emotion detection (Hutto & Gilbert 2014).
````

## compute_arousal — original line 152 (docstring)

````text
RMS of emotion intensities. Engineering heuristic — no paper.
````

## arousal_inverted_u_bump — original line 194 (docstring)

````text
    Returns ``c * a * exp(-b * a)`` with ``b = 1/peak`` and ``c`` chosen so the
    bump attains ``peak_height`` at ``a = peak`` (``c = peak_height * b * e``).
    The full importance multiplier is ``1.0 + arousal_inverted_u_bump(a)``.
````

## arousal_inverted_u_bump — original line 202 (docstring)

````text
    The arousal inverted-U is Hebb's curve (Hebb 1955, "Drives and the C.N.S.
    (conceptual nervous system)," Psychological Review 62:243-254,
    doi:10.1037/h0041823); Yerkes & Dodson (1908) established the
    stimulus-intensity/task-difficulty tradeoff but did not measure arousal.
    This smooth ``c*a*exp(-b*a)`` form is a modern parameterization, not from
    either paper. Factored here so stress_modulation.py (D1) can reuse the exact
    same bump rather than re-deriving the constants.
````

## compute_importance_boost — original line 223 (docstring)

````text
    Arousal inverted-U: f(a) = c * a * exp(-b * a) + 1.0
    where a = arousal, b controls peak location, c scales amplitude.
    With b=1.43 (peak at a=1/b≈0.7), c≈2.213 (peak value ≈ 1.57).
    The arousal inverted-U is Hebb's curve (Hebb 1955); Yerkes & Dodson
    (1908) established the stimulus-intensity/difficulty tradeoff but did
    not measure arousal. This smooth c*a*exp(-b*a) form is a modern
    parameterization, not from either paper.
````

## compute_importance_boost — original line 231 (docstring)

````text
    Specific emotion bonuses are engineering heuristics (no paper):
    - Urgency: +0.3 (critical events must be remembered)
    - Discovery: +0.2 (insights are valuable)
    - Frustration: +0.1 (errors teach lessons)
````

## module — original line 35 (comment)

````text
# Arousal below this floor gives no decay resistance.
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## module — original line 40 (comment)

````text
# Arousal above this threshold marks a memory as emotionally significant.
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## module — original line 243 (comment)

````text
# Smooth Yerkes-Dodson: f(a) = 1.0 + c * a * exp(-b * a)
# b = 1/0.7 ≈ 1.4286 => peak at arousal = 0.7; c ≈ 2.213 => peak value 1.57.
# The bump is factored into arousal_inverted_u_bump so stress_modulation.py
# (D1) reuses the identical Hebb curve; defaults reproduce this exactly.
````
