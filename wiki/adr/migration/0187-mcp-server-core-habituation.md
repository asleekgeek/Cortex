---
title: "ADR-0187 — mcp_server/core/habituation.py rationale"
status: accepted
source: mcp_server/core/habituation.py
---

# ADR-0187 — mcp_server/core/habituation.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Habituation is the simplest form of learning: when a stimulus is presented
repeatedly, the response to it wanes. It is not sensory fatigue and not motor
exhaustion — it is a learned, stimulus-specific down-weighting that recovers
when the stimulus stops, and that a strong or novel event can reverse
(dishabituation) or transiently amplify (sensitization). Cortex has a novelty-
driven write gate but no memory of *how often it has already seen this same
thing*: a low-salience input that repeats identically N times produces the same
novelty verdict on the Nth pass as on the first, so near-duplicate churn is
admitted again and again. That is precisely the bloat habituation exists to
suppress.
````

## module — original line 14 (docstring)

````text
Neuroscience basis (DOI verified against Crossref):
  - Rankin, Abrams, Barry, Bhatnagar, Clayton, Colombo, Coppola, Geyer,
    Glanzman, Marsland, McSweeney, Wilson, Wu & Thompson (2009), "Habituation
    revisited: an updated and revised description of the behavioral
    characteristics of habituation," Neurobiology of Learning and Memory
    92:135-138 (doi:10.1016/j.nlm.2008.09.012). The consensus criteria of
    habituation. The four this module operationalises, by their numbering in
    that paper:
      (1) Repeated stimulation produces a progressive decrease in response,
          often to an asymptote; the decrement is frequently exponential.
      (2) Spontaneous recovery: if the stimulus is withheld, the response
          recovers over time.
      (4) Stimulus specificity: habituation to one stimulus does not transfer
          to a sufficiently different one.
      (8/9) Dishabituation / sensitization: presentation of a strong or novel
          stimulus restores (dishabituates) the habituated response, and a
          salient event can transiently raise responsiveness to other inputs.
````

## module — original line 32 (docstring)

````text
Design (pure business logic — no I/O). Two competing scalar gains multiply the
gate's existing novelty score:
````

## module — original line 35 (docstring)

````text
  RESPONSE GAIN (habituation) — an exponential decrement over the count of
      prior near-identical presentations of the *same* stimulus signature
      (criterion 1), floored so a repeat is damped but never silenced. The
      effective repeat count is first discounted by the idle time since the
      last presentation (criterion 2, spontaneous recovery), so a signature not
      seen for a while behaves as if partially or fully recovered. Specificity
      (criterion 4) is delegated to the caller's signature key: two inputs
      share a habituation history only if they share a signature.
````

## module — original line 44 (docstring)

````text
  SENSITIZATION FACTOR — after a salient event (importance above a threshold),
      responsiveness to subsequent inputs is transiently raised above baseline
      (criteria 8/9), decaying back to 1.0 over a fixed window. This both
      restores a habituated response (dishabituation) and briefly amplifies
      novelty for related inputs, so a salient burst is not itself suppressed
      by an unrelated habituation history.
````

## module — original line 51 (docstring)

````text
The combined gain (response_gain * sensitization_factor) multiplies novelty:
< 1 suppresses a repeated low-salience input toward rejection (bloat control);
> 1 amplifies novelty just after a salient event.
````

## module — original line 55 (docstring)

````text
Honesty note (zetetic standard, matching attentional_control.py /
source_monitoring.py): this is a heuristic decay over a repeat counter, not a
learned model of the stimulus. The decrement rate, the response floor, the
recovery rate, the sensitization amplitude, its decay window, and the salience
threshold are all fixed engineering constants, not parameters fit against a
behavioral dataset — Rankin's paper is a qualitative criteria list, not a
parameterised model, so no source supplies these numbers. The exponential form
and the recovery/specificity/sensitization *directions* follow the criteria;
the magnitudes are hand-tuned. Stimulus identity is whatever signature the
caller supplies (this module normalises text to a signature but does not
itself embed or cluster). Time is supplied by the caller as elapsed hours;
this module reads no clock and touches no store. It shares the NE-channel's
adaptation idea (neuromodulation_channels.NE_HABITUATION_RATE) but operates on
a different axis — per-stimulus response-gain over a repeat count, not the
arousal channel's error-driven adaptation scalar — so the two do not overlap.

````

## stimulus_signature — original line 117 (docstring)

````text
    Two inputs share a habituation history only if they share a signature.
    Normalisation lowercases, strips punctuation, and collapses whitespace so
    trivially-reformatted repeats of the same content collide, while genuinely
    different content does not. This is a deliberately coarse, exact-after-
    normalisation key — it does not cluster semantically (that is the caller's
    job if a softer notion of "same stimulus" is wanted).
    
````

## effective_repeats — original line 134 (docstring)

````text
    ``repeat_count`` is the number of prior presentations of this signature.
    Idle time since the last presentation returns "repeats worth" of credit at
    SPONTANEOUS_RECOVERY_PER_HOUR, so a long-unseen signature behaves as if
    partially or fully recovered. Never returns below 0.
    
````

## HabituationOutcome — original line 192 (docstring)

````text
    ``signature``          — the stimulus-identity key this decision used.
    ``modulated_novelty``  — the input novelty after applying the combined gain,
                             clamped to [0, 1]. This is what the gate compares
                             to its threshold.
    ``response_gain``      — the habituation component (<= 1.0; criteria 1 & 2).
    ``sensitization``      — the sensitization component (>= 1.0; criteria 8/9).
    ``combined_gain``      — response_gain * sensitization, the factor applied.
    ``effective_repeats``  — recovery-discounted repeat count used.
    ``suppressed``         — True iff the pass pushed novelty down (gain < 1),
                             i.e. a habituated repeat the gate is now likelier
                             to reject. The bloat-control signal.
    
````

## habituation_outcome_as_dict — original line 215 (docstring)

````text
A free function, not a method: mutmut categorically excludes the
    body of any `@dataclass`-decorated class (`mutmut/mutation/
    file_mutation.py:236`), so logic placed on `HabituationOutcome` methods
    would carry zero mutation coverage no matter how the test loader names
    the module (issue #262 3rd pass; issue #282).
    
````

## habituate_novelty — original line 254 (docstring)

````text
    Habituation (gain <= 1) suppresses repeated low-salience inputs toward
    rejection; sensitization (factor >= 1) transiently amplifies novelty after
    a salient event. The two multiply. Returns a HabituationOutcome; the caller
    uses ``modulated_novelty`` for the gate decision.
    
````

## module — original line 78 (comment)

````text
# ── Constants (fixed engineering values — see the honesty note) ───────────────
````

## module — original line 80 (comment)

````text
# Criterion 1: exponential response decrement per repeat. gain = exp(-rate * n).
# 0.35 gives a visible but gentle decrement — ~0.70 after one repeat, ~0.50
# after two — so a genuinely novel re-encounter is damped, not erased.
````

## module — original line 85 (comment)

````text
# Response floor: repetition damps novelty but never silences it. Even a heavily
# repeated stimulus keeps 15% of its novelty so the gate can still admit it if
# some other signal (importance, an entity) is strong.
````

## module — original line 90 (comment)

````text
# Criterion 2: spontaneous recovery. Effective repeat count decays by this many
# "repeats worth" of credit per idle hour, so a signature unseen for ~1.4 h
# recovers roughly one repeat of responsiveness; unseen long enough, it is fully
# recovered (effective repeats -> 0).
````
