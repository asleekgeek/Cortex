---
title: "ADR-0292 — mcp_server/core/wiki_axis_registry.py rationale"
status: accepted
source: mcp_server/core/wiki_axis_registry.py
---

# ADR-0292 — mcp_server/core/wiki_axis_registry.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
User direction (2026-05-12): "having only 4 values for each is a band-aid
fix, we should be able to manage anything using regex and recognition."
````

## module — original line 6 (docstring)

````text
This module replaces the hardcoded ``KINDS`` / ``LIFECYCLES`` / ``AUDIENCES``
/ ``PROVENANCES`` frozensets from ``mcp_server.shared.wiki_classification``
with an open-world registry. The set of values for each classification
axis is the union of:
````

## module — original line 11 (docstring)

````text
    1. Python defaults declared in ``wiki_axis_defaults.py`` (bootstrap seed)
    2. User-added markdown files under ``wiki/_schema/<axis>/<value>.md``
````

## module — original line 14 (docstring)

````text
Adding a new audience, lifecycle, kind, or provenance is done by writing
a markdown file with frontmatter — no Python edit required. Each value
ships its own regex detection patterns so the classifier composes the
4-tuple from pattern matches, not from hard-coded enum checks.
````

## module — original line 19 (docstring)

````text
Schema file format::
````

## module — original line 21 (docstring)

````text
    wiki/_schema/audiences/data-scientist.md
    ---
    name: data-scientist
    axis: audience
    display_name: Data scientist
    patterns:
      - '\\b(dataset|train(ing)?|inference|model|notebook|jupyter)\\b'
      - '\\b(scikit|pandas|numpy|pytorch|tensorflow)\\b'
    tag_aliases: [ds, ml, data]
    default: false
    ---
````

## module — original line 33 (docstring)

````text
    # Data scientist audience
````

## module — original line 35 (docstring)

````text
    Pages targeting practitioners building or analysing ML systems.
````

## module — original line 37 (docstring)

````text
Unknown values fail validation; the error message proposes the closest
match via ``difflib.get_close_matches`` (user direction 2026-05-12:
"reject + suggest").
````

## module — original line 41 (docstring)

````text
Module split (issue #134, coding-standards.md §4 — this file was 705
lines, over the 500-line hard limit): the default seed data for every
axis (kinds/lifecycles/audiences/provenances) now lives in
``wiki_axis_defaults.py``. This module keeps the ``AxisValue``/
``AxisRegistry`` data model, schema-file parsing, lookup helpers
(``match_axis``, ``did_you_mean``), and the reverse-DI wiki-root
provider (kept here because tests monkeypatch its module-level global
directly).

````

## AxisValue — original line 82 (docstring)

````text
    Fields:
        name: stable identifier (kebab-case, lowercase).
        axis: which axis this value belongs to (``kind`` / ``lifecycle`` / ...).
        display_name: human-readable label.
        patterns: compiled regex patterns; a content match contributes
            this value to the classification.
        tag_aliases: alternate names that may appear as memory tags;
            a tag match contributes this value to the classification.
        default: True if this is the default for new pages on this axis
            (e.g. ``seedling`` for lifecycle on non-ADR kinds).
        requires_generator: provenance-only — when True, a Classification
            whose ``provenance`` is this value must include a Generator
            block (model/version/prompt_template/generated_at).
        applies_to_kinds: lifecycle-only — restricts this value to a
            subset of kinds. Empty tuple = applies to all kinds.
        description: free-form documentation extracted from the page body.
    
````

## axis_registry_values — original line 127 (docstring)

````text
    A free function, not a method: mutmut categorically excludes the body
    of any `@dataclass`-decorated class (`mutmut/mutation/file_mutation.py:
    236`), so logic placed on `AxisRegistry` methods would carry zero
    mutation coverage no matter how the test loader names the module
    (issue #262 3rd pass; issue #282).
    
````

## build_default_registry — original line 183 (docstring)

````text
    Imports ``wiki_axis_defaults`` lazily (function-local, not at module
    top) because that module imports ``AxisValue``/``AXIS_*`` back from
    this one to build its default seed data — a module-level import
    here would be circular.
    
````

## match_axis — original line 347 (docstring)

````text
    For lifecycle, ``restrict_to_kind`` filters out values whose
    ``applies_to_kinds`` is set and does not include the kind (so an
    ADR cannot be classified as ``seedling`` and a non-ADR cannot be
    ``proposed``).
    
````

## configure_default_wiki_root — original line 398 (docstring)

````text
    Call once at MCP server boot. Core never imports
    ``infrastructure.config`` directly — see issue #126.
    
````

## inline — original line 188 (directive-rationale)

````text
# noqa: PLC0415 — import cycle with mcp_server.core.wiki_axis_defaults; a top-level import fails at boot
````

## module — original line 222 (comment)

````text
# End previous list if any
````

## module — original line 367 (comment)

````text
# Universal lifecycle values do not apply to ADRs (ADRs use
# the proposed/accepted/rejected/superseded subset).
````

## module — original line 380 (comment)

````text
# ── Lazy singleton — cached for in-process classifier calls ─────────────
#
# Reverse DI (issue #126): core declares the *shape* of what it needs (a
# zero-arg callable returning the default wiki root) rather than importing
# ``infrastructure.config.WIKI_ROOT`` directly. The composition root
# (``mcp_server/__main__.py``) calls ``configure_default_wiki_root`` once
# at process boot with the real path; tests inject a fixture path the same
# way. No provider configured → ``get_registry()`` yields the seed-only
# defaults (still correct, just without user ``_schema/`` overrides).
````
