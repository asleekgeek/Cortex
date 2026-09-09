---
title: "ADR-0229 — mcp_server/core/prose_redaction.py rationale"
status: accepted
source: mcp_server/core/prose_redaction.py
---

# ADR-0229 — mcp_server/core/prose_redaction.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
Cortex manufactures reader-facing prose (curated wiki pages, narratives,
briefings). This module owns the pattern inventory used to (a) instruct the
authoring LLM at prompt time and (b) measure authored pages at write time.
Findings are advisory: the write path never blocks on them (generated prose
only gets measured; user-authored content is out of scope — issue #166).
````

## module — original line 9 (docstring)

````text
Distinct from secret/PII redaction (``core/redaction*``): this is prose
style, not data protection.
````

## module — original line 12 (docstring)

````text
Sources (zetetic standard — inventory informed by, implementation ours):
  - Wikipedia, "Signs of AI writing" (WikiProject AI Cleanup) — the
    maintained public catalog; section names cited per pattern below.
  - Method prior art: blader/humanizer v2.9.1, petergyang/no-ai-slop
    (both MIT) — pattern-inventory editing and quoted-evidence detection.
  - House rules (ai-architect.tools redaction practice, 2026): zero em
    dashes in published copy; unsourced attribution is a violation of the
    project's own evidence discipline (CLAUDE.md zetetic standard).
````

## module — original line 21 (docstring)

````text
Only patterns with near-zero false-positive rates on technical prose are
detected mechanically; judgment-level tells (synonym cycling, rule of
three, robotic rhythm) are handled at prompt time via
``REDACTION_CONVENTIONS``. FP guards live in the test suite: an inventory
extension that fires on ordinary technical prose is a regression.

````

## module — original line 52 (comment)

````text
# source: house rule (ai-architect.tools) — zero em dashes in generated copy.
````

## module — original line 54 (comment)

````text
# source: Wikipedia "Signs of AI writing" § Overused vocabulary.
````

## module — original line 66 (comment)

````text
# source: Wikipedia § Vague attributions / weasel wording; escalated by
# the project's zetetic standard (name the source or cut the claim).
````

## module — original line 76 (comment)

````text
# source: Wikipedia § Filler phrases; no-ai-slop "often-empty phrases".
````

## module — original line 87 (comment)

````text
# source: Wikipedia § Superficial analyses — trailing present-participle
# clause faking depth. Narrow verb set keeps FP near zero.
````

## module — original line 98 (comment)

````text
# source: no-ai-slop "binary contrasts"; humanizer § Negative
# parallelisms. Both the two-sentence and the not-just-X-but-Y forms.
````

## module — original line 110 (comment)

````text
# source: no-ai-slop "negative listing" ("Not a X. Not a Y. A Z.").
````

## module — original line 115 (comment)

````text
# source: no-ai-slop "throat-clearing openers".
````

## module — original line 125 (comment)

````text
# source: no-ai-slop "faux-insight setups".
````

## module — original line 134 (comment)

````text
# source: Wikipedia § Undue emphasis on significance/legacy.
````

## module — original line 145 (comment)

````text
# source: Wikipedia § Promotional and advertisement-like language.
````

## module — original line 154 (comment)

````text
# source: humanizer § Copula avoidance; no-ai-slop "fake-strong verbs".
````

## module — original line 163 (comment)

````text
# source: humanizer § Collaborative communication artifacts,
# knowledge-cutoff disclaimers, sycophancy.
````

## module — original line 174 (comment)

````text
# source: humanizer § Signposting and announcements; § Generic
# positive/summary conclusions.
````

## module — original line 184 (comment)

````text
# source: no-ai-slop "rhetorical setups" and "colon reveals" (stock forms).
````

## module — original line 193 (comment)

````text
# source: no-ai-slop "dramatic fragmentation".
````

## module — original line 202 (comment)

````text
# source: keeps a finding to one terminal line; excerpt is a locator, not
# the evidence itself
````

## module — original line 270 (comment)

````text
# Injected into every wiki-authoring prompt (auto_curator prompts) so the
# tells are avoided at generation time; scan_prose measures what slipped
# through at write time. Judgment-level rules live here only.
````
