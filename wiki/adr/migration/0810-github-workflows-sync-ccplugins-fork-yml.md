---
title: "ADR-0810 — .github/workflows/sync-ccplugins-fork.yml rationale"
status: accepted
source: .github/workflows/sync-ccplugins-fork.yml
---

# ADR-0810 — .github/workflows/sync-ccplugins-fork.yml

Source rationale preserved verbatim. Identifiers inside historical quotations are not current identities.

## .github/workflows/sync-ccplugins-fork.yml:jobs.sync.steps.2.run — original line 8

````text
# Try ff-only first — that preserves history if we had any
# local commits that somehow landed. Fall back to hard reset
# (the fork is meant to be a clean mirror, not an author).
````
