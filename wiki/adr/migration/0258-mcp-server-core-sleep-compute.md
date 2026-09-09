---
title: "ADR-0258 — mcp_server/core/sleep_compute.py rationale"
status: accepted
source: mcp_server/core/sleep_compute.py
---

# ADR-0258 — mcp_server/core/sleep_compute.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Biologically inspired offline consolidation pass:
  1. Dream replay:  re-process hot memories through enrichment pipeline
  2. Cluster summarization: synthesize text summaries for fractal L1/L2 clusters
  3. Re-embedding:  re-encode stale/compressed memories with current encoder
  4. Auto-narration: generate a brief project narrative and store as semantic memory
````

## module — original line 9 (docstring)

````text
Pure business logic — no I/O.  All storage is done by the caller (consolidate handler).

````

## _replay_updates_for — original line 38 (docstring)

````text
    Returns update dicts ``{memory_id, enriched_content}``. The hottest set is
    chosen by the streaming heap in ``run_sleep_compute_streamed`` (bounded),
    so this only ever processes ``max_replay`` items.
    
````

## _accumulate_keywords — original line 128 (docstring)

````text
    O(words-in-text) work, O(vocabulary) memory — independent of corpus size,
    so it composes into the single streaming pass.
    
````

## run_sleep_compute_streamed — original line 194 (docstring)

````text
    Every full-list scan in the legacy pass is a BOUNDED reduction, so the
    whole computation needs only O(max_replay + max_reembed + vocab) RAM
    regardless of corpus size:
      - dream replay  → a size-``max_replay`` min-heap of hottest memories;
      - re-embedding  → the first ``max_reembed`` stale memories;
      - narration     → a streaming keyword-frequency dict + running top-1
        importance + a count.
    Peak RAM is one chunk plus those bounded accumulators — so it scales to
    millions of memories. ``run_sleep_compute`` delegates here with a single
    chunk for callers that already hold a list.
````

## run_sleep_compute_streamed — original line 205 (docstring)

````text
    Targeted memory reactivation (F2). The bounded replay heap keys on a replay
    *priority*, not raw heat. With no cue (``cue is None`` / empty) the priority
    is exactly ``heat``, so the hottest set retained and its ordering are
    identical to the pre-F2 pass (identity). With a cue, each memory's priority
    is ``heat + cue_boost * cue_match_score(cue, mem)`` (see
    ``targeted_reactivation``), so cue-matching memories are preferentially
    retained in the bounded top-``max_replay`` set and enriched first — the
    cue-directed replay of Rasch et al. (2007). The cue only ever *adds* a
    non-negative boost. This function stays pure; the ablation guard
    (Mechanism.TARGETED_REACTIVATION) is applied by the caller
    (``sleep_phases``), which passes ``cue=None`` when the mechanism is ablated.
    
````

## run_sleep_compute — original line 285 (docstring)

````text
    Thin wrapper over ``run_sleep_compute_streamed`` (one chunk) so existing
    list-holding callers keep working; new callers should stream chunks. The
    optional ``cue`` (F2 targeted reactivation) is forwarded verbatim; no cue
    means the pass is identical to pre-F2.
    
````

## module — original line 26 (comment)

````text
# Content shorter than this many characters is skipped by dream replay
# enrichment.
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## module — original line 47 (comment)

````text
# Skip already-enriched content to avoid double-appending.
````

## module — original line 226 (comment)

````text
# Consumer-side supersession skip. The chunks come from the decay
# cursor (iter_memories_for_decay), which MUST keep seeing
# superseded physical rows so decay/forgetting/homeostatic keep
# cooling them — so the cursor cannot filter. Sleep, however,
# SERVES content: replay re-enriches the row and the narration
# folds its content into a new semantic memory. A superseded
# version must reach neither. Single-occurrence filter at the
# consumer boundary, per the read-path supersession audit
# (docs/program/pr2-read-path-supersession-audit.json).
````

## module — original line 240 (comment)

````text
# Replay priority = heat + cue boost. No cue → priority == heat, so
# the retained hottest set and its order are byte-for-byte the
# pre-F2 selection (identity).
````
