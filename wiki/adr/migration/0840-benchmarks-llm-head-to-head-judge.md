---
title: "ADR-0840 — benchmarks/llm_head_to_head/judge.py rationale"
status: accepted
source: benchmarks/llm_head_to_head/judge.py
---

# ADR-0840 — benchmarks/llm_head_to_head/judge.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Pairing (load-bearing for §11.3 blind judging):
  - Haiku 4.5 generator answers      → judged by GPT-4o
  - Gemini 2.0 Flash generator answers → judged by Claude Opus 4.7
  - GPT-4o-mini generator answers    → judged by Claude Opus 4.7
````

## module — original line 8 (docstring)

````text
Single-judge fallback (budget-tight): all answers judged by Opus only;
flag Haiku-judged-by-Opus as same-vendor in the manifest.
````

## parse_judge_output — original line 142 (docstring)

````text
    pre: ``text`` is the raw judge response. Per Appendix B, it is one
      JSON object per line with keys ``id`` and ``verdict``.
    post: returns a list of ``JudgeVerdict`` ordered by alphabetic
      condition (A, B, C, D — whichever subset is present). Missing or
      unparseable lines yield ``verdict='incorrect'`` as a conservative
      default (a missing verdict cannot count as correct).
    
````

## module — original line 70 (comment)

````text
# Deterministic hash via Python's ``hash`` is process-salted; use
# a stable arithmetic on the bytes instead.
````

## module — original line 75 (comment)

````text
# Add the protocol-fixed shuffle-seed base so different runs of the
# same code produce the SAME shuffles (protocol §10 manifest field
# ``shuffle_seed_base: 20260501``).
````
