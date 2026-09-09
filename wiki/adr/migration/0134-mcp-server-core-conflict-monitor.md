---
title: "ADR-0134 — mcp_server/core/conflict_monitor.py rationale"
status: accepted
source: mcp_server/core/conflict_monitor.py
---

# ADR-0134 — mcp_server/core/conflict_monitor.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 4 (docstring)

````text
A recall can return items that co-activate but contradict each other: one memory
says a decision holds, another reports it was reversed; one says a build passes,
another that it fails. Cortex ranks these purely by relevance, so two mutually-
incompatible memories can sit side by side at the top of the list with nothing
noticing the disagreement. In the brain that situation — several strong,
incompatible responses active at once — is exactly what the anterior cingulate
is thought to detect, signalling prefrontal cortex to raise cognitive control.
````

## module — original line 12 (docstring)

````text
Neuroscience basis (DOIs verified against Crossref):
  - Botvinick, Braver, Barch, Carter & Cohen (2001), "Conflict monitoring and
    cognitive control," Psychological Review 108(3):624-652
    (doi:10.1037/0033-295X.108.3.624). The ACC detects *response conflict* — the
    simultaneous activation of incompatible responses — and this conflict signal
    drives an increase in top-down control. Botvinick operationalises conflict
    as Hopfield-style energy over co-active competing units, a scalar computable
    from the units' activations.
  - Miller & Cohen (2001), "An Integrative Theory of Prefrontal Cortex
    Function," Annual Review of Neuroscience 24(1):167-202
    (doi:10.1146/annurev.neuro.24.1.167). Prefrontal cortex represents and
    maintains the control signals that bias processing toward task-appropriate
    responses when conflict is high.
````

## module — original line 26 (docstring)

````text
Design (pure business logic — no I/O). Two scalars are computed over the
retrieved set and combined:
````

## module — original line 29 (docstring)

````text
  ENTROPY (co-activation) — the retrieval scores are turned into an activation
      distribution via a numerically-stable softmax (the same shift-by-max
      stabilisation hopfield.py uses), and the Shannon entropy of that
      distribution, normalised to [0, 1] by log(n), measures how *distributed*
      activation is. A single dominant winner has low entropy (no competition);
      several near-tied items have high entropy (many co-active competitors).
      This is the tractable proxy for Botvinick's Hopfield energy: energy is
      high only when several mutually-inhibitory units are strongly co-active,
      and a flat activation distribution is the retrieval-side signature of
      exactly that.
````

## module — original line 40 (docstring)

````text
  CONTRADICTION — a lexical, pairwise measure of whether two co-active items
      actually *disagree*: shared-topic overlap (Jaccard over content tokens)
      multiplied by polarity divergence (one item carries negation/reversal
      markers about the shared topic and the other does not). High only when two
      items talk about the same thing with opposite polarity.
````

## module — original line 46 (docstring)

````text
  CONFLICT SCORE — the product of the two: ``conflict = max_contradiction *
      entropy``. BOTH must be present: a contradiction between co-active
      near-tied competitors scores high (both terms near 1), while a
      contradiction against a clearly dominant winner scores ~0 (entropy ~0 —
      the disagreement is easy to resolve, one item plainly wins), and a healthy
      recall whose top items are all relevant but consistent scores 0 (no
      contradiction). Contradiction is thus necessary and co-activation gates
      it.
````

## module — original line 55 (docstring)

````text
When the score crosses a threshold the set is *in conflict*; the competing pair
with the highest contradiction is identified and its lower-scoring member (the
"losing" memory) is down-weighted, and — when the candidates carry the typed
claim metadata the claim resolver needs — the pair is additionally routed to
``claim_resolver.plan_conflicts`` so the disagreement is surfaced as data.
````

## module — original line 61 (docstring)

````text
Honesty note (zetetic standard, matching value_learning.py / source_monitoring.py
/ attentional_control.py): this is a heuristic scalar computed over retrieval
scores and candidate text, NOT a trained ACC model and NOT Botvinick's actual
Hopfield-energy network — normalised softmax entropy is a monotone proxy for
that energy, chosen because it is computable directly from the scores the recall
pipeline already produces. Contradiction detection is lexical/polarity-based
(shared tokens + negation markers), NOT semantic entailment: it cannot tell that
"the release shipped" contradicts "we cancelled the launch" without shared
surface tokens, and it will not detect contradictions that hinge on world
knowledge, and it treats polarity as a binary presence-of-negation flag — a
genuine double negation ("not un-shippable") is read as negative, not as a
return to positive. The threshold and the two blend weights are fixed engineering
constants, not parameters fit against a labelled conflict signal. The routing to
``claim_resolver`` reuses the existing typed-claim conflict detector unchanged;
this module adds only the retrieval-time scalar and the down-weight.

