---
title: "ADR-0186 — mcp_server/core/grooming_health.py rationale"
status: accepted
source: mcp_server/core/grooming_health.py
---

# ADR-0186 — mcp_server/core/grooming_health.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 3 (docstring)

````text
"Grooming" here means judgment-level curation -- wiki authoring
(curate_wiki), lesson distillation (curate_distill), lesson promotion
(lesson_promotion) -- as distinct from the mechanical consolidate pass
(purge/backfill/dashboards/backlog-count), which already runs at every
SessionEnd and needs no staleness alarm (mcp_server/handlers/
consolidation/wiki_maintenance.py doc header, 2026-05-18).
````

## module — original line 10 (docstring)

````text
Motivating measurement: the wiki went 76 days (2026-04-25 -> 2026-07-10)
without a single page being tended while the mechanical pass ran 91
times in the same window -- the mechanical/judgment split was invisible
because nothing measured the age of the judgment-level work. This
module is the pure decision logic; the DB-backed age lookup lives in
``PgStatsMixin.get_grooming_ages`` (infrastructure/pg_store_stats.py).

````

## legs_due — original line 96 (mixed-contract-rationale)

````text
    Precondition: ``kinds`` has ``'wiki'``/``'distillation'`` keys, each a
    dict carrying ``'stale'`` (bool) and ``'backlog_count'`` (int) --
    ``get_grooming_health``'s exact output shape. A ``'promotion'`` key
    may also be present but is never read here.
    Postcondition: a leg is due iff ``force`` is True, OR the leg is both
    stale AND has a non-zero backlog -- a stale kind with an empty
    backlog has nothing to do; a fresh kind with backlog is still being
    worked through at its natural pace and does not need a scheduled
    nudge. ``force=True`` marks every leg due unconditionally (used by
    an operator-invoked forced run, never by the unattended cron path).
    Invariant: the returned dict has EXACTLY the keys ``'wiki'`` and
    ``'distillation'`` -- ``'promotion'`` is never a key of this
    function's return value, by construction, enforcing at the type
    level that a caller iterating this dict's keys can never reach a
    promotion leg (the design doc's "no auto-promotion, ever" contract,
    see ``lesson_promotion.py``'s own docstring).
    
````

## module — original line 23 (comment)

````text
# Alert threshold -- sourced from the measured cadence of real working
# sessions, not invented (Zetetic §8: no source, no constant).
#
# Query (dev DB postgresql://127.0.0.1:5432/cortex, run 2026-07-11):
#
#   WITH days AS (
#     SELECT DISTINCT date_trunc('day', timestamp) AS d
#     FROM consolidation_log
#   ), gaps AS (
#     SELECT d - lag(d) OVER (ORDER BY d) AS gap FROM days
#   )  # noqa: ERA001 -- sec8 SQL provenance for the constant below, not code
#   SELECT percentile_cont(0.9) WITHIN GROUP (
#            ORDER BY EXTRACT(EPOCH FROM gap) / 86400.0
#          ) AS p90_gap_days
#   FROM gaps WHERE gap IS NOT NULL;
#   -- -> p90_gap_days = 2.0  (19 distinct active session-days measured,
#   --    median gap = 1 day, max observed gap = 9 days)
#
# ``consolidation_log`` gets one row per SessionEnd consolidate call
# (mcp_server/hooks/session_lifecycle.py:_run_consolidation), so
# distinct active days in that table are exactly the empirical cadence
# of real working sessions -- not an assumed "daily" cadence.
#
# A single p90-scale gap (2 days) is still normal jitter -- session
# cadence is irregular (design doc measured 1-47 consolidate calls/day
# depending on activity). Alerting at exactly p90 would fire on
# ordinary variance. Requiring 3x the p90 gap before alerting keeps the
# false-positive rate low under an i.i.d. approximation of gap sizes
# (Chebyshev-style: three independent p90-scale exceedances compound to
# a low joint probability) while still catching drift at 6 days --
# an order of magnitude before the 76-day silence this metric exists to
# catch.
````
