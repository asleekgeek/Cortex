"""Derive the true domain for memories stuck with an empty ``domain`` column.

source: ADR-0199
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

    source: ADR-0199"""
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
