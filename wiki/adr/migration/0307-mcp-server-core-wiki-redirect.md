---
title: "ADR-0307 — mcp_server/core/wiki_redirect.py rationale"
status: accepted
source: mcp_server/core/wiki_redirect.py
---

# ADR-0307 — mcp_server/core/wiki_redirect.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 1 (docstring)

````text
Redirect stubs for renamed wiki pages — Phase 3 of ADR-2244.
````

## module — original line 3 (docstring)

````text
When a page is renamed (e.g. ``adr/_general/2234-decision-001-zero-
dependencies.md.md`` → ``adr/_general/2234-zero-dependencies.md`` during
Phase 4 slug-bug cleanup), the wiki leaves a *redirect stub* at the old
path. The stub has minimal body and a frontmatter declaration that
points readers at the new path.
````

## module — original line 9 (docstring)

````text
The canonical pattern (MediaWiki ``#REDIRECT`` page, TYPO3 page redirect,
GitLab page-renamed redirect): the old path keeps responding to reads
so inbound links continue to resolve, the reader is silently moved to
the new content, and bulk migration becomes safe.
````

## module — original line 14 (docstring)

````text
Stub frontmatter shape::
````

## module — original line 16 (docstring)

````text
    ---
    redirect_to: <new wiki-relative path>
    redirect_id: <UUID4 of the target page>
    redirect_reason: <free-form, optional>
    created: <ISO-8601 UTC timestamp when the stub was minted>
    ---
````

## module — original line 23 (docstring)

````text
    # Moved
````

## module — original line 25 (docstring)

````text
    This page has moved to [<new title>](<new path>).
````

## module — original line 27 (docstring)

````text
Either ``redirect_to`` (path-based) or ``redirect_id`` (ID-based) is
sufficient. When both are present, the ID wins — paths are mutable but
IDs are stable. This module accepts either form.
````

## module — original line 31 (docstring)

````text
Cycle and depth protection
--------------------------
````

## module — original line 34 (docstring)

````text
A redirect chain longer than ``MAX_REDIRECT_DEPTH`` (default 5) returns
None from ``resolve_chain``. This matches MediaWiki convention and keeps
adversarial or accidental cycles from hanging the reader.
````

## module — original line 38 (docstring)

````text
This module is pure logic — no I/O. Callers (``wiki_read`` handler,
migration scripts) read the on-disk content and pass it in.

````

## Redirect — original line 58 (docstring)

````text
    Fields:
        target_path: wiki-relative path the reader should follow, or
            empty string if only the ID is specified.
        target_id: page ID of the destination, or None if only the path
            is specified.
        reason: free-form rationale (e.g. "slug bug fix 2026-05-13"),
            empty string when not given.
    
````

## redirect_is_id_based — original line 83 (docstring)

````text
    A free function, not a method: mutmut categorically excludes the body
    of any `@dataclass`-decorated class (`mutmut/mutation/file_mutation.py:
    236`), so logic placed on `Redirect` methods would carry zero mutation
    coverage no matter how the test loader names the module (issue #262
    3rd pass; issue #282).
    
````

## build_redirect_stub — original line 207 (docstring)

````text
    At least one of ``target_path`` / ``target_id`` must be supplied.
    The body is a single sentence so readers who land on the stub
    directly see a clear "this moved" notice.
````

## build_redirect_stub — original line 205 (mixed-contract-rationale)

````text
    Args:
        target_path: wiki-relative path of the new home.
        target_id: stable page ID of the new home (preferred when known).
        target_title: human-readable title for the link text.
        reason: optional free-form rationale.
        created_at: ISO-8601 UTC timestamp; left blank if not supplied.
````

## parse_frontmatter — original line 258 (docstring)

````text
    Handles the three observed shapes (scalar, inline list, block list).
    Sufficient for redirect detection — full YAML parsing is not needed
    because redirect stubs are minimal and machine-written.
    
````

## module — original line 190 (comment)

````text
# Exhausted max_depth — refuse to keep walking.
````
