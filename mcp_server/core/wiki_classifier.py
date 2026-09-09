"""Wiki content classifier — determines page kind or rejects noise.

source: ADR-0294"""

from __future__ import annotations

from typing import Callable

from mcp_server.core.wiki_classifier_gates import (
    fails_audit_tag_gate,
    fails_hard_negatives,
    positive_score,
)
from mcp_server.core.wiki_classifier_patterns import (
    ADR_PATTERNS,
    CONVENTION_PATTERNS,
    LESSON_PATTERNS,
    POSITIVE_SCORE_THRESHOLD,
    REJECT_PATTERNS,
    REJECT_PREFIXES,
    REJECT_TITLES,
    SPEC_TAGS,
)
from mcp_server.core.wiki_kind_detection import (
    detect_audiences,
    detect_modern_kind,
    detect_provenance,
    pick_lifecycle,
)
from mcp_server.core.wiki_title import derive_title, slugify as _slugify
from mcp_server.observability import silent_failure
from mcp_server.core.wiki_rule_engine import apply_rules
from mcp_server.shared.wiki_classification import Classification, Generator
from mcp_server.core.wiki_axis_registry import (
    AXIS_PROVENANCE,
    axis_registry_get,
    get_registry,
)

__all__ = [
    "classify_memory",
    "configure_user_rules_provider",
    "derive_title",
    "reset_user_rules",
]

# source: ADR-0294


# source: ADR-0294

# source: ADR-0294
_MIN_ADMISSIBLE_CHARS = 50

# source: ADR-0294

# source: ADR-0294
_MIN_SPEC_CHARS = 200

_USER_RULES_CACHE = None  # None = not loaded; [] = loaded but empty
_USER_RULES_PROVIDER: Callable[[], list] | None = None


def configure_user_rules_provider(provider: Callable[[], list]) -> None:
    """Composition-root injection point: register how to obtain the
    user-editable classifier rules (``wiki/_rules/*.md``, parsed into
    ``ClassifierRule`` objects). Call once at MCP server boot.
    """
    global _USER_RULES_PROVIDER
    _USER_RULES_PROVIDER = provider


def _load_user_rules():
    """Lazy-load + cache user rules. Never raises; returns []."""
    global _USER_RULES_CACHE
    if _USER_RULES_CACHE is not None:
        return _USER_RULES_CACHE
    try:
        _USER_RULES_CACHE = (
            list(_USER_RULES_PROVIDER()) if _USER_RULES_PROVIDER is not None else []
        )
    except Exception as exc:  # noqa: BLE001 — source: ADR-0294
        silent_failure.note("wiki_classifier.user_rules_load", exc)
        _USER_RULES_CACHE = []
    return _USER_RULES_CACHE


def reset_user_rules() -> None:
    """Force the next classify_memory call to re-read the rule files.

    Public API — call from a wiki_reload tool when the user edits
    `_rules/*.md` and wants the change to take effect immediately.
    """
    global _USER_RULES_CACHE
    _USER_RULES_CACHE = None


def _apply_user_rules(content: str, tags: list[str] | None):
    """Apply user-loaded rules; return RuleMatch or None when no rule
    matched (caller falls back to hardcoded defaults).

    Returns the RuleMatch dataclass from wiki_rule_engine; the caller
    inspects .target_kind and .matched_rule.
    """
    rules = _load_user_rules()
    if not rules:
        return None

    match = apply_rules(content, tags, rules)
    if match.matched_rule is None:
        return None  # No rule matched — defer to hardcoded defaults
    return match


