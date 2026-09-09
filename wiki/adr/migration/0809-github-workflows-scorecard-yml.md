---
title: "ADR-0809 — .github/workflows/scorecard.yml rationale"
status: accepted
source: .github/workflows/scorecard.yml
---

# ADR-0809 — .github/workflows/scorecard.yml

Source rationale preserved verbatim. Identifiers inside historical quotations are not current identities.

## .github/workflows/scorecard.yml — original line 3

````text
# Issue #178 criterion 6. Cortex adopts the ecosystem's single Scorecard
# definition as a CALL SITE, not a copy: the reusable workflow lives in
# cdeust/ai-architect-mcp-codebase (AP #66/#77) so the pinned action SHAs and the
# report-only policy are maintained in one place. Scorecard grades repo-level
# posture (branch protection, signing, review counts) and is language-
# agnostic, which is exactly the part of the supply-chain story that
# generalises — SBOM and build provenance stay per-repo in release.yml because
# their toolchains differ (uv/pip here, cargo there, pnpm in prd-gen).
````

## .github/workflows/scorecard.yml — original line 12

````text
# The first score is a BASELINE recorded as-is: a low number is a valid
# measurement (§8), not a failure, and this deliberately does not gate a PR —
# a contributor cannot fix repo-level policy inside their diff.
````

## .github/workflows/scorecard.yml — original line 24

````text
# REVERSAL NOTE (post-merge fix, issue #178): the call-site pattern
# (uses: cdeust/ai-architect-mcp-codebase/.../scorecard.yml@main) produced
# startup_failure on main — zero jobs spawned — and scorecard-action's
# publish_results requires the OIDC subject to be THIS repo's own
# default-branch workflow, so a cross-repo reusable call cannot publish
# even when it starts. In-repo canonical template instead; the pinned
# SHAs below match the AP definition and drift is caught by Scorecard
# itself flagging unpinned/stale actions. This workflow only runs on
# main/schedule, so PR CI could not have caught the failure: verified
# post-merge via workflow_dispatch.
````

## .github/workflows/scorecard.yml — original line 40

````text
# source: run 33806380608 (2026-09-03), max 40s; ceil(2 * 40 / 60).
````
