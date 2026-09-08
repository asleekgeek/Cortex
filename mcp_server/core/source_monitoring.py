"""Source / reality monitoring (C1) — attribute a memory's epistemic origin.

source: ADR-0260"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ── Source attributions ─────────────────────────────────────────────────────
PERCEIVED = "perceived"  # source: ADR-0260
TOLD = "told"  # user-stated / instruction
INFERRED = "inferred"  # self-generated reasoning, no external grounding
UNKNOWN = "unknown"  # no discriminating signal either way

# source: ADR-0260


EVIDENCE_TAG = {
    PERCEIVED: "observed",
    TOLD: "stated",
    INFERRED: "inferred",
    UNKNOWN: "inferred",  # source: ADR-0260
}

# ── Feature patterns ────────────────────────────────────────────────────────
# Perceptual grounding — verifiable external references (the traces an external
# source leaves; mirrors claim_extractor._extract_evidence kinds).
_URL_RE = re.compile(r"https?://\S+")
_DOI_RE = re.compile(r"\b10\.\d{4,9}/\S+\b", re.IGNORECASE)
_FILE_RE = re.compile(
    r"\b[\w./-]+\.(?:py|js|ts|md|json|yaml|yml|toml|tex|sql|txt|rs|go|java|c|cpp|h)\b"
)
_SHA_RE = re.compile(r"\b[0-9a-f]{7,40}\b")
_TOOL_RE = re.compile(
    r"\b(?:tool[_\s]?output|stdout|stderr|returned|the output (?:was|shows)|"
    r"grep|read_file|ran|executed|command output)\b",
    re.IGNORECASE,
)

# "Told" markers — explicit attribution to the user / a stated instruction.
_TOLD_RE = re.compile(
    r"\b(?:you (?:said|told|asked|want|mentioned|requested|specified)|"
    r"the user (?:said|wants|asked|requested|specified|prefers)|"
    r"per your|as requested|as you|according to you|you'd like|you prefer)\b",
    re.IGNORECASE,
)

# source: ADR-0260

_INFER_RE = re.compile(
    r"\b(?:i think|i believe|i (?:would )?(?:guess|assume|suspect|expect)|"
    r"probably|presumably|likely|seems? (?:to|like)|appears? to|"
    r"this (?:suggests|implies|means)|it (?:follows|seems)|"
    r"my (?:guess|hypothesis|assumption)|(?:i )?infer|perhaps|maybe|"
    r"could be|might be|so it should|therefore)\b",
    re.IGNORECASE,
)


@dataclass
class SourceJudgement:
    """A source-monitoring attribution for one memory.

    ``attribution``      — PERCEIVED | TOLD | INFERRED | UNKNOWN.
    ``confidence``       — [0,1] margin of the winning family over the runner-up.
    ``evidence_tag``     — store-vocabulary tag (observed/stated/inferred).
    ``perceptual_score`` — count of external-grounding features.
    ``told_score``       — count of user-attribution features.
    ``inferred_score``   — count of cognitive-operation markers.
    ``grounding_refs``   — the concrete external references found (for audit).
    """

    attribution: str
    confidence: float
    evidence_tag: str
    perceptual_score: int
    told_score: int
    inferred_score: int
    grounding_refs: list[str] = field(default_factory=list)


def source_judgement_as_dict(judgement: "SourceJudgement") -> dict:
    """Serialize source judgement as a dictionary.

    source: ADR-0260
    """
    return {
        "attribution": judgement.attribution,
        "confidence": round(judgement.confidence, 4),
        "evidence_tag": judgement.evidence_tag,
        "perceptual_score": judgement.perceptual_score,
        "told_score": judgement.told_score,
        "inferred_score": judgement.inferred_score,
        "grounding_refs": judgement.grounding_refs[:10],
    }


# source: ADR-0260

# source: ADR-0260
_GIT_SHORT_SHA_LEN = 7
_GIT_FULL_SHA_LEN = 40


def extract_grounding(content: str) -> list[str]:
    """Extract URLs, DOIs, file paths, and commit SHAs from content.

    source: ADR-0260
    """
    refs: list[str] = []
    text = content or ""
    for rx in (_URL_RE, _DOI_RE, _FILE_RE):
        refs.extend(m.group(0) for m in rx.finditer(text))
    # SHAs are noisy (any hex run) — only count them as grounding when they look
    # like commit hashes standing alone, not embedded in longer tokens.
    for m in _SHA_RE.finditer(text):
        tok = m.group(0)
        if _GIT_SHORT_SHA_LEN <= len(tok) <= _GIT_FULL_SHA_LEN and (not tok.isdigit()):
            refs.append(tok)
    # de-dup preserving order
    seen: set[str] = set()
    out: list[str] = []
    for r in refs:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


# source: ADR-0260
def classify_source(
    content: str, *, source_field: str | None = None
) -> SourceJudgement:
    """Attribute a memory's epistemic origin from its text (+ optional ingestion
    ``source`` field).

    source: ADR-0260

        A ``source_field`` that is itself a strong external-pathway signal (e.g.
        ``post_tool_capture``, ``ingest_codebase``, ``import``) counts as one unit of
        perceptual grounding — those pathways are, by construction, externally
        sourced.
    """
    text = content or ""
    grounding = extract_grounding(text)
    tool_hit = 1 if _TOOL_RE.search(text) else 0
    told_score = len(_TOLD_RE.findall(text))
    inferred_score = len(_INFER_RE.findall(text))

    perceptual_score = len(grounding) + tool_hit
    if source_field and _is_external_pathway(source_field):
        perceptual_score += 1

    scores = {
        PERCEIVED: perceptual_score,
        TOLD: told_score,
        INFERRED: inferred_score,
    }
    winner = max(scores, key=lambda k: scores[k])
    top = scores[winner]

    if top == 0:
        # No discriminating feature in either direction.
        return SourceJudgement(
            attribution=UNKNOWN,
            confidence=0.0,
            evidence_tag=EVIDENCE_TAG[UNKNOWN],
            perceptual_score=perceptual_score,
            told_score=told_score,
            inferred_score=inferred_score,
            grounding_refs=grounding,
        )

    runner_up = max(v for k, v in scores.items() if k != winner)
    # Confidence = normalized margin of the winner over the runner-up.
    confidence = (top - runner_up) / (top + runner_up) if (top + runner_up) else 0.0

    return SourceJudgement(
        attribution=winner,
        confidence=confidence,
        evidence_tag=EVIDENCE_TAG[winner],
        perceptual_score=perceptual_score,
        told_score=told_score,
        inferred_score=inferred_score,
        grounding_refs=grounding,
    )


# ── The confabulation gate ──────────────────────────────────────────────────
def violates_source_claim(
    content: str,
    claimed_source_tag: str,
    *,
    source_field: str | None = None,
) -> bool:
    """True iff a memory ASSERTS an observed/perceived origin but shows no perceptual
    grounding — the reality-monitoring failure that produces confabulation.

    source: ADR-0260

        ``claimed_source_tag`` is the evidence tag the memory is being written /
        promoted with (observed/perceived/stated/inferred). The gate fires only for
        an *observed* claim that the content cannot support; it never blocks an
        inferred or stated claim (those make no external-grounding promise).
    """
    claim = (claimed_source_tag or "").strip().lower()
    if claim not in ("observed", "perceived"):
        return False  # only an observed-source claim can be a reality-monitoring error
    judgement = classify_source(content, source_field=source_field)
    # Violation: claims observed, but the evidence points to inferred and there
    # is no perceptual grounding at all.
    return judgement.attribution == INFERRED and judgement.perceptual_score == 0


# source: ADR-0260


def promotion_confabulation_risk(cluster_memories: list[dict]) -> bool:
    """Return whether promotion has inferred origin and zero perceptual grounding.

    source: ADR-0260

    This is a per-cluster *flag*, not a drop: the caller annotates the risky
    promotion (see consolidation_engine._process_patterns) and MAY still create
    the semantic memory. Non-fatal by construction — reality monitoring surfaces
    the risk, it does not silently discard a candidate abstraction.
    """
    if not cluster_memories:
        return False
    combined = " ".join(str(m.get("content", "") or "") for m in cluster_memories)
    return violates_source_claim(combined, "observed")


# ── Read-side surfacing: per-hit recall confabulation risk ──────────────────
def recall_confabulation_risk(
    content: str,
    source_attribution: str | None,
) -> bool:
    """True iff a recalled memory's own stored attribution claims an
    externally-grounded origin (perceived) that its content cannot support.

    source: ADR-0260

    A memory stored as inferred/told/unknown makes no external-grounding promise
    and is never flagged. Purely informational: it changes no ordering and drops
    no result.
    """
    attribution = (source_attribution or "").strip().lower()
    # Only a perceived-origin claim can be a reality-monitoring error; the
    # store's PERCEIVED maps to the "observed" claim vocabulary of the gate.
    if attribution != PERCEIVED:
        return False
    return violates_source_claim(content or "", "observed")


# ── Helpers ─────────────────────────────────────────────────────────────────
# Ingestion pathways that are externally sourced by construction.
_EXTERNAL_PATHWAYS = frozenset(
    {
        "post_tool_capture",
        "ingest_codebase",
        "ingest_prd",
        "ingest_findings",
        "import",
        "seed_project",
    }
)


def _is_external_pathway(source_field: str) -> bool:
    return (source_field or "").strip().lower() in _EXTERNAL_PATHWAYS
