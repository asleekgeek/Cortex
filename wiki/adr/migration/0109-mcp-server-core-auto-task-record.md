---
title: "ADR-0109 — mcp_server/core/auto_task_record.py rationale"
status: accepted
source: mcp_server/core/auto_task_record.py
---

# ADR-0109 — mcp_server/core/auto_task_record.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
User direction 2026-05-18: every new task / bug / feature should be
treated with the same detailed approach. This module is the
machinery that turns a session ending with substantive work into a
draft ADR carrying the task-record contract (Entry / Mandatory
elements / How / Result / Serves) — the same shape humans use, so
nothing is below the level of importance.
````

## module — original line 10 (docstring)

````text
The draft is NOT a finished page. It pulls together:
````

## module — original line 12 (docstring)

````text
  * Commit messages made during the session (the user-stated intent).
  * Memories tagged with decision / lesson / fix during the session
    (the things the user explicitly chose to capture).
  * Changed files (the artifact of the work).
  * A frontmatter ``lifecycle: draft`` so the conversational LLM
    refines it on the next session via ``curate_wiki``'s re-author
    queue.
````

## module — original line 20 (docstring)

````text
Pure logic — the handler ``record_session_end`` invokes
``build_task_record`` with the inputs already in hand, then writes
the page via the existing wiki write path.

````

## TaskRecordInputs — original line 44 (docstring)

````text
    Kept as a DTO so the handler composes whatever it has without a
    long parameter list (Clean Architecture §4.4).
    
````

## _derive_title — original line 85 (docstring)

````text
    Priority:
      1. First commit message's subject line — usually states intent.
      2. First memory tagged ``decision``/``lesson`` — the user's
         explicit capture.
      3. Tool-heavy session with no commits / decision memories falls
         back to a generic title; the LLM refines it on the next pass.
    
````

## is_substantive — original line 114 (docstring)

````text
    The thresholds are deliberately lenient: anything with a commit
    earns a record. Tool-heavy read-only sessions need a fair amount of
    activity (5+ tools) AND some captured memories.
    
````

## module — original line 31 (comment)

````text
# Threshold below which a session isn't substantive enough to warrant a
# task-record. Tuned so a quick browse / read-only session doesn't
# pollute the wiki, but any session that produced commits, edits, or
# explicit memories above the floor gets documented.
````

## module — original line 156 (comment)

````text
# source: pre-existing tuned values, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````
