---
title: "ADR-0297 — mcp_server/core/wiki_coverage.py rationale"
status: accepted
source: mcp_server/core/wiki_coverage.py
---

# ADR-0297 — mcp_server/core/wiki_coverage.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Pure business logic — no I/O. The handler composes this with the wiki
filesystem scan.
````

## module — original line 6 (docstring)

````text
Problem this module solves
==========================
````

## module — original line 9 (docstring)

````text
The auto-curator (``mcp_server.core.auto_curator``) clusters memories by
dominant entity. That is bottom-up: it surfaces topics the user *worked
on*, but it can't see what the user *didn't write yet*. As a result,
high-traffic topics get many pages while structural scopes — overall
architecture, public APIs, data flow, runbooks — can remain undocumented
even when the codebase is mature.
````

## module — original line 16 (docstring)

````text
This module is the top-down counterpart. Given a project (domain), it
checks whether each canonical *scope* is documented and returns the
missing scopes as authoring intents the LLM can consume in the same
shape as cluster-driven jobs.
````

## module — original line 21 (docstring)

````text
Scopes (canonical, ordered by structural primacy)
-------------------------------------------------
````

## module — original line 24 (docstring)

````text
  * ``architecture`` — overall design, layers, dependency rule.
    Anchor page: ``reference/<domain>/architecture-overview.md``.
  * ``services`` — major components / modules / handlers / services.
    Anchor pages: ``reference/<domain>/<component>-overview.md``.
  * ``api`` — external surface (CLI, HTTP, MCP tools, library API).
    Anchor page: ``reference/<domain>/api.md``.
  * ``data-flow`` — read/write/consolidation paths, lifecycle of a
    record from ingest to retrieval.
    Anchor page: ``reference/<domain>/data-flow.md``.
  * ``operations`` — runbooks, deploy, observability, on-call.
    Anchor pages under ``runbook/<domain>/``.
  * ``decisions`` — task-records / ADRs. Anchor pages under
    ``adr/<domain>/``.
````

## module — original line 38 (docstring)

````text
Each scope is *covered* when at least one substantive page exists for it
under the right path. Substantive means: the file exists, is over a
minimum size, and is not a stub.
````

## module — original line 42 (docstring)

````text
Why not infer scopes from memory tags
-------------------------------------
````

## module — original line 45 (docstring)

````text
Memory tags are noisy and per-event. Scopes are stable structural
categories of *what every codebase needs documented*. Hard-coding the
six scopes is the right tradeoff: the list is short, the categories are
universal across the projects Cortex sees, and changes to the list are
a deliberate edit here, not an emergent property of tag drift.

````

## DomainCoverage — original line 950 (docstring)

