"""Prose redaction — native inventory of AI-writing tells for generated prose.

source: ADR-0229"""

from __future__ import annotations

import re
from dataclasses import dataclass

CATEGORY_EM_DASH = "em_dash"
CATEGORY_BANNED_WORD = "banned_word"
CATEGORY_WEASEL = "weasel_attribution"
CATEGORY_FILLER = "filler_phrase"
CATEGORY_ING_TACKON = "ing_tackon"
CATEGORY_BINARY_CONTRAST = "binary_contrast"
CATEGORY_NEGATIVE_LISTING = "negative_listing"
CATEGORY_THROAT_CLEARING = "throat_clearing"
CATEGORY_FAUX_INSIGHT = "faux_insight"
CATEGORY_PUFFERY = "importance_puffery"
CATEGORY_PROMOTIONAL = "promotional"
CATEGORY_FAKE_VERB = "fake_strong_verb"
CATEGORY_AI_ARTIFACT = "ai_conversation_artifact"
CATEGORY_SIGNPOST = "signposting"
CATEGORY_RHETORICAL = "rhetorical_setup"
CATEGORY_DRAMATIC_FRAGMENT = "dramatic_fragment"

# (category, pattern) — one compiled regex per class, source-annotated.
_CHECKS: tuple[tuple[str, re.Pattern[str]], ...] = (
    # source: ADR-0229
    (CATEGORY_EM_DASH, re.compile("—")),
    # source: ADR-0229
    (
        CATEGORY_BANNED_WORD,
        re.compile(
            r"\b(delve|foster(?:s|ing)?|leverag(?:e|es|ing)|utiliz(?:e|es|ing)"
            r"|facilitat(?:e|es|ing)|empower(?:s|ing)?|streamlin(?:e|es|ing)"
            r"|cutting-edge|paradigm shift|game.chang(?:er|ing)|tapestry"
            r"|multifaceted|paramount|transformative|embark(?:s|ing)?"
            r"|supercharg(?:e|es|ing)|ever-evolving)\b",
            re.IGNORECASE,
        ),
    ),
    # source: ADR-0229
    (
        CATEGORY_WEASEL,
        re.compile(
            r"(studies show|experts (?:agree|argue|believe)|industry reports"
            r"|widely regarded|many argue)",
            re.IGNORECASE,
        ),
    ),
    # source: ADR-0229
    (
        CATEGORY_FILLER,
        re.compile(
            r"(it'?s worth noting|it'?s important to note|in today'?s world"
            r"|at the end of the day|let'?s dive in|when it comes to"
            r"|at its core|in the age of|in the world of|going forward"
            r"|needless to say|the reality is)",
            re.IGNORECASE,
        ),
    ),
    # source: ADR-0229
    (
        CATEGORY_ING_TACKON,
        re.compile(
            r",\s+(highlighting|underscoring|showcasing|emphasizing"
            r"|reflecting|symbolizing|demonstrating its|cementing"
            r"|solidifying)\b",
            re.IGNORECASE,
        ),
    ),
    # source: ADR-0229
    (
        CATEGORY_BINARY_CONTRAST,
        re.compile(
            r"((?:It|This|That)(?:'s| is) not [^.]{2,60}\."
            r"\s*(?:It|This|That)(?:'s| is)\b"
            r"|\bnot just [^,.;]{2,40}, but\b"
            r"|\b(?:question|problem|point|issue) (?:is|was)n'?t "
            r"[^.]{2,40}[.,]\s*(?:it|It)(?:'s| is)\b)",
        ),
    ),
    # source: ADR-0229
    (
        CATEGORY_NEGATIVE_LISTING,
        re.compile(r"\bNot (?:a|an|the) [^.]{1,40}\.\s*Not (?:a|an|the)\b"),
    ),
    # source: ADR-0229
    (
        CATEGORY_THROAT_CLEARING,
        re.compile(
            r"(here'?s the thing|let me be clear|let'?s be honest"
            r"|to be clear,|the (?:uncomfortable |hard |simple )?truth is"
            r"|here'?s what I mean)",
            re.IGNORECASE,
        ),
    ),
    # source: ADR-0229
    (
        CATEGORY_FAUX_INSIGHT,
        re.compile(
            r"(what nobody tells you|what most people (?:miss|get wrong|skip)"
            r"|the part everyone misses|here'?s what nobody)",
            re.IGNORECASE,
        ),
    ),
    # source: ADR-0229
    (
        CATEGORY_PUFFERY,
        re.compile(
            r"(testament to|pivotal moment|(?:vital|crucial|key) role"
            r"|underscor(?:es|ing) (?:its|the) (?:significance|importance)"
            r"|marks a (?:pivotal|significant)|solidif(?:y|ies) its position"
            r"|indelible mark|evolving landscape|sets? the stage for)",
            re.IGNORECASE,
        ),
    ),
    # source: ADR-0229
    (
        CATEGORY_PROMOTIONAL,
        re.compile(
            r"\b(nestled|boasts? a|vibrant|breathtaking|stunning|must-visit"
            r"|renowned|rich (?:cultural )?heritage|in the heart of)\b",
            re.IGNORECASE,
        ),
    ),
    # source: ADR-0229
    (
        CATEGORY_FAKE_VERB,
        re.compile(
            r"\b(serves as (?:a|an|the)|stands as|functions as (?:a|an|the)"
            r"|acts as (?:a|an|the) (?:hub|beacon|cornerstone))\b",
            re.IGNORECASE,
        ),
    ),
    # source: ADR-0229
    (
        CATEGORY_AI_ARTIFACT,
        re.compile(
            r"(as an AI\b|knowledge cutoff|I hope this helps"
            r"|let me know if you|I'?d be happy to|great question"
            r"|certainly!)",
            re.IGNORECASE,
        ),
    ),
    # source: ADR-0229
    (
        CATEGORY_SIGNPOST,
        re.compile(
            r"(in this (?:article|section|page|document)|we will explore"
            r"|let'?s explore|in conclusion|in summary,)",
            re.IGNORECASE,
        ),
    ),
    # source: ADR-0229
    (
        CATEGORY_RHETORICAL,
        re.compile(
            r"(what if I told you|plot twist:|think about it:"
            r"|the (?:best|craziest|wildest) part[:?])",
            re.IGNORECASE,
        ),
    ),
    # source: ADR-0229
    (
        CATEGORY_DRAMATIC_FRAGMENT,
        re.compile(r"That'?s it\.\s*That'?s\b", re.IGNORECASE),
    ),
)

