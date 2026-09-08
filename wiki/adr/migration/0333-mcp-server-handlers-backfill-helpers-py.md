# ADR-0333: mcp_server/handlers/backfill_helpers.py implementation decisions

Status: accepted; preserved from the existing implementation during issue #514.

These are historical implementation records, not new algorithm or threshold choices.
Source: `mcp_server/handlers/backfill_helpers.py`; original SHA-256 `e0ac4a3af024d07e9e6764d707971f1494873d1e7ae4a58f7cc2cd1180196590`.

## Original docstring, lines 1–4

````text
"""Helpers for backfill_memories -- file discovery, hashing, and concept linking.

Extracted from backfill_memories.py to keep both files under 300 lines.
"""
````

## Original comment, lines 140–146

````text
# Walk recursively to capture four legitimate session layouts:
        #   1. Flat parent           <slug>/<uuid>.jsonl
        #   2. UUID-dir parent       <slug>/<uuid>/<uuid>.jsonl
        #   3. Subagent (data dir)   <slug>/<parent>/data/subagents/agent-<id>.jsonl
        #   4. Subagent (direct)     <slug>/<parent>/agent-<id>.jsonl
        # Pre-fix glob("*.jsonl") only saw layout 1, missing ~89% of sessions
        # when subagent / teammate use is active. Issue #15.
````

## Original docstring, lines 164–172

````text
"""Convert a project slug like '-Users-you-project-name' to a canonical domain.

    Delegates to ``shared.domain_mapping.resolve_domain`` which handles
    git-derived canonicalisation, worktree-suffix stripping, and fragment
    matching. Previously this took ``parts[-1]`` of the slug, which for a
    slug like ``-Users-...-worktrees-pipeline-academic-research-…-body``
    returned ``"body"`` — every truncated slug tail polluted memory.domain
    with a single noise word ("for", "via", "voice", "few", "large", …).
    """
````

## Original docstring, lines 181–193

````text
"""Gist + artifact-pointer an extracted item's content if it is oversized.

    Pre: content is the memory body string for an extracted import/backfill
    item.
    Post: when ``content`` fits GIST_BUDGET, returns it unchanged. When it
    exceeds the budget, the FULL raw content is written to a content-addressed
    artifact and the returned string is a deterministic gist plus a pointer
    line — same write-side hygiene as the post_tool_capture hook
    (docs/provenance/bounded-io-phase2-design.md F3). Single choke point so the
    extractor (core) stays I/O-free: the I/O happens here, in the handler
    (composition-root) layer. Artifact write failure falls back to the full
    content (capture must not be lost).
    """
````

