# ADR-0352: mcp_server/handlers/consolidation/compression.py implementation decisions

Status: accepted; preserved from the existing implementation during issue #514.

These are historical implementation records, not new algorithm or threshold choices.
Source: `mcp_server/handlers/consolidation/compression.py`; original SHA-256 `3183c81e3a7246e8fe56cbe8461013df23216b5d182265f0d5305770b76a64a6`.

## Original comment, lines 23–24

````text
# source: structural — compression levels documented in the module
# docstring: full text (0) -> gist (1) -> tag (2)
````

## Original docstring, lines 34–37

````text
"""Compress aging memories along the rate-distortion curve.

    `memories` may be pre-loaded by the consolidate handler (issue #13).
    """
````

## Original comment, lines 85–86

````text
# Preconditions:
            #   - mem["content"] is the original full text.
````

