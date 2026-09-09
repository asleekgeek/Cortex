# ADR-0357: mcp_server/handlers/consolidation/drain_operations.py implementation decisions

Status: accepted; preserved from the existing implementation during issue #514.

These are historical implementation records, not new algorithm or threshold choices.
Source: `mcp_server/handlers/consolidation/drain_operations.py`; original SHA-256 `ae387291b4d15b7ca42d3f103aa0a6d19f239b9b5e8ca80e1d5d46c3cda8c91c`.

## Original docstring, lines 1–15

````text
"""Per-page drain routines for the headless authoring worker.

Issues ``claude -p`` calls and rewrites wiki pages. Split out of
``headless_authoring`` (Fowler: Move Function); anchor-page authoring
is a separate concern, split further into ``anchor_authoring`` (issue
#276). The public import surface stays ``headless_authoring``, which
these names re-export.

Import-cycle note (issue #237): a module-top ``from . import
headless_authoring as _root`` would deadlock a fresh interpreter
importing this module before ``headless_authoring`` finishes (it
imports these functions back at load time). Each function resolves
``_root`` lazily at call time instead — every
``monkeypatch.setattr(headless_authoring, ...)`` stays observed.
"""
````

## Original comment, lines 154–154

````text
# Deferred import (issue #237): see module docstring's import-cycle note.
````

## Original docstring, lines 271–276

````text
"""Fill every curation gap on one page in a single ``claude -p`` call.

    One request/page (vs. ``drain_one``'s one/gap) is ~7-8x faster and
    keeps cross-references coherent; gap set is a LIVE AUDIT. One
    DrainResult per gap; a failure on one gap leaves others intact.
    """
````

## Original comment, lines 277–277

````text
# Deferred import (issue #237): see module docstring's import-cycle note.
````