````text
    Data only — deliberately no methods. mutmut's mutation generator
    categorically excludes the body of any `@dataclass`-decorated class
    (`mutmut/mutation/file_mutation.py:236`), so logic placed on methods
    here would carry zero mutation coverage no matter how the test loader
    names the module (issue #262 3rd pass; issue #282).
    `domain_coverage_covered_count` / `domain_coverage_missing_count` /
    `domain_coverage_coverage_ratio` / `domain_coverage_missing_scopes`
    below carry the same logic as free functions instead.
    
````

## _has_substantive_anchor — original line 994 (docstring)

````text
    A page is substantive when it exists and is at least ``_MIN_PAGE_BYTES``
    bytes. This guards against empty placeholders authored by the groomer
    or stub pages created by codebase_analyze.
````

## _has_substantive_anchor — original line 998 (docstring)

````text
    When ``max_age_days`` is set, an anchor page older than that window
    is treated as **stale** (returns None as if it didn't exist), so the
    auto-curator re-emits an authoring job. Existing pages get the same
    coverage discipline as missing ones — the wiki stays in sync with
    the codebase without a human in the loop.
    
````

## audit_domain — original line 1078 (docstring)

````text
    Coverage rules:
      * If the scope has anchor filenames, a substantive anchor page
        counts as coverage. ``services`` and ``api`` are pre-eminent
        anchor-based scopes.
      * If the scope has no anchor filenames (``decisions``), any
        substantive page in its directories counts after the minimum
        page count is met (default 1).
      * If ``max_age_days`` is set (default 90), anchor pages older than
        the window count as missing so the auto-curator refreshes them.
````

## _is_plausible_domain — original line 1138 (docstring)

````text
    Rejected:
      * Bare years (``2026``) — time buckets dropped into the wiki by
        slug normalisation, not real projects.
      * Names starting with ``.`` or ``_`` — reserved (``_general`` is
        an exception covered downstream).
    
````

## audit_all_domains — original line 1203 (docstring)

````text
Audit every discovered domain. Sorted by missing-count desc so the
    most under-documented projects surface first.
````

## audit_all_domains — original line 1206 (docstring)

````text
    ``max_age_days`` propagates to each per-domain audit so stale anchor
    pages count as missing.
    
````

## _index_wiki_file_references — original line 1347 (docstring)

````text
    Scans every ``.md`` page across all kinds; not domain-scoped because
    a domain's services may be referenced from cross-cutting pages. The
    domain argument is for future scoping if false-positive cross-domain
    matches become a problem.
    
````

## FileCoverage — original line 1389 (docstring)

````text
    Data only — see `DomainCoverage`'s docstring for why.
    `file_coverage_coverage_ratio` below carries the same logic as a free
    function instead.
    
````

## audit_files — original line 1410 (docstring)

````text
    A file is *covered* when its relative path OR its basename appears
    in the body of any wiki page. Returns the uncovered list capped at
    50 entries so a wide-open project doesn't balloon the return.
    
````

## module — original line 67 (comment)

````text
# Refresh window: a scope page older than this many days is considered
# stale and counts as missing again, so the auto-curator re-emits an
# authoring job to bring it back in line with the codebase. The wiki
# stays up to date without a human in the loop.
#
# 2026-05-18: 90 days is the conservative default. Pages move slowly;
# anchor pages (architecture / services / api) churn even more slowly.
# Callers that want a tighter cadence pass ``max_age_days`` to
# ``audit_domain`` / ``audit_all_domains``.
````

## module — original line 97 (comment)

````text
# Whether this scope's content is derivable by READING the source
# tree (Read/Glob/Grep only — the headless authoring worker has no
# git, no runtime, no human intent). When False, autonomous authoring
# of the anchor would be fabrication (zetetic-forbidden): the content
# lives in git history, future plans, or human decisions — not in the
# code. Such scopes are still surfaced as coverage gaps for a human;
# the headless drain skips them. Default True.
````

## inline — original line 321 (comment)

````text
# any spec or rfc page counts
````

## module — original line 324 (comment)

````text
# PRDs/RFCs encode human intent (problem framing, goals,
# non-goals) that is not present in the source tree — authoring
# one from code alone would be fabrication.
````

## module — original line 340 (comment)

````text
# ADRs record the rationale behind human decisions — the "why we
# chose X over Y" lives in people's heads and discussions, not in
# the code. Auto-authoring would invent that rationale.
````

## module — original line 362 (comment)

````text
# ── Task-oriented how-to guides (Diátaxis: how-to quadrant) ────────
#
# Onboarding above and code-walkthrough cover the learning + reading
# axes; what's missing is the *task-oriented* how-to layer — the
# guides a user hits when they have a concrete goal already
# (install, fix a known error, contribute). Three universal
# categories cover the bulk of project-level user demand:
````

## module — original line 856 (comment)

````text
# A changelog is reconstructed from git/release history, which the
# Read/Glob/Grep-only worker cannot access. Without a committed
# CHANGELOG.md it would invent release entries.
````

## module — original line 879 (comment)

````text
# A roadmap is forward-looking strategy — what's planned/deferred
# and why. None of that exists in the current source tree;
# authoring it would be pure fabrication.
````

## module — original line 884 (comment)

````text
# ── Inclusive design ───────────────────────────────────────────────
````

## module — original line 902 (comment)

````text
# Accessibility posture (WCAG level, screen-reader/keyboard
# support) is only groundable when UI a11y code exists; for the
# backend projects here it would be fabricated. A human authors
# the honest "not applicable — no UI" page.
````

## module — original line 926 (comment)

````text
# i18n/l10n posture is only groundable when an i18n library and
# strings files exist; otherwise it would be fabricated. A human
# authors the honest "single-locale" page.
````

## module — original line 1119 (comment)

````text
# Bare year buckets (notes/2026/*.md) — these are time buckets, not projects.
````

## module — original line 1124 (comment)

````text
# source: structural — a bare year slug ("2026") is 4 digits; see the
# "Bare years" rejection documented in _is_plausible_domain below.
````

## module — original line 1128 (comment)

````text
# A directory name must appear under at least this many kind directories to
# count as a real domain rather than a one-off.
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````

## module — original line 1217 (comment)

````text
# ── File-level coverage ────────────────────────────────────────────────
#
# Anchor-page coverage (above) ensures every project has the six
# structural scopes documented. File-level coverage is the second axis:
# every source file in the project must be referenced *somewhere* in
# the wiki. The reference can be inside an architecture page that lists
# the file, a services page that names it, a dedicated file-doc, or an
# ADR that touched it. Anything that isn't named anywhere is a hole.
#
# This is what "nothing should be left uncovered" means concretely:
# a reader following the wiki should never encounter a file in the
# repo that has no breadcrumb back to a wiki page.
````

## inline — original line 1296 (directive-rationale)

````text
# noqa: PLC0415 — optional-feature probe: ImportError here is a handled degraded mode
````

## module — original line 1318 (comment)

````text
# In-place filter so os.walk doesn't descend into skip dirs.
````

## module — original line 1327 (comment)

````text
# relpath emits backslashes on Windows; downstream indexing and
# comparisons assume '/'. source: REPORT_..._CORTEX_WINDOWS §5.3
````
