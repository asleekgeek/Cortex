# ADR-0346: mcp_server/handlers/consolidation/cascade.py implementation decisions

Status: accepted; preserved from the existing implementation during issue #514.

These are historical implementation records, not new algorithm or threshold choices.
Source: `mcp_server/handlers/consolidation/cascade.py`; original SHA-256 `191b922e1103ce47f333577e2f7abb51d4b06c2a2f73f130576fbf5c76f9b38d`.

## Original comment, lines 21–23

````text
# Source: issue #13 — cascade previously wrote a heartbeat UPDATE on
# EVERY scanned memory (~2000) even when nothing advanced. Below this
# delta, the hours_in_stage change is noise and the write is waste.
````

## Original comment, lines 26–28

````text
# Source: issue #13 — the 503-transition payload darval reported is
# redundant with the stage_transitions table and inflates the MCP
# response. Surface a preview + count instead.
````

## Original comment, lines 142–144

````text
# Compute stage_entered_at for the new stage:
        # For backfilled memories with real timestamps, account for the time
        # they would have spent in the previous stage (min_dwell hours).
````

## Original comment, lines 168–171

````text
# Not advancing: only write a heartbeat if the hours delta is
    # large enough to be informative. Below _HEARTBEAT_SKIP_HOURS the
    # change is noise and the write is wasted fsync amplification
    # (issue #13, Feinstein audit of darval's 66K-store run).
````

