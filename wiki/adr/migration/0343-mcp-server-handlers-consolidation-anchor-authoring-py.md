# ADR-0343: mcp_server/handlers/consolidation/anchor_authoring.py implementation decisions

Status: accepted; preserved from the existing implementation during issue #514.

These are historical implementation records, not new algorithm or threshold choices.
Source: `mcp_server/handlers/consolidation/anchor_authoring.py`; original SHA-256 `301dc3c2feae8ac3f26e6b8b0b450c115fa09faf75e218f321a6bf4377c96800`.

## Original docstring, lines 1–19

````text
"""Anchor-page authoring for the headless authoring worker.

A project missing its architecture / services / api / ci-cd / mcp /
ai-usage / prd / decisions anchor page has no gap marker to drain — the
page simply doesn't exist. This module detects missing anchors via the
coverage audit, feeds Claude a project-level overview (file tree,
README, key config files, source file counts), and asks it to author
the anchor from scratch. Split out of ``drain_operations`` (Fowler:
Move Function, issue #276) to keep that module under the size limit;
the public import surface stays ``headless_authoring``, which
re-exports ``drain_missing_anchors``.

Import-cycle note (issue #237 family): a module-top ``from . import
headless_authoring as _root`` would deadlock a fresh interpreter
importing this module before ``headless_authoring`` finishes (it
imports ``drain_missing_anchors`` back at load time). ``_root`` is
resolved lazily at call time instead — every
``monkeypatch.setattr(headless_authoring, ...)`` stays observed.
"""
````

## Original comment, lines 114–116

````text
# Groundable-only filter: content that can't be derived from the
        # source tree alone (prd, decisions, changelog, roadmap, ...) is
        # skipped entirely rather than fabricated (zetetic-forbidden).
````

## Original comment, lines 148–148

````text
# Deferred import (issue #237): see module docstring's import-cycle note.
````

