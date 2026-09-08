"""Wiki page templates + naming conventions.

source: ADR-0315"""

from __future__ import annotations

from typing import Final

# ── Required front-matter fields per page kind ──────────────────────────

REQUIRED_FRONTMATTER: Final[dict[str, tuple[str, ...]]] = {
    # source: ADR-0315
    "adr": (
        "id",
        "title",
        "status",
        "date",
        "entry",
        "mandatory",
        "how",
        "result",
        "serves",
        "consequences",
    ),
    "specs": ("title", "status", "owner", "created", "updated"),
    "guides": ("title", "audience", "prerequisites", "updated"),
    "reference": ("title", "scope", "updated"),
    "conventions": ("title", "applies_to", "updated"),
    "lessons": ("title", "date", "triggering_event", "updated"),
    "notes": ("title", "updated"),
    "journal": ("title", "date"),
    "files": ("file_path", "language", "updated"),
    # source: ADR-0315
    "tutorial": (
        "title",
        "kind",
        "lifecycle",
        "audience",
        "provenance",
        "updated",
    ),
    "how-to": (
        "title",
        "kind",
        "lifecycle",
        "audience",
        "provenance",
        "updated",
    ),
    "runbook": (
        "title",
        "kind",
        "lifecycle",
        "audience",
        "provenance",
        "trigger",
        "updated",
    ),
    "rfc": (
        "title",
        "kind",
        "lifecycle",
        "audience",
        "provenance",
        "created",
        "updated",
    ),
    "explanation": (
        "title",
        "kind",
        "lifecycle",
        "audience",
        "provenance",
        "updated",
    ),
}

# source: ADR-0315


STATUS_VALUES: Final[dict[str, tuple[str, ...]]] = {
    "adr": ("proposed", "accepted", "rejected", "deprecated", "superseded"),
    "specs": ("draft", "review", "accepted", "implemented", "deprecated"),
}


# ── Templates ────────────────────────────────────────────────────────────


ADR_TEMPLATE = """---
id: {{id}}
title: {{title}}
status: {{status}}
date: {{date}}
supersedes: {{supersedes}}
---

# ADR-{{id}}: {{title}}

## Status

{{status}}

## Entry

> Problem, task, or trigger that opened this work — the situation as it
> existed before any change. State the symptom, the user request, or the
> external event that put this on the table. Avoid speculation about
> root causes; that belongs in How.

{{entry}}

## Mandatory elements

> Constraints that had to be respected: architectural rules (Clean
> Architecture layer boundaries, SOLID), invariants (no SQLite, layer
> dependency rule, source-citation discipline), compatibility windows,
> deadlines, regulatory or security gates, paper-grounded equations,
> contracts with upstream/downstream systems.

{{mandatory}}

## How

> Approach taken — implementation path, technical choices, the sequence
> of moves. Reference specific files (with full paths) and the design
> reasoning. If alternatives were tried and abandoned, name them here;
> if formally considered and rejected, capture them under Alternatives.

{{how}}

## Result

> What was actually delivered. Concrete outcome — code shipped, tests
> passing, regression avoided, latency or accuracy delta measured. Cite
> the commit, the benchmark run, or the artifact that proves the
> outcome. If the work is partial, state precisely what is and is not
> done.

{{result}}

## Serves

> What this enables — purpose and downstream role. Who depends on it,
> which system invariant it upholds, which user-visible behaviour it
> supports. This is the "why it stays in the codebase" answer.

{{serves}}

## Context

> Legacy section — kept for ADRs authored before 2026-05-18. New ADRs
> may merge Context into Entry. The grooming agent preserves any
> existing Context content here.

{{context}}

## Decision

> Legacy section — kept for ADRs authored before 2026-05-18. New ADRs
> express the decision through Result + How. The grooming agent
> preserves any existing Decision content here.

{{decision}}

## Consequences

### Positive
{{consequences_positive}}

### Negative
{{consequences_negative}}

### Neutral
{{consequences_neutral}}

## Alternatives considered

{{alternatives}}

## References

{{references}}
"""


SPEC_TEMPLATE = """---
title: {{title}}
status: {{status}}
owner: {{owner}}
created: {{created}}
updated: {{updated}}
---

# {{title}}

## Problem

{{problem}}

## Goals

{{goals}}

## Non-goals

{{non_goals}}

## Design

{{design}}

## Invariants

{{invariants}}

## Open questions

{{open_questions}}

## References

{{references}}
"""


GUIDE_TEMPLATE = """---
title: {{title}}
audience: {{audience}}
prerequisites: {{prerequisites}}
updated: {{updated}}
---

# {{title}}

## When to use

{{when_to_use}}

## Prerequisites

{{prerequisites_detail}}

## Steps

{{steps}}

## Verification

{{verification}}

## Troubleshooting

{{troubleshooting}}
"""


REFERENCE_TEMPLATE = """---
title: {{title}}
scope: {{scope}}
updated: {{updated}}
---

# {{title}}

## Scope

{{scope_detail}}

## API / Interface

{{api}}

## Examples

{{examples}}

## See also

{{see_also}}
"""


CONVENTION_TEMPLATE = """---
title: {{title}}
applies_to: {{applies_to}}
updated: {{updated}}
---

# {{title}}

## Rule

{{rule}}

## Rationale

{{rationale}}

## Examples

### Correct
{{correct_examples}}

### Incorrect
{{incorrect_examples}}

## Enforcement

{{enforcement}}
"""


