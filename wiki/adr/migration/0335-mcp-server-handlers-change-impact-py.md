# ADR-0335: mcp_server/handlers/change_impact.py implementation decisions

Status: accepted; preserved from the existing implementation during issue #514.

These are historical implementation records, not new algorithm or threshold choices.
Source: `mcp_server/handlers/change_impact.py`; original SHA-256 `de6671f04fbe513c2a051d3484d1c14b38187c45d74fe14a9e5bde521bdb5471`.

## Original docstring, lines 1–20

````text
"""Handler: change_impact — find memories touched by a commit's code
changes (ADR-0046 Phase 4).

Flow:
  1. Ask AP's ``detect_changes`` for changed symbols and files between
     two commits (defaults: ``HEAD~1``..``HEAD``).
  2. Optionally expand via ``get_impact`` for each changed symbol to
     include downstream call-graph reach.
  3. Match the impacted qualnames and file paths against the content
     of recent memories (pure-logic matcher in core).
  4. Return a deterministic report; the caller decides whether to bump
     heat, tag, or notify.

Read-only by default. If ``apply_heat_bump=True`` and the match set is
small (≤ 20), the handler calls ``update_memory_heat`` for each match
with a capped delta — the same ``_IMPACT_BOOST`` as the preemptive hook.

When AP is disabled the handler returns ``status=skipped`` with the
usual explanation.
"""
````

## Original schema description, interim lines 47–54

````text
Report which Cortex memories reference code that changed in a commit (ADR-0046 Phase 4). Uses ai-architect-mcp-codebase's detect_changes and optionally get_impact to compute the symbol/file impact set, then matches against recent memories. Read-only by default; pass apply_heat_bump=true to nudge heat on the top 20 matches by +0.15. Requires AP enabled (CORTEX_MEMORY_AP_ENABLED=1, the default); returns status=skipped otherwise.
````

