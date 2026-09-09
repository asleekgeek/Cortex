# ADR-0344: mcp_server/handlers/consolidation/authoring_prompts.py implementation decisions

Status: accepted; preserved from the existing implementation during issue #514.

These are historical implementation records, not new algorithm or threshold choices.
Source: `mcp_server/handlers/consolidation/authoring_prompts.py`; original SHA-256 `2454910fdad945bbc9fdd35ba65d00ff3ec5bbe65598fe81629255708028137c`.

## Original docstring, lines 1–20

````text
"""Prompt construction, response parsing, and gap-marker primitives.

Pure leaf helpers for the headless authoring worker. No I/O, no
subprocess, no patchable state — these are deterministic string
transforms split out of ``headless_authoring`` to keep that module
under the size limit (Fowler: Extract Function / Move Function). The
public import surface remains ``headless_authoring``; these names are
imported there and by the drain/orchestration siblings.

Prompt-injection defence (audit B-1): any text sourced from the
filesystem (source code, wiki frontmatter, README, manifests, gap
descriptions derived from frontmatter) is untrusted input. Wrapping
every such block in the delimiter below, together with the GUARD
header, demotes the content to DATA in the model's context, not
instructions.

Reference: Anthropic prompt-injection mitigation guidance — use
explicit content delimiters and a system-level guard line to
separate trusted instructions from untrusted source material.
"""
````

## Original docstring, lines 41–47

````text
"""Wrap ``text`` in the untrusted-source-material delimiter.

    Pre-condition:  ``text`` is a string (may be empty).
    Post-condition: returned string is delimited so the model treats
                    its content as data, not instructions.
    Invariant:      original text is preserved verbatim between tags.
    """
````

## Original comment, lines 149–151

````text
# gap_description may originate from wiki frontmatter (attacker-
    # influenceable) — always wrap as untrusted even when it matched a
    # known slug, because the fallback path passes raw frontmatter text.
````

## Original docstring, lines 425–430

````text
"""Parse the LLM response back into ``{gap_name: content}`` dict.

    The response uses ``<<<gap-slug>>>`` delimiters per the prompt
    contract. Robust to extra whitespace, missing delimiters (gaps
    not present in the response stay unfilled and replay later).
    """
````

