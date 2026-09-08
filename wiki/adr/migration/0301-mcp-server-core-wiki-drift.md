---
title: "ADR-0301 — mcp_server/core/wiki_drift.py rationale"
status: accepted
source: mcp_server/core/wiki_drift.py
---

# ADR-0301 — mcp_server/core/wiki_drift.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Pure logic, no I/O orchestration beyond filesystem reads.
````

## module — original line 5 (docstring)

````text
The autonomous wiki maintenance has three reject axes (stub, classifier,
deletion-by-rule). Drift is the **opposite** of deletion: a page that
*should* live on but is out of sync with the codebase. Examples:
````

## module — original line 9 (docstring)

````text
  * The page cites ``mcp_server/old/foo.py`` but that file was moved or
    deleted in a refactor. The page is now lying.
  * The page's frontmatter ``updated`` date is older than every source
    file it cites. The code has changed and the prose hasn't.
  * The page's structural sections (``## Status`` / ``## Decision``) are
    missing — the body drifted off-template.
````

## module — original line 16 (docstring)

````text
For each drift case we emit a *re-authoring job* — same wire shape as
the coverage and cluster jobs ``auto_curator`` produces, so a single
``curate_wiki`` call mixes new-page jobs, scope-fill jobs, and update
jobs into one queue the LLM consumes in order.
````

## module — original line 21 (docstring)

````text
Source for the policy: user direction 2026-05-18 — "All legacy or
preexisting documentation should be refined and verified and updated
accordingly. Every new task, new bug, new feature, as well as all
legacy existing element of a project should have the same level of
importance and should be treated with the same detailed approach."

````

## PageDrift — original line 43 (docstring)

````text
A single page that needs re-authoring, with the reason recorded.
````

## _is_likely_source_path — original line 137 (docstring)

````text
    Rejects:
      * Tokens whose first segment is a wiki-internal kind directory.
      * URL fragments and protocol-prefixed strings.
      * Bare technology names (``Node.js``, ``Three.js``) that the path
        regex captures only because they end in a code extension.
      * Empty tokens.
    
````

## _file_exists_under — original line 230 (docstring)

````text
    Tries the full relative path first, then the basename anywhere
    under the tree (rename-tolerant — a moved file still counts as
    present so we don't fire spurious drift jobs on every refactor).
    
````

## audit_page_drift — original line 268 (docstring)

````text
    Drift reasons are accumulated — a single page can hit multiple axes
    (missing source AND off-template), and the re-authoring prompt
    surfaces all of them so the LLM can fix everything in one pass.
    
````

## audit_wiki_drift — original line 356 (docstring)

````text
    ``source_root_resolver`` is a callable ``domain -> str | None`` —
    typically ``mcp_server.core.wiki_coverage._project_source_root``.
    Injected so this module stays unit-testable without touching the
    registry.
````

## audit_wiki_drift — original line 361 (docstring)

````text
    ``domain_filter`` restricts the scan to one project — applied
    *during* the walk so ``limit`` returns the first N drifts of that
    domain rather than the first N drifts overall (which might all be
    in other projects).
    
````

## module — original line 55 (comment)

````text
# Reason taxonomy — kept short so each entry is self-explanatory.
````

## module — original line 61 (comment)

````text
# Page kinds whose entire purpose is to document a source file — these are
# the kinds the STEP-3 backfill (core.wiki_source_backfill) targets, and
# the ones REASON_MISSING_LINK applies to. Restricted to ``reference``
# (the kind ``codebase_analyze``/rebucket route file-docs to, per
# CHANGELOG 3.15.4 "File-documentation pages") — pages of other kinds
# (adr, explanation, ...) don't claim to document one file, so an absent
# link there is not drift.
````

## module — original line 81 (comment)

````text
# Wiki-internal path prefixes — when a citation begins with one of these
# segments, it's a cross-reference to another wiki page (often shaped as
# ``reference/<domain>/<slug>.py.md`` flattened by the bulk migration),
# not a source-tree path. Those must NOT trigger the missing-source-file
# axis because they are not source files.
````

## module — original line 107 (comment)

````text
# Product names that _FILE_PATH_RE captures because they end in a code
# extension but are technologies, not files. Observed false positives:
# a page saying "zero-dep Node.js MCP server" was flagged for a missing
# source file ``Node.js`` (curate_wiki batch 4, 2026-06-11). Matched
# case-insensitively against the whole token.
````

## module — original line 210 (comment)

````text
# source: structural — the wiki layout is kind/domain/filename, so a valid
# relative path splits into at least three segments.
````

## module — original line 238 (comment)

````text
# Prune the same vendored / build dirs as list_source_files. Without this,
# a repo carrying a venv/, node_modules/, deps/, or site-packages/ at its
# root makes this per-cited-path fallback walk tens of thousands of files,
# turning one consolidate cycle into a multi-minute stall. The skip set is
# the single source of truth for "not a source tree".
````

## module — original line 291 (comment)

````text
# Reason 1: missing source files. Only check when we have a source
# root — domains without a checked-out tree (``_general``, etc.)
# can't be audited for this axis.
````

## module — original line 300 (comment)

````text
# Reason 2: stale content. Compute page age from mtime; the
# frontmatter ``updated`` is checked but mtime is the authoritative
# signal because frontmatter can lie / be groomed without prose
# changes.
````

## module — original line 316 (comment)

````text
# Reason 3: off-template. Check whether every required section for
# this kind is present in the body. Missing sections are loud
# structural drift — the groomer normally fixes this, but if the
# groomer is disabled or the page predates the current template the
# re-author pass catches it.
````

## module — original line 327 (comment)

````text
# Reason 4: missing source link. A source-documenting page (kind ==
# "reference") that declares no documented file in its frontmatter
# AND has no groundable cited path in its body is a page nobody can
# trace to a real file — the STEP-3 backfill
# (core.wiki_source_backfill.derive_primary_source) either couldn't
# find an unambiguous candidate or hasn't run yet. Surfaced as drift
# so it queues as a re-authoring job. Without a source_root we can't
# verify any citation, so an unlinked page is flagged regardless —
# this only affects backlog counts, nothing is deleted.
````

## module — original line 377 (comment)

````text
# Normalize to '/' so _kind_and_domain_from_path's path parsing
# works on Windows. source: REPORT_..._CORTEX_WINDOWS §5.3
````
