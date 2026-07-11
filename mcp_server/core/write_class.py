"""Write-class classification — the single choke point for M-D2/M-D3/7.4.

Design doc: ``scratchpad/memoire-qui-comprend-design.md`` §M-D2 (taxonomy
table) + §M-D3 (homeostatic stratification, this module's first consumer).

**Why this module exists.** Two independent M-series decisions need to know
"what kind of write is this memory" without disagreeing with each other:
M-D3 (this increment, 7.1) stratifies homeostatic regulation by class;
M-D2/7.4 will gate the write path itself by class. Both MUST resolve the
same memory to the same class, or the write gate and the homeostat argue
about the population they're each regulating. ``classify_write_class`` is
therefore THE single contract — every future writer classifies through
this function, never a parallel predicate.

**Today** (pre-7.4): classification is derived from ``memory["source"]``
(the only signal that exists in the schema today). **After 7.4** lands an
explicit ``write_class`` column, this function's FIRST check becomes that
column — see the ``explicit column`` branch below, already wired so 7.4 is
a data migration, not a second classification path. No double path is ever
introduced: this is the one function both increments call.

Taxonomy (M-D2 table, verbatim):

| Class       | Determination (source)                                    |
|-------------|------------------------------------------------------------|
| auto        | ``post_tool_capture``                                      |
| deliberate  | NOT IN (post_tool_capture, codebase_analyze, seed, ingest,  |
|             | cls, consolidation) — i.e. everything not otherwise listed |
| derived     | ``consolidation`` (memify_derive) + ``cls*`` (CLS semantic  |
|             | promotion — same rationale: machine-synthesized from the   |
|             | consolidation pipeline, not user intent, measured DB       |
|             | source distinct from ``consolidation`` but sharing the     |
|             | policy: idempotence markers judge duplication, not novelty)|
| mechanical  | backfill/ingest/seed/codebase_analyze — one-shot bulk       |
|             | import passes, not an ongoing population                   |

Pure logic. No I/O, no DB access — a classification is a projection of
data already in hand.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

AUTO = "auto"
DELIBERATE = "deliberate"
DERIVED = "derived"
MECHANICAL = "mechanical"

ALL_WRITE_CLASSES: tuple[str, ...] = (AUTO, DELIBERATE, DERIVED, MECHANICAL)

# source == post_tool_capture is the ONLY auto-capture pathway (audit,
# core/write_post_store.py::_AUTO_CAPTURE_SOURCES — same set, re-exported
# here rather than imported to keep this module dependency-free; the two
# are documented as required to move together).
_AUTO_SOURCES: frozenset[str] = frozenset({"post_tool_capture"})

# "consolidation" is memify_derive's exact source value
# (handlers/consolidation/memify_derive.py:245). Sources beginning with
# "cls" (cls-consolidation, measured: 59 rows in dev DB) are CLS semantic
# promotion — a second machine-synthesis pathway out of the consolidation
# pipeline, sharing derived's rationale (idempotence-judged, not
# novelty-judged; see M-D2's "derived" row justification).
_DERIVED_SOURCES: frozenset[str] = frozenset({"consolidation"})
_DERIVED_SOURCE_PREFIXES: tuple[str, ...] = ("cls",)

# Bulk/one-shot ingestion pathways (audit, core/source_monitoring.py::
# _EXTERNAL_PATHWAYS is the closest existing precedent set; this list adds
# codebase_analyze and generalizes the seed/ingest family, matching the
# M-D2 table's "mechanical" row and measured DB source values: backfill:*
# (prefix, one entry per scanned directory), seed_project, ingest_codebase).
_MECHANICAL_SOURCES: frozenset[str] = frozenset(
    {
        "codebase_analyze",
        "seed_project",
        "seed",
        "ingest_codebase",
        "ingest_prd",
        "ingest_findings",
        "ingest",
        "import",
        "import_sessions",
    }
)
_MECHANICAL_SOURCE_PREFIXES: tuple[str, ...] = ("backfill:",)

# SQL-side mirror of _AUTO_SOURCES, exported for the one call site
# (homeostatic._apply_fold) that must restrict a raw UPDATE to the auto
# class before the explicit write_class column exists (7.4). This is NOT
# a second classification path: it is the same frozenset, sorted for a
# stable parameter list. When 7.4 lands, that call site switches to
# ``WHERE write_class = 'auto'`` and this export is deleted in the same
# migration — documented in homeostatic.py::_apply_fold.
AUTO_SOURCE_VALUES: tuple[str, ...] = tuple(sorted(_AUTO_SOURCES))

# SQL-side mirror of "everything NOT deliberate" (auto | derived |
# mechanical), exported for pg_store_memory_reheat.py::
# list_deliberate_below_target — the other DB-facing call site besides
# homeostatic._apply_fold's AUTO_SOURCE_VALUES above. INC7.2 root-cause
# fix: that query used to carry its OWN hardcoded exact-match tuple
# ("seed", "ingest", "cls") that never matched the real DB values
# ("seed_project", "ingest_codebase", "cls-consolidation" — a PREFIX
# family, not an exact string) — a second, silently-diverged
# classification path that let mechanical/derived rows through the
# "deliberate" filter undetected. Exporting the exact-match and prefix
# sets here instead means there is exactly ONE place the taxonomy is
# defined; the SQL predicate cannot drift from ``classify_write_class``'s
# verdict again because it is built from the same frozensets.
NON_DELIBERATE_EXACT_SOURCES: tuple[str, ...] = tuple(
    sorted(_AUTO_SOURCES | _DERIVED_SOURCES | _MECHANICAL_SOURCES)
)
NON_DELIBERATE_SOURCE_PREFIXES: tuple[str, ...] = tuple(
    sorted(_DERIVED_SOURCE_PREFIXES + _MECHANICAL_SOURCE_PREFIXES)
)


def classify_write_class(memory: Mapping[str, Any] | str | None) -> str:
    """Resolve a memory (or a bare source string) to its write class.

    Precondition: ``memory`` is a mapping carrying at least a ``source``
        key (memory row shape from ``_normalize_memory_row`` / any
        ``remember()`` payload), a bare source string, or ``None``.
    Postcondition: return value is one of ``ALL_WRITE_CLASSES``. Unknown
        or empty source resolves to ``DELIBERATE`` — the safe default:
        an unclassified write is never assumed to be flood/noise, so it
        is never subject to fold-style regulation (matches the doctrine
        this module exists to enforce — see module docstring).

    7.4 forward-compatibility: if ``memory`` carries an explicit
    ``write_class`` value in ``ALL_WRITE_CLASSES``, it wins outright —
    this is the future explicit-column fast path, active today for any
    caller that already sets it (defensive; the column does not exist
    in the schema yet).
    """
    if memory is None:
        source = ""
    elif isinstance(memory, str):
        source = memory
    else:
        explicit = memory.get("write_class")
        if explicit in ALL_WRITE_CLASSES:
            return str(explicit)
        source = memory.get("source") or ""

    s = str(source).strip()
    if s in _AUTO_SOURCES:
        return AUTO
    if s in _DERIVED_SOURCES or s.startswith(_DERIVED_SOURCE_PREFIXES):
        return DERIVED
    if s in _MECHANICAL_SOURCES or s.startswith(_MECHANICAL_SOURCE_PREFIXES):
        return MECHANICAL
    return DELIBERATE
