"""Tests for mcp_server.core.grooming_health — pure staleness logic.

No I/O, no PG connection needed (Move 5: separated from the DB-backed
age lookup in PgStatsMixin.get_grooming_ages, tested separately in
tests_py/handlers/test_get_grooming_health.py).
"""

from datetime import datetime, timedelta, timezone

from mcp_server.core.grooming_health import (
    GROOMING_STALENESS_THRESHOLD_DAYS,
    days_since,
    is_stale,
    legs_due,
)


class TestDaysSince:
    def test_none_returns_none(self):
        assert days_since(None) is None

    def test_now_returns_near_zero(self):
        now = datetime.now(timezone.utc)
        assert days_since(now.isoformat(), now=now) == 0.0

    def test_naive_timestamp_treated_as_utc(self):
        now = datetime.now(timezone.utc)
        naive = (now - timedelta(days=3)).replace(tzinfo=None).isoformat()
        result = days_since(naive, now=now)
        assert result is not None
        assert abs(result - 3.0) < 0.01

    def test_ten_days_ago(self):
        now = datetime.now(timezone.utc)
        ten_days_ago = (now - timedelta(days=10)).isoformat()
        result = days_since(ten_days_ago, now=now)
        assert result is not None
        assert abs(result - 10.0) < 0.01


class TestIsStale:
    def test_never_run_is_always_stale(self):
        """Undefined age (last_iso=None) exceeds any finite threshold."""
        assert is_stale(None) is True
        assert is_stale(None, threshold_days=1000.0) is True

    def test_recent_run_is_not_stale(self):
        now = datetime.now(timezone.utc)
        recent = (now - timedelta(hours=1)).isoformat()
        assert is_stale(recent, now=now) is False

    def test_run_older_than_threshold_is_stale(self):
        now = datetime.now(timezone.utc)
        old = (now - timedelta(days=GROOMING_STALENESS_THRESHOLD_DAYS + 1)).isoformat()
        assert is_stale(old, now=now) is True

    def test_run_at_exactly_threshold_is_not_stale(self):
        """Boundary: strictly greater-than, not >=, so a run landing
        exactly on the threshold day doesn't flip stale on a clock
        rounding artifact."""
        now = datetime.now(timezone.utc)
        exactly = (now - timedelta(days=GROOMING_STALENESS_THRESHOLD_DAYS)).isoformat()
        assert is_stale(exactly, now=now) is False

    def test_custom_threshold_overrides_default(self):
        now = datetime.now(timezone.utc)
        two_days_ago = (now - timedelta(days=2)).isoformat()
        assert is_stale(two_days_ago, threshold_days=1.0, now=now) is True
        assert is_stale(two_days_ago, threshold_days=3.0, now=now) is False

    def test_default_threshold_is_positive_and_sourced(self):
        # Sourced from measured session cadence (module docstring); a
        # regression to 0 or negative would make every kind permanently
        # stale.
        assert GROOMING_STALENESS_THRESHOLD_DAYS > 0


class TestLegsDue:
    """G-3 scheduled groomer: decides which legs a headless run should
    execute, from get_grooming_health's exact kinds shape."""

    def _kinds(self, *, wiki_stale, wiki_backlog, distill_stale, distill_backlog):
        return {
            "wiki": {"stale": wiki_stale, "backlog_count": wiki_backlog},
            "distillation": {"stale": distill_stale, "backlog_count": distill_backlog},
            "promotion": {"stale": True, "backlog_count": 133},
        }

    def test_stale_with_backlog_is_due(self):
        kinds = self._kinds(
            wiki_stale=True, wiki_backlog=12, distill_stale=True, distill_backlog=25
        )
        assert legs_due(kinds) == {"wiki": True, "distillation": True}

    def test_stale_with_empty_backlog_is_not_due(self):
        """Nothing to drain even though the age alarm fired."""
        kinds = self._kinds(
            wiki_stale=True, wiki_backlog=0, distill_stale=True, distill_backlog=0
        )
        assert legs_due(kinds) == {"wiki": False, "distillation": False}

    def test_fresh_with_backlog_is_not_due(self):
        """Recently groomed; still catching up at its own pace."""
        kinds = self._kinds(
            wiki_stale=False, wiki_backlog=12, distill_stale=False, distill_backlog=25
        )
        assert legs_due(kinds) == {"wiki": False, "distillation": False}

    def test_mixed_legs_independent(self):
        kinds = self._kinds(
            wiki_stale=True, wiki_backlog=12, distill_stale=False, distill_backlog=25
        )
        assert legs_due(kinds) == {"wiki": True, "distillation": False}

    def test_force_marks_both_due_regardless_of_health(self):
        kinds = self._kinds(
            wiki_stale=False, wiki_backlog=0, distill_stale=False, distill_backlog=0
        )
        assert legs_due(kinds, force=True) == {"wiki": True, "distillation": True}

    def test_promotion_never_a_key_of_the_result(self):
        """Type-level enforcement of the no-auto-promotion invariant: a
        caller iterating legs_due()'s keys can never reach a promotion
        leg, even if 'promotion' is present (and stale) in the input."""
        kinds = self._kinds(
            wiki_stale=False, wiki_backlog=0, distill_stale=False, distill_backlog=0
        )
        result = legs_due(kinds, force=True)
        assert "promotion" not in result
        assert set(result.keys()) == {"wiki", "distillation"}

    def test_missing_kind_degrades_to_not_due(self):
        assert legs_due({}) == {"wiki": False, "distillation": False}