_FENCE = re.compile(r"^\s*(```|~~~)")

# source: ADR-0229
# source: ADR-0229
_EXCERPT_MAX = 80


@dataclass(frozen=True)
class ProseFinding:
    """One detected AI-writing tell in a piece of generated prose."""

    line: int
    category: str
    match: str
    excerpt: str


def scan_prose(text: str) -> list[ProseFinding]:
    """Scan generated prose for the mechanical inventory.

    Fenced code blocks are skipped (code is not copy). YAML frontmatter is
    scanned — titles and descriptions are reader-facing.
    """
    findings: list[ProseFinding] = []
    in_fence = False
    for lineno, line in enumerate(text.splitlines(), start=1):
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for category, pattern in _CHECKS:
            hit = pattern.search(line)
            if hit is None:
                continue
            findings.append(
                ProseFinding(
                    line=lineno,
                    category=category,
                    match=hit.group(0),
                    excerpt=line.strip()[:_EXCERPT_MAX],
                )
            )
    return findings


def summarize_findings(findings: list[ProseFinding], cap: int = 10) -> dict:
    """Advisory summary for tool responses (never blocks a write)."""
    return {
        "count": len(findings),
        "by_category": _count_by_category(findings),
        "first": [
            {
                "line": f.line,
                "category": f.category,
                "match": f.match,
                "excerpt": f.excerpt,
            }
            for f in findings[:cap]
        ],
    }


def _count_by_category(findings: list[ProseFinding]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.category] = counts.get(f.category, 0) + 1
    return counts


# source: ADR-0229


REDACTION_CONVENTIONS = """\
- Redaction pass (write like a person, not a press release):
  * No em dashes anywhere in the page. Use commas, periods, or parentheses.
  * No filler vocabulary: delve, leverage, utilize, facilitate, empower, \
streamline, cutting-edge, paradigm shift, game changer, tapestry, \
multifaceted, paramount, transformative, ever-evolving.
  * No unsourced attribution ("studies show", "experts agree", "widely \
regarded"): name the memory, benchmark, or paper, or cut the claim.
  * No trailing "-ing" analysis clauses ("..., highlighting the team's \
commitment"): state the concrete mechanism or consequence instead.
  * No importance puffery ("pivotal", "testament to", "vital role") and no \
promotional adjectives: state the fact and let the reader judge.
  * No binary contrasts ("It's not X. It's Y."), no negative listing \
("Not a X. Not a Y."), no rule-of-three rhythm, no colon reveals \
("The best part: ..."): state the point directly, vary sentence shapes.
  * No throat-clearing ("Here's the thing"), faux insight ("what nobody \
tells you"), signposting ("in this section"), or rhetorical setups \
("What if I told you"): the first sentence carries the point.
  * Repeat the clear word instead of cycling synonyms; prefer "is"/"has" \
over "serves as"/"stands as".
  * No summary-recap ending and no aphorism kicker: end on the last \
concrete point, limitation, or next action."""
