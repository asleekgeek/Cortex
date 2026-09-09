---
title: "ADR-0168 — mcp_server/core/dual_process_retrieval.py rationale"
status: accepted
source: mcp_server/core/dual_process_retrieval.py
---

# ADR-0168 — mcp_server/core/dual_process_retrieval.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Human memory retrieval is not one process but two. *Familiarity* is a fast,
a-contextual sense that an item has been encountered before — a scalar signal
of prior exposure available almost immediately, with no recovery of the item's
associated context. *Recollection* is a slower, contextual reconstruction that
brings back the specifics — where and when the item was encountered and what
accompanied it. The two dissociate behaviourally and anatomically: familiarity
is associated with perirhinal cortex, recollection with the hippocampus.
````

## module — original line 11 (docstring)

````text
Cortex already has the *shape* of this dissociation in its retrieve→rerank
pipeline. A cheap first-pass fusion (``recall_memories`` WRRF) surfaces
candidates; an expensive post-WRRF chain (Hopfield completion, HDC, spreading
activation, dendritic modulation, emotional/mood reranking, reconsolidation,
FlashRank, value/conflict) reconstructs the contextual ordering. What was
missing is the *early gate*: a lightweight a-contextual familiarity signal read
BEFORE the expensive chain, so an overwhelmingly-familiar query can be answered
without paying for full reconstruction (two-stage retrieval — cheap recall +
expensive rerank — is standard IR practice).
````

## module — original line 21 (docstring)

````text
Neuroscience basis (DOIs verified against Crossref):
  - Yonelinas (2002), "The Nature of Recollection and Familiarity: A Review of
    30 Years of Research," Journal of Memory and Language 46(3):441-517
    (doi:10.1006/jmla.2002.2864). Recollection and familiarity are separable
    retrieval processes: familiarity is fast and scales with a graded
    strength/similarity signal; recollection is a slower, threshold-like
    recovery of the study context.
  - Diana, Yonelinas & Ranganath (2007), "Imaging recollection and familiarity
    in the medial temporal lobe: a three-component model," Trends in Cognitive
    Sciences 11(9):379-386 (doi:10.1016/j.tics.2007.08.001). A
    medial-temporal-lobe division of labour: perirhinal cortex signals item
    familiarity, parahippocampal cortex encodes context, and the hippocampus
    binds item-to-context for recollection.
````

## module — original line 35 (docstring)

````text
Design (pure business logic — no I/O). The familiarity signal is the MAX vector
cosine similarity between the query and the retrieved candidates — a single
a-contextual scalar, computed with NO context assembly (no entity graph, no
spreading activation, no reconstruction). Three primitives are exposed:
````

## module — original line 40 (docstring)

````text
  (a) ``familiarity_score(similarities)`` — the max-similarity gate itself.
  (b) ``assess_familiarity(similarities)`` — the gate plus supporting scalars
      (mean, and the top1↔top2 margin that says whether one item clearly wins).
  (c) ``recollection_needed(signal)`` / ``triage(candidates, similarities)`` —
      the decision: familiarity is SUFFICIENT only when it is overwhelming (max
      similarity over threshold AND a single clearly-dominant match); every
      weaker case needs slow contextual recollection. ``triage`` additionally
      annotates each candidate with its per-candidate familiarity without
      changing order or membership.
````

## module — original line 50 (docstring)

````text
Honesty note (zetetic standard, matching value_learning.py / source_monitoring.py
/ attentional_control.py): "familiarity" here is a max-vector-cosine-similarity
HEURISTIC, and "recollection" is the pre-existing rerank chain — this is NOT a
trained dual-process model (no ROC / dual-process-signal-detection fit à la
Yonelinas, no separately-parameterised familiarity vs. recollection estimators).
The threshold and margin are fixed engineering constants, not values learned
against a task-performance signal. The mapping to neuroscience is structural
(a fast a-contextual scalar gate before slow contextual reconstruction), not a
claim that the max-similarity value equals a perirhinal familiarity strength.
The default triage does NOT skip recollection — it only annotates; the
latency-saving short-circuit is opt-in and fires only on an overwhelming,
unambiguous familiarity hit, so it never silently changes what a normal recall
returns.

````

## FamiliaritySignal — original line 100 (docstring)

