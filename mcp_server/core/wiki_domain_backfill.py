"""Derive the true project domain for wiki pages stuck in a catch-all
bucket (``uncategorized``, ``_general``, ``global``, or any domain not
present in the repo registry).

source: ADR-0300"""

from __future__ import annotations

from collections import Counter
from typing import Callable

DomainsContainingFn = Callable[[str], set[str]]


def derive_page_domain(
    source_paths: list[str], domains_containing: DomainsContainingFn
) -> str | None:
    """Derive one page's true domain by majority vote over source paths.

    source: ADR-0300"""
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
