"""Core: grooming staleness classification (pure logic, no I/O).

"Grooming" here means judgment-level curation -- wiki authoring
(curate_wiki), lesson distillation (curate_distill), lesson promotion
(lesson_promotion) -- as distinct from the mechanical consolidate pass
(purge/backfill/dashboards/backlog-count), which already runs at every
SessionEnd and needs no staleness alarm (mcp_server/handlers/
consolidation/wiki_maintenance.py doc header, 2026-05-18).

Motivating measurement: the wiki went 76 days (2026-04-25 -> 2026-07-10)
without a single page being tended while the mechanical pass ran 91
times in the same window -- the mechanical/judgment split was invisible
because nothing measured the age of the judgment-level work. This
module is the pure decision logic; the DB-backed age lookup lives in
``PgStatsMixin.get_grooming_ages`` (infrastructure/pg_store_stats.py).
"""

from __future__ import annotations

from datetime import datetime, timezone

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
#   )
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
GROOMING_STALENESS_THRESHOLD_DAYS = 6.0


def days_since(last_iso: str | None, now: datetime | None = None) -> float | None:
    """Elapsed days between ``last_iso`` and ``now``.

    Precondition: ``last_iso`` is a valid ISO-8601 timestamp string, or
    None.
    Postcondition: returns a non-negative float when ``last_iso`` is
    set; returns None when ``last_iso`` is None (the grooming kind has
    never executed -- age is undefined, not zero).
    """
    if not last_iso:
        return None
    ts = datetime.fromisoformat(last_iso)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    now = now or datetime.now(timezone.utc)
    return (now - ts).total_seconds() / 86400.0


def is_stale(
    last_iso: str | None,
    threshold_days: float = GROOMING_STALENESS_THRESHOLD_DAYS,
    now: datetime | None = None,
) -> bool:
    """True when a grooming kind is overdue for attention.

    Precondition: ``threshold_days`` > 0.
    Postcondition: True iff the kind has never run (``last_iso`` is
    None) or last ran more than ``threshold_days`` ago. Never-run is
    always stale by construction -- an undefined age exceeds any finite
    threshold.
    """
    d = days_since(last_iso, now=now)
    return d is None or d > threshold_days
