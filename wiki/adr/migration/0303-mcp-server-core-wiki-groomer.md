---
title: "ADR-0303 — mcp_server/core/wiki_groomer.py rationale"
status: accepted
source: mcp_server/core/wiki_groomer.py
---

# ADR-0303 — mcp_server/core/wiki_groomer.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
The grooming system has two parts:
````

## module — original line 5 (docstring)

````text
  1. **Auditor** (this module, deterministic): scans every wiki page,
     reports drift against the page's kind template. Fast, runs every
     consolidate cycle. Produces a structured list of issues (missing
     front-matter, wrong status value, non-canonical slug, missing
     required section).
````

## module — original line 11 (docstring)

````text
  2. **Rewriter** (claude-agents/cortex-wiki-groomer.md, LLM): handed the
     audit output + the raw page, rewrites to the template while
     preserving content semantics. Runs on-demand when the auditor
     reports issues, or when the user invokes /cortex:groom-wiki.
````

## module — original line 16 (docstring)

````text
This module is pure-functional — no I/O, no LLM calls. The auditor's
output is structured so tests can assert on it and the LLM rewriter
has an unambiguous work list.
````

## module — original line 20 (docstring)

````text
Source: user directive "agent or llm on side to write with template and
naming conventions to keep it tidy and up to date".

````

## page_audit_has_issues — original line 59 (docstring)

````text
A free function, not a method: mutmut categorically excludes the
    body of any `@dataclass`-decorated class (`mutmut/mutation/
    file_mutation.py:236`), so logic placed on `PageAudit` methods would
    carry zero mutation coverage no matter how the test loader names the
    module (issue #262 3rd pass; issue #282).
    
````

## audit_wiki — original line 210 (docstring)

````text
    Returns audits only for pages with issues (groomed pages are
    filtered out to keep the output focused on the work list).
    
````

## module — original line 73 (comment)

````text
# source: structural — a quoted scalar needs both an opening and a closing
# quote character, so it is at least two characters long.
````
