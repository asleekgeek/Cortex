---
title: "ADR-0177 — mcp_server/core/entity_dedup_filters.py rationale"
status: accepted
source: mcp_server/core/entity_dedup_filters.py
---

# ADR-0177 — mcp_server/core/entity_dedup_filters.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Normalization, entropy gating, shingle/MinHash construction, and the three
false-positive blockers that keep near-miss-but-distinct labels from merging.
Ported from graphify's dedup pipeline (graphify/dedup.py) and adapted to
Cortex's entity model. Pure logic — no I/O.
````

## module — original line 8 (docstring)

````text
Constants are inherited from graphify's empirically-tuned pipeline; they are
re-validated by the dup-collapse benchmark (benchmarks/entity_dedup/). Each
carries its source below.

````

## entropy — original line 43 (docstring)

````text
Shannon entropy (bits/char) of the normalized label (Shannon 1948).
````

## make_minhash — original line 62 (docstring)

````text
MinHash over space-stripped shingles so 'a b' and 'ab' share shingles.
````

## is_variant_pair — original line 78 (docstring)

````text
    Only meaningful for short labels (< 12 chars); longer labels go through
    Jaro-Winkler normally. Source: graphify _is_variant_pair.
    
````

## short_label_blocked — original line 92 (docstring)

````text
    Insertions/deletions on short strings (cranel/cranelr, M1/M1 Pro) score high
    on Jaro-Winkler via the prefix bonus but are rarely true duplicates. Allow
    only a same-length, single-character substitution (a real typo like
    Extractor/Extractar). Source: graphify _short_label_blocked. ``jw_score`` is
    in [0, 1].
    
````

## is_affix_extension — original line 108 (docstring)

````text
    Prefix extensions (getActiveSession / getActiveSessions, parseConfig /
    parseConfigFile — graphify #1201) and suffix extensions (MemoryStore /
    PgMemoryStore, Store / FileStore) are specializations, not duplicates: the
    longer label adds a qualifier. Both inflate Jaro-Winkler via shared
    substrings. Block regardless of score.
    
````

## is_structural_identifier — original line 127 (docstring)

````text
    Cortex mis-types module identifiers like ``mcp_server.core.engram`` as
    ``technology``. These are code symbols whose identity is structural, not a
    fuzzy concept label — and their long shared prefixes (``mcp_server.core.``)
    inflate Jaro-Winkler past the merge threshold for unrelated modules. Exempt
    them from the fuzzy pass exactly as graphify exempts ``file_type=="code"``
    (graphify #1205). Multi-segment dotted paths (>= 2 dots, e.g.
    ``a.b.c``) and any slash path qualify; single-dot names (``Node.js``,
    ``Vue.js``) do not.
    
````

## affixes_sandwich_difference — original line 154 (docstring)

````text
    teststoreclassification / testcoreclassification share the prefix "test" and
    a long suffix ("classification") but differ in the middle (store/core) — the
    discriminating concept. Jaro-Winkler scores the shared majority high. Works
    on the normalized (glued) form, so it catches CamelCase identifiers that have
    no separators to tokenize on. When one middle is empty (the labels differ
    only by an affix, e.g. embeddingengine / embedding engine) this does not
    fire — that case is a real merge or handled by is_affix_extension.
    
````

## shared_prefix_masks_difference — original line 178 (docstring)

````text
    Jaro-Winkler's prefix bonus (Winkler 1990) was calibrated for short personal
    names; on longer strings a long common prefix over-credits the score even
    when the discriminating remainders differ. When the longest common prefix is
    at least half of the shorter label, require the post-prefix remainders to
    themselves clear MERGE_THRESHOLD — otherwise block. Defense-in-depth beyond
    is_structural_identifier for long shared-prefix concept labels.
    
````

## module — original line 23 (comment)

````text
# ── tunable constants (source: graphify graphify/dedup.py) ──────────────────
````

## inline — original line 24 (comment)

````text
# bits/char; gate out low-information labels (Shannon 1948)
````

## module — original line 69 (comment)

````text
# Trailing version/variant suffix: digits (+letters) like "v2", "A55", or a
# 2+ letter codename revision. Stem must end in a letter so plain words don't
# match. Source: graphify _VARIANT_SUFFIX.
````

## module — original line 118 (comment)

````text
# source: rule documented in is_structural_identifier docstring (graphify
# #1205 exemption) — multi-segment dotted paths have >= 2 dots; single-dot
# names like "Node.js" do not qualify
````

## module — original line 142 (comment)

````text
# strict=False: a common-prefix scan is defined precisely for strings of
# differing length (it stops at the shorter one).
````

## module — original line 164 (comment)

````text
# Clamp so prefix and suffix don't overlap on the shorter string.
````
