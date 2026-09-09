# ADR-0354: mcp_server/handlers/consolidation/cycle_types.py implementation decisions

Status: accepted; preserved from the existing implementation during issue #514.

These are historical implementation records, not new algorithm or threshold choices.
Source: `mcp_server/handlers/consolidation/cycle_types.py`; original SHA-256 `998970bbf5ed681ed66fbe0ac092315f0eabf9a5ecaef11cc07625685d11ffd9`.

## Original docstring, lines 1–14

````text
"""Cycle execution/telemetry data types for the headless authoring worker.

Split out of ``headless_authoring`` (Fowler: Move Function, issue #276)
to keep that module under the size limit; ``InvokeResult`` and
``_AnchorCandidate`` stay there (worker identity/config, a distinct
concern from a cycle's execution telemetry). The public import surface
stays ``headless_authoring``, which re-exports all three names below —
every existing ``_root.CycleBudget`` / ``_root.DrainResult`` /
``_root.CycleSummary`` call site is unaffected: same class objects,
same module attribute, just defined in a different file.

No import-cycle concern here: these are plain dataclasses with no
dependency on ``headless_authoring`` or any sibling.
"""
````

## Original docstring, lines 24–44

````text
"""Per-cycle wall-clock + USD budget tracker.

    Pre-condition:  ``deadline`` is a ``time.monotonic()`` value in the
                    future; ``usd_cap`` is a float (<=0 means unlimited).
    Invariant:      ``usd_spent`` is monotonically non-decreasing.

    Concurrency note: with CORTEX_HEADLESS_CONCURRENCY > 1, multiple
    coroutines can see ``exhausted() == False`` simultaneously before any
    of them has charged the budget.  The USD cap is therefore a SOFT
    ceiling with overshoot of at most ``concurrency - 1`` calls beyond
    the cap.  This is acceptable for an operational safety rail.

    Data only — deliberately no methods. mutmut's mutation generator
    categorically excludes the body of any `@dataclass`-decorated class
    (`mutmut/mutation/file_mutation.py:236`), so logic placed on methods
    here would carry zero mutation coverage no matter how the test loader
    names the module (issue #262 3rd pass; issue #282).
    `cycle_budget_time_left` / `cycle_budget_exhausted` /
    `cycle_budget_charge` below carry the same logic as free functions
    instead.
    """
````

## Original comment, lines 94–95

````text
# Budget telemetry fields (added in throttle refactor — callers that
    # access only the original fields are not affected).
````

## Original comment, lines 97–100

````text
# wall_clock_ms is intentionally equal to duration_ms for the cycle: both
    # measure the cycle's wall-clock span. Kept as a distinct, explicitly-named
    # field because wiki_maintenance's telemetry dict emits both keys; the
    # original duration_ms is retained for pre-throttle callers.
````

