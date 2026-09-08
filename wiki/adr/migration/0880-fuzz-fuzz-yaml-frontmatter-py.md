# ADR-0880: fuzz/fuzz_yaml_frontmatter.py design and historical evidence

Status: accepted; existing test/harness evidence preserved during issue #514.

Source `fuzz/fuzz_yaml_frontmatter.py`, original SHA-256 `00b0bb28ebd63a60c9c8b707a554e7847aafdbbf368cb3d9ae05e0bdd7c4f264`.
Assertions and runtime fixture literals remain unchanged.

## Original docstring, lines 2–23

````text
"""Fuzz the hand-rolled YAML frontmatter parser.

Why this target
---------------
`parse_yaml_frontmatter` is a hand-written parser — not a hardened library —
and it reads the front matter of memory and wiki documents. Those documents
carry LLM output and anything else that reaches the ingest path, so its input
is untrusted by the standard's own rule (§13.1 D2). A parser over untrusted
text with no fuzzing is exactly where crash-on-input bugs outlive a green
unit suite, because tests encode the shapes the author thought of.

It is also regex-driven (`^---\\s*\\n([\\s\\S]*?)\\n---\\s*\\n([\\s\\S]*)$`
over the whole document), which puts pathological backtracking on the table
for a document a user can supply. libFuzzer's own timeout is what surfaces
that; it is not something an assertion can express.

Properties asserted (all total-function properties, not parse correctness):
  * returns a FrontmatterResult for ANY input, never raises;
  * `meta` is always a dict — callers index it without a None check;
  * every key is lowercased, which is the documented contract;
  * `body` is a substring of the input — the parser must not invent text.
"""
````

