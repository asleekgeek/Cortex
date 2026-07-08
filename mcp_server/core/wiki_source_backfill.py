"""Derive the primary documented source file for wiki pages that lack one
(ADR-0051 STEP 3).

``wiki_reindex`` / ``migrate_wiki`` already backfill ``documents_primary``
for pages whose frontmatter *has* a ``documents``/``source_file_path``/
``file`` field (``mcp_server.shared.wiki_source_paths.extract_document_paths``).
This module closes the remaining gap: pages with no such field.

Pure logic, no I/O — filesystem existence checks are injected via
``exists_fn`` so this module stays unit-testable without touching a real
tree, and so it can live in core/ per the Dependency Rule (core imports
shared/ + stdlib only; no ``os``/``pathlib`` here).

Derivation is a strict priority chain; each step either produces exactly
one confident candidate or falls through — the zetetic anti-fabrication
standard (CLAUDE.md, coding-standards.md §8) forbids guessing a "most
likely" primary when the evidence is ambiguous:

  1. **claim_evidence** — file paths cited as evidence on the page's
     source memory's claims (``pg_store_wiki_thermo.get_claim_file_refs_for_pages``).
     Accepted only when exactly one distinct normalized path is present;
     several candidates with no way to rank them is refused, not guessed.
  2. **codebase_grounding** — the wiki page's own ``rel_path`` slug,
     reversed into a plausible source path (mirrors
     ``scripts/wiki_rebucket_file_docs.py::_derive_target_path``'s
     ``path.replace("/", "-")`` forward transform). Accepted only if
     ``exists_fn`` confirms the reversed guess names a real file — the
     guess is never trusted on its own.
  3. **body** — a single source-file-shaped path cited in the page's
     lead + sections (reusing ``wiki_drift._extract_cited_paths``, not
     duplicating its regex/filter logic), accepted only if it resolves
     via ``exists_fn`` and no other groundable candidate ties with it.

Returns ``None`` when no step produces an unambiguous, real-file-backed
candidate — the caller (``wiki_maintenance``) then leaves the page
unlinked for the next ``wiki_drift`` REASON_MISSING_LINK pass to surface
as a re-authoring job.

Pre-condition:  ``page`` carries at least ``rel_path`` and ``domain``
                (str); ``lead``/``sections`` are optional and default to
                empty; ``claim_files`` entries are raw (not yet
                normalized) path strings; ``exists_fn`` answers whether a
                normalized, source-root-relative path names a real file.
Post-condition: the returned path (if any) is canonical per
                ``normalize_source_path`` and ``exists_fn`` returns True
                for it whenever the derivation step requires grounding
                (steps 2 and 3; step 1 is not filesystem-checked here —
                claim evidence is already a memory-derived fact, grounded
                at write time by the claim extractor).
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

    Several candidates carry no ranking signal here (no per-ref weight
    is passed through ``get_claim_file_refs_for_pages``), so more than
    one distinct path is a refusal, not a guess.
    """
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

    ``wiki_rebucket_file_docs._derive_target_path`` forward-transforms a
    source path into a slug via ``path.replace("/", "-")`` then
    ``slugify``. This reverses that specific transform (dashes back to
    slashes) on the page's filename stem. The guess is lossy (a source
    path containing a literal dash is indistinguishable from a directory
    separator) so it is NEVER trusted alone — only returned when
    ``exists_fn`` independently confirms a real file at that path.
    """
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

    Reuses ``wiki_drift._extract_cited_paths`` (regex + wiki-internal /
    technology-name filtering) rather than duplicating it. Several
    groundable citations carry no signal for which is "primary" — a tie
    is a refusal, matching ``_from_claim_evidence``'s discipline.
    """
    lead = str(page.get("lead") or "")
    sections = page.get("sections")
    section_text = "\n".join(str(v) for v in sections.values()) if isinstance(sections, dict) else ""
    body = f"{lead}\n{section_text}"

    grounded: dict[str, None] = {}
    for cited in _extract_cited_paths(body):
        canonical = normalize_source_path(cited)
        if canonical and exists_fn(canonical):
            grounded.setdefault(canonical, None)
    if len(grounded) == 1:
        return next(iter(grounded))
    return None
