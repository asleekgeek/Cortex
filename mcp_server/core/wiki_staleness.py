"""Phase 4 — Staleness brake for wiki pages.

A page becomes stale when the file references it cites no longer
exist on disk. Stale pages get is_stale=True and lose heat faster
(half-life multiplier).

Pure logic: this module is given a page's referenced file paths and
a per-path existence map (computed by the handler with filesystem
I/O), and returns the decision.

Staleness signal sources:
  - claim_events.evidence_refs where kind='file' (most reliable)
  - Inline file-pattern matches in lead/sections (best-effort)

ADR-0051 STEP 4 adds ``harvest_page_refs_typed`` / ``normalize_typed_refs``:
the staleness brake above only needs the *union* of referenced paths, but
persisting them as ``wiki.page_sources`` rows (link_kind='references')
needs per-path provenance (was this path cited by a claim, or only found
by best-effort regex in the body?) so downstream consumers can weigh the
two differently. ``harvest_page_refs`` is kept and now derives from the
typed variant rather than duplicating the merge logic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from mcp_server.shared.wiki_source_paths import normalize_source_path

_FILE_REF_RE = re.compile(
    r"\b([\w./-]+\.(?:py|js|ts|md|json|yaml|yml|sql|go|rs|rb|java|cpp|c|h|hpp|sh|toml))\b"
)

# A page is stale when this fraction of its file refs are missing.
STALE_THRESHOLD = 0.5
# A page must reference at least this many files for staleness to apply
# (avoid false positives from pages with one stray file mention).
MIN_FILE_REFS = 2


@dataclass(frozen=True)
class StalenessDecision:
    """Per-page staleness verdict."""

    page_id: int
    file_refs: list[str]
    missing_refs: list[str]
    is_stale_now: bool
    is_stale_was: bool
    transitioned: bool
    rationale: str


def extract_file_refs(text: str) -> list[str]:
    """Return distinct file paths mentioned in a body of text."""
    if not text:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for m in _FILE_REF_RE.finditer(text):
        ref = m.group(1)
        if ref not in seen:
            seen.add(ref)
            out.append(ref)
    return out


def evaluate_staleness(
    *,
    page_id: int,
    is_stale_was: bool,
    file_refs: list[str],
    existence: dict[str, bool],
) -> StalenessDecision:
    """Decide whether a page is stale.

    Inputs:
      page_id       — wiki.pages.id
      is_stale_was  — current value on the page row
      file_refs     — list of file paths mentioned by the page (claim
                      evidence + inline pattern matches; deduped)
      existence     — {path: True if exists, False if missing}

    A page is stale iff:
      - len(file_refs) >= MIN_FILE_REFS
      - missing / total >= STALE_THRESHOLD
    """
    if len(file_refs) < MIN_FILE_REFS:
        return StalenessDecision(
            page_id=page_id,
            file_refs=file_refs,
            missing_refs=[],
            is_stale_now=False,
            is_stale_was=is_stale_was,
            transitioned=is_stale_was,  # True if we're un-staling
            rationale=(f"too few file refs ({len(file_refs)} < {MIN_FILE_REFS})"),
        )

    missing = [ref for ref in file_refs if not existence.get(ref, False)]
    fraction = len(missing) / len(file_refs)
    is_stale_now = fraction >= STALE_THRESHOLD
    return StalenessDecision(
        page_id=page_id,
        file_refs=file_refs,
        missing_refs=missing,
        is_stale_now=is_stale_now,
        is_stale_was=is_stale_was,
        transitioned=is_stale_now != is_stale_was,
        rationale=(
            f"{len(missing)}/{len(file_refs)} refs missing "
            f"({fraction * 100:.0f}% — threshold {int(STALE_THRESHOLD * 100)}%)"
        ),
    )


def harvest_page_refs(page: dict, claim_evidence_files: list[str]) -> list[str]:
    """Collect all file refs a page should be checked against.

    Combines:
      - claim-derived file refs (high signal, from extractor)
      - inline file patterns in lead + section bodies (best effort)

    A thin adapter over ``harvest_page_refs_typed`` that drops the
    per-path provenance the staleness brake doesn't need (it only cares
    about the union of paths to existence-check).
    """
    return sorted(harvest_page_refs_typed(page, claim_evidence_files))


# Per-path provenance tags for harvest_page_refs_typed / normalize_typed_refs.
REF_SOURCE_CLAIM_EVIDENCE = "claim_evidence"
REF_SOURCE_BODY = "body"


def harvest_page_refs_typed(
    page: dict, claim_evidence_files: list[str]
) -> dict[str, str]:
    """Like ``harvest_page_refs`` but keeps, per path, which signal found it.

    Pre-condition:  ``claim_evidence_files`` are raw (not yet normalized)
                    path strings, as returned by
                    ``pg_store_wiki_thermo.get_claim_file_refs_for_pages``.
    Post-condition: every key of the returned dict is a raw (not yet
                    normalized — see ``normalize_typed_refs``) path
                    string; the value is ``REF_SOURCE_CLAIM_EVIDENCE`` if
                    that exact raw string was present in
                    ``claim_evidence_files``, else ``REF_SOURCE_BODY``.
                    When the same raw path is cited both ways, claim
                    evidence wins (it is the higher-signal source).
    """
    origins: dict[str, str] = {}

    def _collect_body(text: str) -> None:
        for ref in extract_file_refs(text):
            origins.setdefault(ref, REF_SOURCE_BODY)

    _collect_body(page.get("lead") or "")
    sections = page.get("sections") or {}
    if isinstance(sections, dict):
        for body in sections.values():
            _collect_body(str(body))
    elif isinstance(sections, list):
        for s in sections:
            body = s.get("body") if isinstance(s, dict) else getattr(s, "body", "")
            _collect_body(str(body))

    for ref in claim_evidence_files or []:
        origins[ref] = REF_SOURCE_CLAIM_EVIDENCE  # claim always wins a tie

    return origins


def normalize_typed_refs(typed_refs: dict[str, str]) -> dict[str, str]:
    """Canonicalize a ``harvest_page_refs_typed`` result for persistence.

    ``wiki.page_sources.source_path`` must share the same canonical form
    across every link_kind (``mcp_server.shared.wiki_source_paths
    .normalize_source_path`` — the convention ``documents`` links already
    use) so the reverse index doesn't split one real file into two rows.

    Two raw refs that normalize to the same canonical path collapse into
    one entry. ``claim_evidence`` wins the merge regardless of iteration
    order (mirrors ``harvest_page_refs_typed``'s own precedence): a path
    already recorded as claim-evidence is never demoted to body, and a
    later claim-evidence hit always promotes an existing body entry.
    """
    out: dict[str, str] = {}
    for raw, origin in typed_refs.items():
        canonical = normalize_source_path(raw)
        if canonical is None:
            continue
        if canonical not in out or origin == REF_SOURCE_CLAIM_EVIDENCE:
            out[canonical] = origin
    return out


__all__ = [
    "STALE_THRESHOLD",
    "MIN_FILE_REFS",
    "REF_SOURCE_CLAIM_EVIDENCE",
    "REF_SOURCE_BODY",
    "StalenessDecision",
    "extract_file_refs",
    "evaluate_staleness",
    "harvest_page_refs",
    "harvest_page_refs_typed",
    "normalize_typed_refs",
]
