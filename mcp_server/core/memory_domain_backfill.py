"""Derive the true domain for memories stuck with an empty ``domain``
column (I6-D3, ADR-0051-family batch-completion campaign).

``memories.domain`` is set once, at ``remember`` time, from whatever
``directory``/``domain`` hint the caller supplied
(``handlers/remember.py::_resolve_domain``). For 1 355 rows that
derivation failed or was never attempted (root cause fixed for future
writes by issue #95's ``normalize_project_id`` casing fix) — the stock
of already-written rows still carries ``domain = ''``.

This module re-derives the domain from evidence the memory row already
carries, in a strict priority order, and refuses to guess when no
evidence resolves:

  1. ``directory_context`` (the raw cwd stored by ``post_tool_capture``
     at write time, ``pg_schema.py:29``) — resolved via the injected
     ``resolve_directory`` callable (production: ``resolve_cwd``, the
     same git-root-based function ``remember``'s write path already
     uses, ``remember.py:246``).
  2. a ``project:<slug>`` tag (written by ``backfill_memories``,
     ``backfill_memories.py:161-164``) — resolved via the injected
     ``resolve_project_tag`` callable (production: ``slug_to_domain``,
     the same function ``backfill_memories`` already uses,
     ``backfill_helpers.py:157-166``).
  3. neither resolves → orphan. No neighbor/embedding/similarity
     inference (Q3 arbitrage: no retroactive fabrication of
     provenance) — the row stays domain-less and is tagged
     ``domain-orphan`` so the state is explicit and requeryable.

Pure logic, no I/O — filesystem/git walks and registry lookups are
injected via ``resolve_directory``/``resolve_project_tag`` so this
module stays unit-testable without touching a real tree or DB, and so
it can live in core/ per the Dependency Rule (core imports shared/ +
stdlib only).
"""

from __future__ import annotations

from typing import Callable, NamedTuple

ResolveDirectoryFn = Callable[[str], str]
ResolveProjectTagFn = Callable[[str], str]

_PROJECT_TAG_PREFIX = "project:"


class DomainDerivation(NamedTuple):
    """Result of re-deriving one memory's domain.

    ``domain`` is ``""`` when no evidence resolved (orphan case).
    ``evidence`` names which source won: ``"directory_context"``,
    ``"project_tag"``, or ``""`` for the orphan case — this is the
    value the campaign journal records per row.
    """

    domain: str
    evidence: str


def _first_project_tag(tags: list[str]) -> str | None:
    """Return the slug of the first ``project:<slug>`` tag, or ``None``.

    First-match, not majority-vote: a memory carries at most one such
    tag in practice (written once by ``backfill_memories``), and
    picking the first occurrence keeps the derivation deterministic
    without adding an unneeded tie-break rule.
    """
    for tag in tags:
        if isinstance(tag, str) and tag.startswith(_PROJECT_TAG_PREFIX):
            slug = tag[len(_PROJECT_TAG_PREFIX) :]
            if slug:
                return slug
    return None


def derive_memory_domain(
    directory_context: str,
    tags: list[str],
    resolve_directory: ResolveDirectoryFn,
    resolve_project_tag: ResolveProjectTagFn,
) -> DomainDerivation:
    """Re-derive one memory's domain from its own stored evidence.

    Pre-condition:  ``directory_context`` and ``tags`` are the memory
                    row's own columns (``tags`` already JSON-decoded to
                    a list of strings); ``resolve_directory`` maps a
                    raw cwd to a canonical domain or ``""`` when it
                    cannot (mirrors ``resolve_cwd``'s contract:
                    deterministic, no fabrication); ``resolve_project_tag``
                    maps a project slug to a canonical domain or ``""``
                    (mirrors ``slug_to_domain``).
    Post-condition: returns ``DomainDerivation(domain, evidence)``.
                    ``domain`` is non-empty iff a source resolved;
                    ``evidence`` names the winning source
                    (``"directory_context"`` beats ``"project_tag"``
                    when both would resolve — directory evidence is
                    written unconditionally by every capture, tag
                    evidence only by backfill imports, so directory
                    evidence is checked first). Neither source
                    resolving returns ``DomainDerivation("", "")`` —
                    the orphan case; callers must not invent a domain
                    for it.
    """
    if directory_context:
        domain = resolve_directory(directory_context)
        if domain:
            return DomainDerivation(domain, "directory_context")

    slug = _first_project_tag(tags)
    if slug:
        domain = resolve_project_tag(slug)
        if domain:
            return DomainDerivation(domain, "project_tag")

    return DomainDerivation("", "")


__all__ = ["DomainDerivation", "derive_memory_domain"]
