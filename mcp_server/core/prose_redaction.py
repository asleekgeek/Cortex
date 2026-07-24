"""Prose redaction — native inventory of AI-writing tells for generated prose.

Cortex manufactures reader-facing prose (curated wiki pages, narratives,
briefings). This module owns the pattern inventory used to (a) instruct the
authoring LLM at prompt time and (b) measure authored pages at write time.
Findings are advisory: the write path never blocks on them (generated prose
only gets measured; user-authored content is out of scope — issue #166).

Distinct from secret/PII redaction (``core/redaction*``): this is prose
style, not data protection.

Sources (zetetic standard — inventory informed by, implementation ours):
  - Wikipedia, "Signs of AI writing" (WikiProject AI Cleanup) — the
    maintained public catalog of the patterns detected here.
  - Method prior art: blader/humanizer v2.9.1, petergyang/no-ai-slop
    (both MIT) — pattern-inventory editing and quoted-evidence detection.
  - House rules (ai-architect.tools redaction practice, 2026): zero em
    dashes in published copy; unsourced attribution is a violation of the
    project's own evidence discipline (CLAUDE.md zetetic standard).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ── Inventory (mechanically detectable subset) ─────────────────────────
# Judgment-level tells (importance puffery in context, colon reveals,
# synonym cycling) are handled at prompt time via REDACTION_CONVENTIONS;
# regexes below only carry patterns with near-zero false-positive rates
# on technical prose.

# source: house rule (ai-architect.tools). Em dash as rhythm crutch is the
# single strongest tell; policy for generated copy is zero.
_EM_DASH = re.compile("—")

# source: Wikipedia "Signs of AI writing" § Overused vocabulary.
_BANNED_WORDS = re.compile(
    r"\b(delve|foster(?:s|ing)?|leverag(?:e|es|ing)|utiliz(?:e|es|ing)"
    r"|facilitat(?:e|es|ing)|empower(?:s|ing)?|streamlin(?:e|es|ing)"
    r"|cutting-edge|paradigm shift|game.chang(?:er|ing)|tapestry"
    r"|multifaceted|paramount|transformative|embark(?:s|ing)?"
    r"|supercharg(?:e|es|ing)|ever-evolving)\b",
    re.IGNORECASE,
)

# source: Wikipedia "Signs of AI writing" § Weasel wording / vague
# attribution; escalated to a violation by the project's zetetic standard
# (name the source or cut the claim).
_WEASEL = re.compile(
    r"(studies show|experts (?:agree|argue|believe)|industry reports"
    r"|widely regarded|it'?s worth noting|it'?s important to note"
    r"|in today'?s world|at the end of the day|let'?s dive in)",
    re.IGNORECASE,
)

# source: Wikipedia "Signs of AI writing" § Superficial analyses — a
# trailing present-participle clause tacked onto a sentence to fake depth.
# Detected only in the narrow ", <-ing verb of the known set>" form to
# keep false positives near zero on technical prose.
_ING_TACKON = re.compile(
    r",\s+(highlighting|underscoring|showcasing|emphasizing|reflecting"
    r"|symbolizing|demonstrating its|cementing|solidifying)\b",
    re.IGNORECASE,
)

_FENCE = re.compile(r"^\s*(```|~~~)")

CATEGORY_EM_DASH = "em_dash"
CATEGORY_BANNED_WORD = "banned_word"
CATEGORY_WEASEL = "weasel_attribution"
CATEGORY_ING_TACKON = "ing_tackon"

_CHECKS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (CATEGORY_EM_DASH, _EM_DASH),
    (CATEGORY_BANNED_WORD, _BANNED_WORDS),
    (CATEGORY_WEASEL, _WEASEL),
    (CATEGORY_ING_TACKON, _ING_TACKON),
)

_EXCERPT_MAX = 80  # source: keeps a finding to one terminal line; excerpt is a locator, not the evidence itself


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


# Injected into every wiki-authoring prompt (auto_curator prompts) so the
# tells are avoided at generation time; scan_prose measures what slipped
# through at write time.
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
  * No importance puffery ("pivotal", "testament to", "vital role"): state \
the fact and let the reader judge.
  * No summary-recap ending and no aphorism kicker: end on the last \
concrete point, limitation, or next action."""