def _classify_to_legacy_kind(content: str, tags: list[str] | None = None) -> str | None:
    """Run the admission gates and return a legacy kind name or None.

    source: ADR-0294
    """
    if not content or len(content.strip()) < _MIN_ADMISSIBLE_CHARS:
        return None

    stripped = content.strip()
    first_line = stripped.split("\n", 1)[0].strip()

    # source: ADR-0294

    tag_set_pre = {t.lower() for t in (tags or [])}
    if fails_audit_tag_gate(tag_set_pre):
        return None

    # source: ADR-0294

    user_rule_match = _apply_user_rules(content, tags)
    if user_rule_match is not None:
        if user_rule_match.target_kind in (None, ""):
            return None  # rule says reject
        if user_rule_match.matched_rule and user_rule_match.target_kind:
            return user_rule_match.target_kind  # rule admits with kind

    # Gate 1 — Noise rejection (obvious tool/system/slash artefacts)
    for prefix in REJECT_PREFIXES:
        if stripped.startswith(prefix):
            return None

    for pattern in REJECT_PATTERNS:
        if pattern.match(stripped):
            return None

    slug = _slugify(first_line)
    if slug in REJECT_TITLES:
        return None

    # Gate 2 — Hard-negative gate (task-shape, narration, status, deixis,
    # path/URL titles, audit-shaped titles)
    if fails_hard_negatives(content, first_line):
        return None

    # source: ADR-0294

    tag_set = tag_set_pre
    _explicit_knowledge_tags = {
        # source: ADR-0294
        "decision",
        "adr",
        "architecture",
        "spec",
        "design",
        "lesson",
        "convention",
        "rule",
        "standard",
        "paper",
        "research",
        # source: ADR-0294
        "runbook",
        "playbook",
        "tutorial",
        "getting-started",
        "how-to",
        "howto",
        "rfc",
        "proposal",
        "journal",
        # source: ADR-0294
    }
    has_explicit_tag = bool(tag_set & _explicit_knowledge_tags)

    # Gate 3 — Positive scoring (only when no explicit knowledge tag)
    if not has_explicit_tag:
        if positive_score(content, tag_set) < POSITIVE_SCORE_THRESHOLD:
            return None

    # ─── Admitted — now route to the right kind ──────────────────────

    for pat in ADR_PATTERNS:
        if pat.search(content):
            return "adr"

    if tag_set & {"decision", "adr"}:
        return "adr"

    for pat in LESSON_PATTERNS:
        if pat.search(content):
            return "lesson"

    if tag_set & {"lesson", "debugging", "fix", "bug-fix"}:
        return "lesson"

    for pat in CONVENTION_PATTERNS:
        if pat.search(content):
            return "convention"

    if tag_set & {"convention", "rule", "standard"}:
        return "convention"

    if tag_set & SPEC_TAGS and len(content) > _MIN_SPEC_CHARS:
        return "spec"

    if tag_set & {"architecture", "design"} and len(content) > _MIN_SPEC_CHARS:
        return "spec"

    # Catch-all: meaningful content that passed the gate
    return "note"


# source: ADR-0294


def classify_memory(
    content: str,
    tags: list[str] | None = None,
):
    """Classify memory content for the wiki.

    source: ADR-0294

    Returns a ``Classification`` (kind, lifecycle, audience, provenance,
    generator, tags) from ``mcp_server.shared.wiki_classification`` when
    the memory should be admitted, or ``None`` to reject.

    source: ADR-0294
    """

    legacy_kind = _classify_to_legacy_kind(content, tags)
    if legacy_kind is None:
        return None

    modern_kind = detect_modern_kind(content, tags, legacy_kind)
    provenance = detect_provenance(tags)
    lifecycle = pick_lifecycle(modern_kind)
    audiences = detect_audiences(content, tags, modern_kind)

    # Provenance with full generator block when the registered provenance
    # requires it. The registry entry's ``requires_generator`` flag is the
    # source of truth — no hardcoded set of provenance names here.
    generator: Generator | None = None

    prov_value = axis_registry_get(get_registry(), AXIS_PROVENANCE, provenance)
    if prov_value is not None and prov_value.requires_generator:
        generator = Generator(
            model="unknown",
            version="",
            prompt_template="",
            generated_at="",
        )

    # source: ADR-0294
    tag_set = {t.lower() for t in (tags or [])}
    out_tags = tuple(sorted(tag_set))[:50]

    return Classification(
        kind=modern_kind,
        lifecycle=lifecycle,
        audience=audiences,
        provenance=provenance,
        generator=generator,
        tags=out_tags,
    )
