---
title: "ADR-0298 — mcp_server/core/wiki_coverage_dashboard.py rationale"
status: accepted
source: mcp_server/core/wiki_coverage_dashboard.py
---

# ADR-0298 — mcp_server/core/wiki_coverage_dashboard.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Meadows leverage-point audit 2026-05-18 identified Level 6 (information
flows) as a top-3 intervention: the system knows what's missing
(``curation_gaps`` per page, scope audit per project) but the user
doesn't unless they drill into 700 individual file-docs. The
dashboard surfaces the gap report as a single readable page per
project so the user (and the headless authoring worker) sees at a
glance what's covered, what's empty, and what's in progress.
````

## module — original line 11 (docstring)

````text
The dashboard for each project lives at::
````

## module — original line 13 (docstring)

````text
    wiki/_dashboards/<domain>.md
````

## module — original line 15 (docstring)

````text
Generated content — NOT human-authored. Regenerated on every
``consolidate`` cycle so it stays current.

````

## render_dashboard — original line 123 (docstring)

````text
    The page declares its kind / domain / scope and is structured so
    a non-technical reader sees: (a) the project's documentation
    completeness in one number, (b) which canonical slots are filled
    vs. empty, (c) how many file-doc pages still carry open gaps,
    (d) direct links into the existing anchor pages.
    
````

## module — original line 114 (comment)

````text
# How many uncovered source files the dashboard lists before truncating.
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## inline — original line 272 (directive-rationale)

````text
# noqa: BLE001 — mechanism boundary; failure is observable via silent_failure
````