````

## _topic_tokens — original line 243 (docstring)

````text
    Negation markers are stripped here because they measure *polarity*, not
    *topic* — including them would let two negations spuriously overlap.
    
````

## _has_negation — original line 259 (docstring)

````text
    Presence-based, not parity-based: natural text stacks reinforcing negatives
    ("not complete, it failed") far more often than it genuinely double-negates
    ("not un-shippable"), so counting parity would wrongly cancel the common
    case. The cost is that a true double negation is NOT detected as a return to
    positive polarity — a documented limitation (see the module honesty note),
    not a bug.
    
````

## score_entropy — original line 294 (docstring)

````text
    0 = one item dominates (no competition); 1 = all items equally active (a
    completely flat distribution). Fewer than two scores return 0.0 — a single
    item cannot compete with itself. The normalisation is by ``log(n)`` (the
    entropy of the uniform distribution over n items) so the value is comparable
    across result-set sizes.
    
````

## ConflictAssessment — original line 348 (docstring)

````text
    ``conflict_score``    — the gated, entropy-amplified scalar in [0, 1] the
                            threshold is compared against.
    ``entropy``           — normalised softmax entropy of the scores (co-activation).
    ``max_contradiction`` — the highest pairwise contradiction found (0 if none).
    ``competing_pair``    — (memory_id_a, memory_id_b) of the most-contradictory
                            pair, or None when no contradiction was found.
    ``loser_id``          — the memory_id of the lower-scoring member of the
                            competing pair (the one a resolver would down-weight),
                            or None.
    ``high``              — True iff ``conflict_score >= threshold``.
    
````

## conflict_assessment_as_dict — original line 369 (docstring)

````text
A free function, not a method: mutmut categorically excludes the
    body of any `@dataclass`-decorated class (`mutmut/mutation/
    file_mutation.py:236`), so logic placed on `ConflictAssessment` methods
    would carry zero mutation coverage no matter how the test loader names
    the module (issue #262 3rd pass; issue #282).
    
````

## apply_downweight — original line 476 (docstring)

````text
    No-op (returns the input unchanged) when the assessment is not ``high`` or
    carries no ``loser_id``. When it fires, the loser's ``score`` is multiplied
    by ``(1 - penalty)`` and the list is re-sorted by score descending, so the
    contested-and-weaker memory drops below its corroborated rivals. The winner
    is left untouched — this demotes the loser rather than boosting the winner,
    keeping the operation conservative.
    
````

## route_to_resolver — original line 500 (docstring)

````text
    This reuses ``claim_resolver.plan_conflicts`` unchanged. It is only
    meaningful when the candidates carry the typed-claim metadata that detector
    needs — ``claim_type`` and ``entity_ids``. The retrieved set is treated as a
    self-contained batch: each candidate is also registered as a potential prior
    for every entity it mentions, so ``plan_conflicts`` can surface
    disagreeing-type pairs (e.g. a decision paired with a limitation) about
    shared entities.
````

## module — original line 87 (comment)

````text
# ── Tunable constants (env-overridable, like the recall_pipeline stages) ──────
# A set is "in conflict" when the gated score crosses this threshold. Chosen so
# that a genuine contradiction between two near-tied items (contradiction ~0.5,
# entropy ~1.0 -> conflict ~0.5) fires, while a contradiction against a clearly
# dominant winner (entropy ~0 -> conflict ~0.25) does not.
````

## module — original line 94 (comment)

````text
# Multiplicative penalty applied to the losing memory's score when a
# high-conflict pair is found. Deliberately partial: the loser is demoted, not
# removed — disagreement is data, and the caller may still want to see both.
````

## module — original line 172 (comment)

````text
# Stopwords excluded from topic-overlap. Deliberately does NOT include the
# negation markers above — those carry the polarity signal and must survive.
````

## module — original line 234 (comment)

````text
# source: floor documented in the _topic_tokens docstring ("keeping only
# tokens of length >= 3"); tuning provenance not recorded
````
