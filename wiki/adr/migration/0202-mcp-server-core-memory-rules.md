---
title: "ADR-0202 — mcp_server/core/memory_rules.py rationale"
status: accepted
source: mcp_server/core/memory_rules.py
---

# ADR-0202 — mcp_server/core/memory_rules.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Implements condition parsing (field, operator, value) and evaluation against
memory dicts. Hard rules EXCLUDE matching memories, soft rules boost/penalize
retrieval scores, tag rules attach a tag to matching memories.
````

## module — original line 7 (docstring)

````text
This module is the single grammar authority for rule text: `add_rule`
(mcp_server/handlers/add_rule.py) MUST accept only condition/action strings
this module can parse — enforced by calling `validate_rule` at write time.
Canonical syntax:
    condition: "<field> <operator> <value>", operator in VALID_OPERATORS.
        e.g. "importance > 0.7", "tag contains deprecated".
    action:    "filter" (hard rules only) | "boost:<float>" | "penalty:<float>"
               (soft rules only) | "tag:<name>" (tag rules only).
````

## module — original line 16 (docstring)

````text
Pure business logic — no I/O. Rule storage is handled by the caller.

````

## evaluate_condition — original line 192 (mixed-contract-rationale)

````text
    Precondition: `condition` is any string (parseable or not); `memory` is a
    dict, possibly missing the referenced field.
    Postcondition: returns True iff the condition parses AND the memory
    satisfies it. An unparseable condition never matches (returns False) —
    this is the read-side fail-safe: a malformed rule (which should not
    exist post `validate_rule`, but may for legacy data written before that
    gate existed) degrades to a silent no-op rather than, under hard-rule
    semantics, excluding every memory from every recall. The parse failure
    is logged so operators can find and repair the offending row.
    
````

## validate_rule — original line 322 (mixed-contract-rationale)

````text
    Precondition: none — inputs may be arbitrary strings.
    Postcondition: returns the empty list iff `condition` is parseable by
    parse_condition, `action` is parseable by parse_action, and the action's
    mechanism matches rule_type (hard→filter, soft→boost/penalty,
    tag→tag:name). This is the fail-closed write-time gate: it is the only
    place a rule is rejected outright; evaluate_condition's read-time
    behavior on unparseable conditions is deliberately permissive (see its
    docstring) precisely because this gate is expected to prevent
    unparseable conditions from ever reaching storage in the first place.
    
````
