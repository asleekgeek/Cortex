"""Derive the primary documented source file for wiki pages that lack one.

source: ADR-0309
"""

from __future__ import annotations

from typing import Callable, Final

from mcp_server.core.wiki_drift import _extract_cited_paths
from mcp_server.shared.wiki_source_paths import normalize_source_path

SOURCE_CLAIM_EVIDENCE: Final[str] = "claim_evidence"
SOURCE_CODEBASE_GROUNDING: Final[str] = "codebase_grounding"
SOURCE_BODY: Final[str] = "body"

ExistsFn = Callable[[str], bool]


def derive_primary_source(
    page: dict[str, object],
    claim_files: list[str],
    exists_fn: ExistsFn,
) -> tuple[str, str] | None:
    """Derive the single best primary documented file for ``page``.

    Returns ``(canonical_source_path, source_tag)`` or ``None`` when no
    step yields an unambiguous, groundable candidate. See module
    docstring for the priority chain and its refusal conditions.
    """
    candidate = _from_claim_evidence(claim_files)
    if candidate is not None:
        return candidate, SOURCE_CLAIM_EVIDENCE

    rel_path = str(page.get("rel_path") or "")
    candidate = _from_codebase_grounding(rel_path, exists_fn)
    if candidate is not None:
        return candidate, SOURCE_CODEBASE_GROUNDING

    candidate = _from_body(page, exists_fn)
    if candidate is not None:
        return candidate, SOURCE_BODY

    return None


def _from_claim_evidence(claim_files: list[str]) -> str | None:
    """Exactly one distinct normalized claim-cited file -> use it.

    source: ADR-0309"""
    normalized: dict[str, None] = {}
    for raw in claim_files:
        canonical = normalize_source_path(raw)
        if canonical:
            normalized.setdefault(canonical, None)
    if len(normalized) == 1:
        return next(iter(normalized))
    return None


def _from_codebase_grounding(rel_path: str, exists_fn: ExistsFn) -> str | None:
    """Reverse the wiki page's own slug into a source-path guess.

    source: ADR-0309"""
    if not rel_path or not rel_path.endswith(".md"):
        return None
    stem = rel_path.rsplit("/", 1)[-1][: -len(".md")]
    if not stem:
        return None
    guess = stem.replace("-", "/")
    canonical = normalize_source_path(guess)
    if canonical and exists_fn(canonical):
        return canonical
    return None


def _from_body(page: dict[str, object], exists_fn: ExistsFn) -> str | None:
    """Exactly one groundable path cited in the page's lead + sections.

    source: ADR-0309"""
    lead = str(page.get("lead") or "")
    sections = page.get("sections")
    section_text = (
        "\n".join(str(v) for v in sections.values())
        if isinstance(sections, dict)
        else ""
    )
    body = f"{lead}\n{section_text}"

    grounded: dict[str, None] = {}
    for cited in _extract_cited_paths(body):
        canonical = normalize_source_path(cited)
        if canonical and exists_fn(canonical):
            grounded.setdefault(canonical, None)
    if len(grounded) == 1:
        return next(iter(grounded))
    return None
