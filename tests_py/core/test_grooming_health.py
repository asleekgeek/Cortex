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
