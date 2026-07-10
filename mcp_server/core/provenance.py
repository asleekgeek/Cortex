"""Provenance grading — pure business logic (I6-D6).

Grades a memory's content by the CONTROLLABILITY of the external references
it makes: file paths, git commit SHAs, URLs, and content-addressed artifact
digests (``infrastructure/artifact_store.py``, ``sha256[:16]``). Citation
references (DOI / arXiv id) are recognized but never auto-checked — no
source exists to verify them against (coding-standards.md §8: "no source,
no implementation" applies equally to verification code).

Grade vocabulary (persisted to ``memories.source_attribution`` by
``handlers/validate_memory.py``, the sole writer of this grade going
forward — I6-D6):

  VERIFIED     — every controllable reference in the memory currently
                 checks out (all file paths exist, all commit SHAs resolve
                 in their memory's local repo, all artifact digests match).
  VERIFIABLE   — the memory carries references, but at least one could not
                 be conclusively checked here and now (repo unavailable
                 locally, URL not sampled this pass, a citation with no
                 automated check), and no CHECKED reference came back dead.
  UNVERIFIABLE — no reference at all (testimony only), OR at least one
                 checked reference is dead (missing file, unreachable URL,
                 missing/mismatched artifact digest).

Per-type grade ceiling (from the I6-D6 design table — not every reference
type can reach every grade):
  file path        → VERIFIED (exists) | UNVERIFIABLE (missing)
  git commit SHA    → VERIFIED (found in a locally-available repo) |
                       VERIFIABLE (repo unavailable locally, or the check
                       was inconclusive — a stale/shallow local clone is
                       indistinguishable from a genuinely dead SHA, so we
                       never penalize the memory to UNVERIFIABLE from a
                       commit ref alone)
  URL               → VERIFIABLE (2xx/3xx, or not sampled this pass) |
                       UNVERIFIABLE (4xx/5xx/timeout) — a URL can never
                       raise a memory to VERIFIED; the web fluctuates and
                       a dead link does not invalidate a historical fact
                       (kept OUT of the staleness score for the same
                       reason — see core/staleness.py).
  artifact digest   → VERIFIED (recomputed sha256[:16] matches) |
                       UNVERIFIABLE (artifact missing or hash mismatch)
  citation (DOI/arXiv) → VERIFIABLE at best — never auto-verified, never
                       marked dead.

The memory's overall grade is the WORST outcome among its references
(min over the ranking UNVERIFIABLE < VERIFIABLE < VERIFIED). A memory with
zero extractable references is UNVERIFIABLE (testimony only).

No I/O performed here. Callers (validate_memory) resolve existence /
reachability / repo availability and pass the outcomes in — the same
caller-resolves-I/O separation as core/staleness.py.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ── Grade vocabulary ────────────────────────────────────────────────────────
VERIFIED = "verified"
VERIFIABLE = "verifiable"
UNVERIFIABLE = "unverifiable"

GRADES = (VERIFIED, VERIFIABLE, UNVERIFIABLE)
_RANK = {UNVERIFIABLE: 0, VERIFIABLE: 1, VERIFIED: 2}  # worst → best

# ── Reference extraction ────────────────────────────────────────────────────

# Hex tokens that plausibly look like a git commit SHA (short or full).
# All-digit runs are excluded (those are more likely counters/timestamps).
_COMMIT_RE = re.compile(r"\b[0-9a-f]{7,40}\b")

_URL_RE = re.compile(r"https?://\S+")

# Content-addressed artifact pointer: <...>/artifacts/<yyyy-mm>/<16-hex>.md
# (infrastructure/artifact_store.py: ARTIFACTS_DIR / <yyyy-mm> / sha256[:16].md)
_ARTIFACT_RE = re.compile(
    r"([\w./\\-]*artifacts[/\\]\d{4}-\d{2}[/\\]([0-9a-f]{16})\.md)"
)

# Citation markers this tool recognizes but never auto-checks: DOI and arXiv ids.
_CITATION_RE = re.compile(
    r"\b(?:10\.\d{4,9}/\S+|arXiv:\d{4}\.\d{4,5})\b", re.IGNORECASE
)


def extract_commit_refs(content: str) -> list[str]:
    """Deduplicated candidate commit SHAs (hex, 7-40 chars, not all-digit)."""
    seen: set[str] = set()
    out: list[str] = []
    for m in _COMMIT_RE.finditer(content or ""):
        tok = m.group(0)
        if tok.isdigit() or tok in seen:
            continue
        seen.add(tok)
        out.append(tok)
    return out


def extract_url_refs(content: str) -> list[str]:
    """Deduplicated http(s) URLs, trailing punctuation stripped."""
    seen: set[str] = set()
    out: list[str] = []
    for m in _URL_RE.finditer(content or ""):
        url = m.group(0).rstrip(").,;:'\"")
        if url and url not in seen:
            seen.add(url)
            out.append(url)
    return out


def extract_artifact_refs(content: str) -> list[tuple[str, str]]:
    """Deduplicated (artifact_path, embedded_sha256_prefix) pairs."""
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for m in _ARTIFACT_RE.finditer(content or ""):
        path, digest = m.group(1), m.group(2)
        if path not in seen:
            seen.add(path)
            out.append((path, digest))
    return out


def has_citation_ref(content: str) -> bool:
    """True iff content carries a structured DOI/arXiv citation marker."""
    return bool(_CITATION_RE.search(content or ""))


# ── Grading ──────────────────────────────────────────────────────────────────


@dataclass
class ProvenanceReport:
    """Result of a provenance-grading pass for a single memory."""

    memory_id: int
    grade: str
    ref_counts: dict[str, int]
    dead_refs: list[str] = field(default_factory=list)
    uncheckable_refs: list[str] = field(default_factory=list)
    reason: str = "no_extractable_reference"


def _build_reason(grade: str, dead: list[str], uncheckable: list[str]) -> str:
    if grade == UNVERIFIABLE and dead:
        return f"dead_refs: {', '.join(dead[:3])}"
    if grade == UNVERIFIABLE:
        return "no_extractable_reference"
    if grade == VERIFIABLE and uncheckable:
        return f"uncheckable_refs: {', '.join(uncheckable[:3])}"
    return "all_refs_verified"


def grade_provenance(
    memory_id: int,
    *,
    file_refs: list[str],
    existing_paths: set[str],
    commit_refs: list[str],
    commit_verdicts: dict[str, bool],
    url_refs: list[str],
    url_verdicts: dict[str, bool | None],
    artifact_refs: list[tuple[str, str]],
    artifact_verdicts: dict[str, bool],
    has_citation: bool,
) -> ProvenanceReport:
    """Grade one memory from pre-resolved per-reference outcomes.

    precondition: every ref in file_refs/commit_refs/url_refs/(path for
    artifact_refs) has, at most, a corresponding entry in its verdicts dict
    (a missing entry is treated as the least-favorable outcome for that
    type, never crashes).
    postcondition: returns a ProvenanceReport whose grade is the worst
    outcome (UNVERIFIABLE < VERIFIABLE < VERIFIED) among all reference
    outcomes, or UNVERIFIABLE when there is no extractable reference at all.
    """
    outcomes: list[str] = []
    dead: list[str] = []
    uncheckable: list[str] = []

    for p in file_refs:
        if p in existing_paths:
            outcomes.append(VERIFIED)
        else:
            outcomes.append(UNVERIFIABLE)
            dead.append(p)

    for sha in commit_refs:
        if commit_verdicts.get(sha, False):
            outcomes.append(VERIFIED)
        else:
            outcomes.append(VERIFIABLE)
            uncheckable.append(sha)

    for url in url_refs:
        verdict = url_verdicts.get(url)
        if verdict is False:
            outcomes.append(UNVERIFIABLE)
            dead.append(url)
        else:
            outcomes.append(VERIFIABLE)
            if verdict is None:
                uncheckable.append(url)

    for path, _digest in artifact_refs:
        if artifact_verdicts.get(path, False):
            outcomes.append(VERIFIED)
        else:
            outcomes.append(UNVERIFIABLE)
            dead.append(path)

    if has_citation:
        outcomes.append(VERIFIABLE)

    if not outcomes:
        return ProvenanceReport(
            memory_id=memory_id,
            grade=UNVERIFIABLE,
            ref_counts=_ref_counts(
                file_refs, commit_refs, url_refs, artifact_refs, has_citation
            ),
            dead_refs=[],
            uncheckable_refs=[],
            reason="no_extractable_reference",
        )

    grade = min(outcomes, key=lambda g: _RANK[g])
    return ProvenanceReport(
        memory_id=memory_id,
        grade=grade,
        ref_counts=_ref_counts(
            file_refs, commit_refs, url_refs, artifact_refs, has_citation
        ),
        dead_refs=dead,
        uncheckable_refs=uncheckable,
        reason=_build_reason(grade, dead, uncheckable),
    )


def _ref_counts(
    file_refs: list[str],
    commit_refs: list[str],
    url_refs: list[str],
    artifact_refs: list[tuple[str, str]],
    has_citation: bool,
) -> dict[str, int]:
    return {
        "file": len(file_refs),
        "commit": len(commit_refs),
        "url": len(url_refs),
        "artifact": len(artifact_refs),
        "citation": 1 if has_citation else 0,
    }
