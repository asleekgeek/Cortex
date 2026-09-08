---
title: "ADR-0290 — mcp_server/core/value_learning.py rationale"
status: accepted
source: mcp_server/core/value_learning.py
---

# ADR-0290 — mcp_server/core/value_learning.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Cortex already computes a dopamine reward-prediction error
(``neuromodulation_channels.compute_dopamine_rpe``) but uses it only to
modulate the LTP rate of the memory currently being written. Nothing *accrues*
value over time, and nothing assigns credit backward from a session's outcome to
the memories that were actually used to produce it. This module adds that
missing layer: a learned scalar value per memory, updated by a temporal-
difference rule from session outcomes, with eligibility-trace credit assignment.
````

## module — original line 11 (docstring)

````text
Neuroscience / RL basis (all DOIs verified against Crossref):
  - Schultz, Dayan & Montague (1997), "A neural substrate of prediction and
    reward," Science 275:1593-1599 (doi:10.1126/science.275.5306.1593). Dopamine
    encodes a temporal-difference reward-prediction error δ = reward - V. We
    reuse the SAME actual-reward mapping the DA-RPE already uses
    (positive -> 0.7 + 0.3·importance, negative -> 0.2 - 0.1·importance,
    neutral -> 0.5) so the value layer and the neuromodulator agree on "reward."
  - Sutton & Barto (1998), "Reinforcement Learning: An Introduction," MIT Press.
    The TD(λ) value update V ← V + α·δ and eligibility traces: a memory used
    earlier in the recall set that led to a good outcome still gets credit,
    discounted by how long ago / how far down the recall list it was used.
  - Mnih et al. (2015), "Human-level control through deep reinforcement
    learning," Nature 518:529-533 (doi:10.1038/nature14236). TD-error learning
    of a value function at scale; the same error signal Cortex already computes,
    here turned into a persistent per-item value rather than a transient
    modulation gain.
````

## module — original line 28 (docstring)

````text
Scope / honesty note (zetetic standard, matching dual_store_cls.py and
procedural_memory.py): this is a tabular TD(0)/TD(λ) value estimator over
individual memories — a running, reward-weighted estimate — not a deep value
network. The papers motivate the design; Mnih 2015's contribution
(function approximation over raw pixels) is explicitly NOT implemented. The
value is a scalar bookkeeping signal, and the eligibility trace is a simple
geometric decay over recall rank, not a full TD(λ) backup through a trajectory.
````

## module — original line 36 (docstring)

````text
Boundary with existing machinery: this does NOT replace ``compute_dopamine_rpe``
(which stays the per-write LTP modulator). It consumes the same reward mapping
and produces a separate, persistent ``value`` that feeds retention (high-value
memories resist decay) and retrieval priority. Pure business logic — no I/O.
Handlers pass in the recalled-memory ids + session outcome and persist the
returned value updates.

````

## ValueUpdate — original line 106 (docstring)

````text
    Data only — deliberately no methods. mutmut's mutation generator
    categorically excludes the body of any `@dataclass`-decorated class
    (`mutmut/mutation/file_mutation.py:236`), so logic placed on methods
    here would carry zero mutation coverage no matter how the test loader
    names the module (issue #262 3rd pass; issue #282). ``value_update_as_dict``
    below carries the same logic as a free function instead.
    
````

## td_update — original line 143 (docstring)

````text
    ``V ← V + (alpha·eligibility)·(reward − V)`` (Sutton & Barto; the δ = reward
    − V term is Schultz's reward-prediction error). Returns
    ``(new_value, delta)`` where ``delta`` is the *unweighted* prediction error
    (reward − V) — the signed learning signal — and ``new_value`` is clamped to
    [0, 1].
    
````

## assign_credit — original line 173 (docstring)

````text
    Each memory at rank ``k`` (0-based) gets an eligibility trace
    ``trace_lambda**k`` — the top hit is fully responsible for the outcome, later
    hits progressively less (Sutton & Barto eligibility traces). The reward is
    the shared DA-RPE mapping, and each memory's value is TD-updated by its own
    trace-weighted step. Returns one ``ValueUpdate`` per recalled memory, in the
    same order.
````

## assign_credit — original line 180 (docstring)

````text
    A neutral session (neither positive nor negative) still produces updates —
    reward 0.5 pulls every value gently toward the neutral prior, which is the
    correct behaviour: a memory used in an unremarkable session should regress
    toward average, not hold an inflated value.
    
````

## retrieval_priority — original line 229 (docstring)

````text
    ``score' = base_score · (1 + weight·(value − prior))`` — a memory worth more
    than average gets a small ranking boost, one worth less a small penalty,
    proportional to how far its value is from the neutral prior. ``weight`` is
    deliberately small so value nudges rather than dominates content relevance.
    
````

## module — original line 48 (comment)

````text
# ── Tuning constants ────────────────────────────────────────────────────────
# TD learning rate: V <- V + alpha * (reward - V). Matches the combined
# alpha*beta = 0.1 used by compute_dopamine_rpe so the value layer learns at the
# same pace as the dopamine baseline it shadows (Daw 2011 range [0.01-0.25]).
````

## module — original line 54 (comment)

````text
# Eligibility-trace decay across the recall set (Sutton & Barto TD(lambda)).
# The k-th memory in a recall list of relevance-ranked results receives credit
# scaled by TRACE_LAMBDA**k — the top hit is most responsible for the outcome,
# later hits progressively less. 0.8 gives a gentle decay (5th item ~0.41).
````

## module — original line 60 (comment)

````text
# Value is bounded to [0, 1] to stay commensurate with the other [0,1] memory
# signals (importance, confidence, schema_match_score) it will be blended with.
````

## module — original line 70 (comment)

````text
# Reward mapping — IDENTICAL to neuromodulation_channels.compute_dopamine_rpe so
# the value layer and the dopamine signal never disagree on what "reward" means.
# Kept as a local constant set rather than an import to keep this module free of
# neuromodulation coupling; the shared source of truth is documented here and
# guarded by a test that asserts equality with the DA-RPE mapping.
````

## module — original line 133 (comment)

````text
# ── TD value update (Schultz / Sutton & Barto) ──────────────────────────────
````