````text
    ``familiarity`` — MAX similarity (the fast a-contextual gate; Yonelinas 2002).
    ``mean``        — mean similarity across the set (a diffuse-vs-peaked proxy).
    ``margin``      — top1 − top2 similarity; how clearly one item wins. Equals
                      ``familiarity`` for a singleton set (no competitor).
    ``n``           — number of similarity values the signal was computed over.
    ``method``      — how the similarities were obtained (see METHOD_* tags);
                      only ``METHOD_VECTOR`` is faithful enough to permit a
                      recollection short-circuit.
    
````

## familiarity_signal_as_dict — original line 118 (docstring)

````text
A free function, not a method: mutmut categorically excludes the
    body of any `@dataclass`-decorated class (`mutmut/mutation/
    file_mutation.py:236`), so logic placed on `FamiliaritySignal` methods
    would carry zero mutation coverage no matter how the test loader names
    the module (issue #262 3rd pass; issue #282).
    
````

## TriageResult — original line 137 (docstring)

````text
    ``candidates``          — the candidate dicts, each annotated with its own
                              ``familiarity`` (when similarities align 1:1);
                              order and membership are UNCHANGED.
    ``signal``              — the set-level FamiliaritySignal.
    ``recollection_needed`` — True iff the query needs slow contextual
                              recollection (the default assumption).
    ``shortcut``            — True iff the caller opted in AND familiarity is
                              overwhelming AND the signal is a faithful vector
                              read: recollection may be skipped for latency.
                              False by default so recall output never changes.
    
````

## familiarity_score — original line 159 (docstring)

````text
    A single scalar of prior-exposure strength (Yonelinas 2002), computed with
    no context assembly. Returns 0.0 for an empty set.
    
````

## recollection_needed — original line 200 (docstring)

````text
    Familiarity is SUFFICIENT (recollection NOT needed) only when it is
    overwhelming and unambiguous:
      - the signal is a faithful vector read (``METHOD_VECTOR``), AND
      - max similarity >= ``threshold``, AND
      - a single candidate clearly wins: either there is only one candidate,
        or the top1↔top2 ``margin`` >= ``margin``.
    Every weaker or non-vector case returns True — recollection is the default.
    This asymmetry is deliberate: the cheap familiarity gate may only *skip*
    reconstruction on an unmistakable hit, never on a marginal one.
    
````

## triage — original line 232 (docstring)

````text
    ALWAYS annotates each candidate with its per-candidate ``familiarity`` (the
    similarity that fed the gate) when ``similarities`` aligns 1:1 with
    ``candidates`` — order and membership are preserved exactly. It computes the
    set-level FamiliaritySignal and the ``recollection_needed`` decision.
````

## triage — original line 237 (docstring)

````text
    ``shortcut`` is True ONLY when the caller passes ``allow_shortcut=True`` AND
    familiarity is overwhelming AND the signal is a faithful vector read. With
    the default ``allow_shortcut=False`` the result never licenses skipping
    recollection, so a caller that always runs the full chain sees an unchanged
    (only annotated) candidate list.
````

## module — original line 69 (comment)

````text
# ── Constants (fixed engineering defaults — NOT learned) ────────────────────
# Above this max cosine similarity a single candidate is "familiar enough" that
# its prior-exposure signal is unambiguous. Deliberately high: cosine ~0.92 is a
# near-duplicate / almost-exact match, the regime where a-contextual familiarity
# alone is trustworthy. Below it, the graded familiarity signal is not decisive
# and contextual recollection is required (Yonelinas 2002: familiarity is graded;
# only its high tail behaves like a clean old/new signal).
````

## module — original line 78 (comment)

````text
# The top-1 similarity must beat the top-2 by at least this margin for the hit to
# count as a *single clearly-dominant* match. Guards against the case where many
# candidates are all highly similar (a diffuse, ambiguous set) — that is exactly
# when recollection is needed to pick among them, not when familiarity suffices.
# Waived for a singleton candidate set (nothing competes).
````

## module — original line 91 (comment)

````text
# source: structural — a top1↔top2 margin exists only when at least two
# candidates compete
````

## module — original line 186 (comment)

````text
# top1 − top2; for a singleton there is no competitor, so margin = top.
````

## module — original line 191 (comment)

````text
# ── (c) the decision ──────────────────────────────────────────────────────────
````