LESSON_TEMPLATE = """---
title: {{title}}
date: {{date}}
triggering_event: {{triggering_event}}
updated: {{updated}}
---

# {{title}}

## What happened

{{what_happened}}

## Why it went wrong

{{root_cause}}

## What we learned

{{lesson}}

## Rule going forward

{{rule}}

## References

{{references}}
"""


NOTE_TEMPLATE = """---
title: {{title}}
updated: {{updated}}
---

# {{title}}

{{body}}
"""


JOURNAL_TEMPLATE = """---
title: {{title}}
date: {{date}}
---

# {{title}}

## Summary

{{summary}}

## Details

{{details}}
"""


FILE_TEMPLATE = """---
file_path: {{file_path}}
language: {{language}}
updated: {{updated}}
---

# {{file_path}}

## Purpose

{{purpose}}

## Public API

{{public_api}}

## Dependencies

{{dependencies}}

## Notes

{{notes}}
"""


# source: ADR-0315


TUTORIAL_TEMPLATE = """---
title: {{title}}
kind: tutorial
lifecycle: {{lifecycle}}
audience: {{audience}}
provenance: {{provenance}}
updated: {{updated}}
---

# {{title}}

## What you'll learn

{{learning_outcomes}}

## Prerequisites

{{prerequisites}}

## Steps

{{steps}}

## Next steps

{{next_steps}}
"""


HOWTO_TEMPLATE = """---
title: {{title}}
kind: how-to
lifecycle: {{lifecycle}}
audience: {{audience}}
provenance: {{provenance}}
updated: {{updated}}
---

# {{title}}

## When to use this

{{when_to_use}}

## Steps

{{steps}}

## Verification

{{verification}}
"""


RUNBOOK_TEMPLATE = """---
title: {{title}}
kind: runbook
lifecycle: {{lifecycle}}
audience: {{audience}}
provenance: {{provenance}}
trigger: {{trigger}}
updated: {{updated}}
---

# {{title}}

## Trigger

{{trigger_description}}

## Diagnosis

{{diagnosis}}

## Recovery procedure

{{recovery_steps}}

## Rollback

{{rollback}}

## Post-incident

{{post_incident}}
"""


RFC_TEMPLATE = """---
title: {{title}}
kind: rfc
lifecycle: {{lifecycle}}
audience: {{audience}}
provenance: {{provenance}}
created: {{created}}
updated: {{updated}}
---

# {{title}}

## Summary

{{summary}}

## Motivation

{{motivation}}

## Proposed design

{{design}}

## Alternatives considered

{{alternatives}}

## Open questions

{{open_questions}}
"""


EXPLANATION_TEMPLATE = """---
title: {{title}}
kind: explanation
lifecycle: {{lifecycle}}
audience: {{audience}}
provenance: {{provenance}}
updated: {{updated}}
---

# {{title}}

## Context

{{context}}

## Explanation

{{explanation}}

## Implications

{{implications}}

## See also

{{see_also}}
"""


TEMPLATES: Final[dict[str, str]] = {
    # source: ADR-0315
    "adr": ADR_TEMPLATE,
    "specs": SPEC_TEMPLATE,
    "guides": GUIDE_TEMPLATE,
    "reference": REFERENCE_TEMPLATE,
    "conventions": CONVENTION_TEMPLATE,
    "lessons": LESSON_TEMPLATE,
    "notes": NOTE_TEMPLATE,
    "journal": JOURNAL_TEMPLATE,
    "files": FILE_TEMPLATE,
    # source: ADR-0315
    "tutorial": TUTORIAL_TEMPLATE,
    "how-to": HOWTO_TEMPLATE,
    "runbook": RUNBOOK_TEMPLATE,
    "rfc": RFC_TEMPLATE,
    "explanation": EXPLANATION_TEMPLATE,
}


def template_for(kind: str) -> str | None:
    """Return the template for a page kind, or None if unknown."""
    return TEMPLATES.get(kind)


def required_fields(kind: str) -> tuple[str, ...]:
    """Return the required front-matter keys for a page kind."""
    return REQUIRED_FRONTMATTER.get(kind, ("title", "updated"))


def valid_status_values(kind: str) -> tuple[str, ...]:
    """Return the valid ``status`` values for a page kind, or ()."""
    return STATUS_VALUES.get(kind, ())


# ── Naming conventions ───────────────────────────────────────────────────


class NamingConvention:
    """Canonical naming rules per page kind.

    Each rule pair ``(regex_pattern, description)`` defines how a slug
    must be shaped. The grooming agent applies the rule to rename pages
    off the convention.
    """

    ADR = (
        r"^\d{4}-[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$",
        "ADR: <4-digit>-<kebab-slug>.md (e.g., 0042-prefer-plan-over-list.md)",
    )

    SPEC = (
        r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$",
        "Spec: <kebab-slug>.md (e.g., phase-5-pool-admission-design.md)",
    )

    DEFAULT = (
        r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$",
        "Page: <kebab-slug>.md — lowercase alphanum + hyphens, no "
        "underscores, no leading/trailing hyphens.",
    )


def naming_convention(kind: str) -> tuple[str, str]:
    """Return (regex_pattern, human description) for a page kind."""
    if kind == "adr":
        return NamingConvention.ADR
    if kind == "specs":
        return NamingConvention.SPEC
    return NamingConvention.DEFAULT
