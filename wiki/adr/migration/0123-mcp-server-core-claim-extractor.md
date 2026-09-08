---
title: "ADR-0123 — mcp_server/core/claim_extractor.py rationale"
status: accepted
source: mcp_server/core/claim_extractor.py
---

# ADR-0123 — mcp_server/core/claim_extractor.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Deterministic, pattern-based extractor that turns a memory's content
into a list of typed ClaimEvents (Hopper IR layer 1).
````

## module — original line 6 (docstring)

````text
Pure logic — no I/O, no LLM calls. The LLM-augmented refinement step
lives in a separate handler that wraps this with prompt-driven
enrichment when needed.
````

## module — original line 10 (docstring)

````text
The extractor splits content into candidate sentences, classifies each
by pattern matching against eight ClaimType buckets, and pulls out
evidence references (file paths, URLs, citations, commit SHAs).
````

## module — original line 14 (docstring)

````text
Sentences that match no pattern are dropped — silent rejection is the
default, mirroring the wiki classifier's positive-signal philosophy.

````

## _classify_sentence — original line 161 (docstring)

````text
Return (claim_type, confidence) for a sentence, or None if it
    matches no pattern. None → drop the sentence (default-reject).
    
````

## extract_claims — original line 262 (docstring)

````text
    Process:
      1. Strip fenced code blocks (don't classify code as prose claims).
      2. Split into candidate sentences.
      3. Classify each sentence by pattern; drop unclassified.
      4. Pull document-level evidence refs (URLs, files, papers, commits).
      5. Attach evidence refs to every claim from this content (a single
         shared evidence pool — refining per-claim attribution is a
         later optimization).
````

## module — original line 43 (comment)

````text
# source: pre-existing tuned values, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## module — original line 148 (comment)

````text
# references — line that is essentially a URL / citation / doi
````

## module — original line 228 (comment)

````text
# ── Supersedes detection ─────────────────────────────────────────────
````
