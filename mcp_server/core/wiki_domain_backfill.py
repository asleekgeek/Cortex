"""Derive the true project domain for wiki pages stuck in a catch-all
bucket (``uncategorized``, ``_general``, ``global``, or any domain not
present in the repo registry).

``wiki.pages.domain`` is set at authoring time from whatever hint was
available then; for a sizeable slice of pages that hint was wrong or
absent, so the page landed in a catch-all rather than the project it
actually documents. This module re-derives the domain from evidence the
page already carries: the ``source_path`` rows in ``wiki.page_sources``
(``ADR-0051``), each of which names a file the page documents. Every
one of those source paths lives under exactly one project's checked-out
filesystem root (or none, if the root isn't registered) — the project
whose root contains the most of the page's source paths is the page's
true domain.

Pure logic, no I/O — filesystem containment checks are injected via
``domains_containing`` so this module stays unit-testable without
touching a real tree, and so it can live in core/ per the Dependency
Rule (core imports shared/ + stdlib only; no ``os``/``pathlib`` here).

Zetetic anti-fabrication discipline (CLAUDE.md, coding-standards.md
§8): a majority vote is only trustworthy when it is unambiguous. A tie
between the top two candidate domains carries no signal for which one
is right, so it is refused rather than broken arbitrarily.
"""

from __future__ import annotations

from collections import Counter
from typing import Callable

DomainsContainingFn = Callable[[str], set[str]]


def derive_page_domain(
    source_paths: list[str], domains_containing: DomainsContainingFn
) -> str | None:
    """Derive one page's true domain by majority vote over source paths.

    Pre-condition:  ``source_paths`` are the page's ``wiki.page_sources``
                    ``source_path`` values (raw, not yet normalized);
                    ``domains_containing(source_path)`` returns the set
                    of registered project domains whose filesystem root
                    contains a real file at that path (usually zero or
                    one domain, occasionally more when repo roots
                    overlap).
    Post-condition: returns the domain with strictly the most votes, or
                    ``None`` when no source path resolves to any domain,
                    or when the top two domains tie on vote count — a
                    tie carries no ranking signal, so guessing between
                    them would be fabrication, not derivation.
    """
    votes: Counter[str] = Counter()
    for source_path in source_paths:
        # A basename with no directory separator is too ambiguous to
        # attribute to one project's filesystem root — many projects
        # can contain a file with the same bare name.
        if not source_path or "/" not in source_path:
            continue
        for domain in domains_containing(source_path):
            votes[domain] += 1

    if not votes:
        return None

    top = votes.most_common(2)
    if len(top) > 1 and top[0][1] == top[1][1]:
        return None
    return top[0][0]


__all__ = ["derive_page_domain"]
