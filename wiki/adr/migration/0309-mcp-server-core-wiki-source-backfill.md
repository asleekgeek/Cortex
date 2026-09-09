---
title: "ADR-0309 — mcp_server/core/wiki_source_backfill.py rationale"
status: accepted
source: mcp_server/core/wiki_source_backfill.py
---

# ADR-0309 — mcp_server/core/wiki_source_backfill.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 1 (docstring)

````text
Derive the primary documented source file for wiki pages that lack one
(ADR-0051 STEP 3).
````

## module — original line 4 (docstring)

````text
``wiki_reindex`` / ``migrate_wiki`` already backfill ``documents_primary``
for pages whose frontmatter *has* a ``documents``/``source_file_path``/
``file`` field (``mcp_server.shared.wiki_source_paths.extract_document_paths``).
This module closes the remaining gap: pages with no such field.
````

## module — original line 9 (docstring)

````text
Pure logic, no I/O — filesystem existence checks are injected via
``exists_fn`` so this module stays unit-testable without touching a real
tree, and so it can live in core/ per the Dependency Rule (core imports
shared/ + stdlib only; no ``os``/``pathlib`` here).
````

## module — original line 14 (docstring)

````text
Derivation is a strict priority chain; each step either produces exactly
one confident candidate or falls through — the zetetic anti-fabrication
standard (CLAUDE.md, coding-standards.md §8) forbids guessing a "most
likely" primary when the evidence is ambiguous:
````

## module — original line 19 (docstring)

````text
  1. **claim_evidence** — file paths cited as evidence on the page's
     source memory's claims (``pg_store_wiki_thermo.get_claim_file_refs_for_pages``).
     Accepted only when exactly one distinct normalized path is present;
     several candidates with no way to rank them is refused, not guessed.
  2. **codebase_grounding** — the wiki page's own ``rel_path`` slug,
     reversed into a plausible source path (mirrors
     ``scripts/wiki_rebucket_file_docs.py::_derive_target_path``'s
     ``path.replace("/", "-")`` forward transform). Accepted only if
     ``exists_fn`` confirms the reversed guess names a real file — the
     guess is never trusted on its own.
  3. **body** — a single source-file-shaped path cited in the page's
     lead + sections (reusing ``wiki_drift._extract_cited_paths``, not
     duplicating its regex/filter logic), accepted only if it resolves
     via ``exists_fn`` and no other groundable candidate ties with it.
````

## module — original line 34 (docstring)

````text
Returns ``None`` when no step produces an unambiguous, real-file-backed
candidate — the caller (``wiki_maintenance``) then leaves the page
unlinked for the next ``wiki_drift`` REASON_MISSING_LINK pass to surface
as a re-authoring job.
````

## module — original line 39 (docstring)

````text
Pre-condition:  ``page`` carries at least ``rel_path`` and ``domain``
                (str); ``lead``/``sections`` are optional and default to
                empty; ``claim_files`` entries are raw (not yet
                normalized) path strings; ``exists_fn`` answers whether a
                normalized, source-root-relative path names a real file.
Post-condition: the returned path (if any) is canonical per
                ``normalize_source_path`` and ``exists_fn`` returns True
                for it whenever the derivation step requires grounding
                (steps 2 and 3; step 1 is not filesystem-checked here —
                claim evidence is already a memory-derived fact, grounded
                at write time by the claim extractor).

````

## _from_claim_evidence — original line 96 (docstring)

````text
    Several candidates carry no ranking signal here (no per-ref weight
    is passed through ``get_claim_file_refs_for_pages``), so more than
    one distinct path is a refusal, not a guess.
    
````

## _from_codebase_grounding — original line 113 (docstring)

````text
    ``wiki_rebucket_file_docs._derive_target_path`` forward-transforms a
    source path into a slug via ``path.replace("/", "-")`` then
    ``slugify``. This reverses that specific transform (dashes back to
    slashes) on the page's filename stem. The guess is lossy (a source
    path containing a literal dash is indistinguishable from a directory
    separator) so it is NEVER trusted alone — only returned when
    ``exists_fn`` independently confirms a real file at that path.
    
````

## _from_body — original line 136 (docstring)

````text
    Reuses ``wiki_drift._extract_cited_paths`` (regex + wiki-internal /
    technology-name filtering) rather than duplicating it. Several
    groundable citations carry no signal for which is "primary" — a tie
    is a refusal, matching ``_from_claim_evidence``'s discipline.
    
````
