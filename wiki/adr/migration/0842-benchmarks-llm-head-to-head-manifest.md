---
title: "ADR-0842 — benchmarks/llm_head_to_head/manifest.py rationale"
status: accepted
source: benchmarks/llm_head_to_head/manifest.py
---

# ADR-0842 — benchmarks/llm_head_to_head/manifest.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Every scored run emits a ``manifest.json`` in
``benchmarks/llm_head_to_head/results/<runid>/`` containing every field
listed in §10. Missing fields → run downgraded to *exploratory* per
``docs/provenance/verification-protocol.md`` global invariants.
````

## git_tree_dirty — original line 147 (docstring)

````text
    pre: ``repo_root`` is a git checkout (or returns clean if not).
    post: returns (is_dirty, list of changed files); the file list is
      capped at 200 entries to keep the manifest readable.
    
````

## write_manifest — original line 272 (docstring)

````text
    pre: results_dir parent exists.
    post:
      - returns the path to the written file.
      - raises RuntimeError if the secret-audit finds suspected keys
        (defence in depth — keys must NEVER reach disk).
    
````

## module — original line 40 (comment)

````text
# Values that should NEVER appear in a manifest (defence in depth).
````
