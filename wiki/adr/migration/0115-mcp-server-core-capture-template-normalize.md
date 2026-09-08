---
title: "ADR-0115 — mcp_server/core/capture_template_normalize.py rationale"
status: accepted
source: mcp_server/core/capture_template_normalize.py
---

# ADR-0115 — mcp_server/core/capture_template_normalize.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 1 (docstring)

````text
Pure normalization of auto-capture/derived-fact template boilerplate,
applied ONLY to the write-gate's NOVELTY DECISION (embedding-novelty
re-scoring and structural-novelty features) — never to the content that
gets stored, and never to the ``embedding`` column written by
``remember()``.
````

## module — original line 7 (docstring)

````text
Decision: M-D1 (docs design "memoire qui comprend", section 7.3).
````

## module — original line 9 (docstring)

````text
Scope narrowed by incident i7d3 (2026-07-11): the original M-D1 design
also normalized the STORED embedding (``remember.py``'s
``emb_engine.encode()`` call) and shipped a one-shot corpus backfill.
That stored-embedding path was measured to correlate with a LongMemEval
regression (MRR -0.05 to -0.13 across three runs, R@10 near floor —
a ranking-degradation profile) in a shared, contended benchmark
environment; root-cause investigation could not conclusively separate
"caused by this code" from "caused by a benchmark-container concurrency
hole" (the pure baseline on unmodified code regressed WORSE in the same
window, which argues against this code being the cause — but the
ambiguity itself was disqualifying under the zero-tolerance bench gate).
Per the tolerance-zero rule (rework or abandon, never negotiate), the
stored-embedding path was reverted (``remember.py`` and
``remember_helpers._do_merge`` both encode raw ``content`` again, exactly
as before M-D1) and the corpus backfill tooling was deleted. This module
is now wired ONLY into ``remember_helpers.compute_template_normalized_
similarities`` (embedding-novelty signal) and ``evaluate_gate``'s
structural-novelty call — both are write-gate DECISION inputs, computed
fresh at gate-evaluation time and discarded; neither ever reaches
storage or the recall vector space. This makes the mechanism
bench-neutral BY CONSTRUCTION, not just "not exercised by this
benchmark": grep confirms zero remaining callers of this module touch
the ``embedding`` column.
````

## module — original line 33 (docstring)

````text
Fact base (measured, i6d2 campaign, docs/campaigns/i6d2_near_dup_calibration_report.md):
the auto-capture template built by
``mcp_server.hooks.post_tool_capture._build_memory_content`` — a fixed
``# Tool: X`` header, a labeled reference line (``**Read:** ...``,
``**File:** ...``, ``**Command:** ...``, ``**Glob:** ...``,
``**Grep:** ...``), an ``## Output`` / ``**Output:**`` section label, code
fence delimiters, and an optional ``**Artifact:** ...`` pointer line —
drives cosine similarity to 0.95-0.99 between memories that reference
DIFFERENT entities (worst offender: pairs of ``**Read:**
`.../checkpoints/<uuid>.md``` differing only by UUID). At every
candidate threshold (0.75-0.95) measured precision was 0.02-0.10 — the
TEMPLATE, not the fact, drives the embedding.
````

## module — original line 46 (docstring)

````text
The derived-fact template written by
``mcp_server.core.curation.identify_derivable_facts`` (memify_derive,
INC6.1b) — ``"{src} and {tgt} are strongly linked ({type},
weight={w})"`` — is the same failure in miniature: the connective text
is shared by every derived fact, so distinct entity pairs collide in
embedding space (measured: 0 derived facts ever survived the write
gate, 20/20 rejected).
````

## module — original line 54 (docstring)

````text
Design constraint (append-only, Q3 arbitration): the STORED content is
never mutated, and — post i7d3 — neither is the STORED embedding. Only
transient strings handed to ``EmbeddingEngine.encode()`` for a gate
DECISION, and to ``_structural_features``, ever pass through this
function. This module is therefore pure (core layer, stdlib-only, zero
I/O) and idempotent — running it twice produces the same output as
running it once, because the stripped skeleton markers no longer match
on the second pass.
````

## module — original line 63 (docstring)

````text
Safety gate: the function only transforms content that matches one of
the two known templates byte-for-byte at the structural-marker level.
Deliberate memories and free-form notes are returned UNCHANGED. Because
no stored vector is ever touched (post i7d3), there is no write/read
vector-space coherence question left to reason about for the recall
path — the read-side query embedding (``recall_helpers.py``) and the
stored embedding column are BOTH always raw content, exactly as before
this module existed. The only remaining consumer of this function's
output is the write gate's own novelty arithmetic, computed fresh and
discarded every call.

````

## capture_template_normalize — original line 151 (docstring)

````text
    Contract:
      pre:  ``content`` is the RAW string that would otherwise be passed to
            ``EmbeddingEngine.encode()`` or to ``_structural_features``.
      post: if ``content`` matches the auto-capture header or the
            derived-fact connective sentence, returns the payload with the
            template skeleton removed (never the empty string — falls back
            to the original ``content`` if stripping the skeleton would
            leave nothing, so a representation is always produced).
            Otherwise returns ``content`` unchanged (deliberate memories
            and free-form notes are never touched).
      invariant: idempotent — ``f(f(x)) == f(x)`` for all ``x``, because
            the stripped markers no longer match the normalized output on
            a second pass.
    
````

## module — original line 85 (comment)

````text
# Labeled reference line prefixes — strip the LABEL, keep the payload
# (file path / command / pattern) that follows it. Stripping the payload
# too would destroy the only signal that distinguishes two captures of
# the same tool kind (out of scope for M-D1 — see decision doc §1.3,
# "payload collision" is a separate, deferred, read-path concern).
````
