"""Tests for the distillation leg of the scheduled groomer (G-3) —
``handlers.consolidation.distill_drain``.

No real ``claude`` subprocess and no PostgreSQL connection needed
anywhere in this file: ``run_distill_drain_cycle`` never calls
``remember``/``wiki_write`` itself (the invoke DI seam stands in for the
``claude -p`` child, matching ``test_headless_authoring_throttle.py``'s
pattern), and the module under test performs no store I/O of its own.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import pytest

import mcp_server.handlers.consolidation.distill_drain as dd
import mcp_server.handlers.consolidation.headless_authoring as ha


def _job(marker: str = "distill-of:abc", kind: str = "error_success") -> dict[str, Any]:
    return {
        "job_type": "distill",
        "dossier_kind": kind,
        "topic": "t",
        "domain": "d",
        "memory_ids": [1, 2],
        "marker": marker,
        "avg_heat": 0.5,
        "prompt": f"Distillation dossier ({kind}) ... marker={marker}",
    }


@dataclass
class _FakeInvokeStats:
    calls: int = 0
    max_concurrent: int = 0
    prompts_seen: list = field(default_factory=list)
    _in_flight: int = field(default=0, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    async def __call__(
        self,
        prompt: str,
        *,
        cost_per_call: float = 0.1,
        sleep: float = 0.01,
        text: str | None = "ok",
        **_: Any,
    ) -> ha.InvokeResult:
        async with self._lock:
            self.calls += 1
            self._in_flight += 1
            self.prompts_seen.append(prompt)
            if self._in_flight > self.max_concurrent:
                self.max_concurrent = self._in_flight
        await asyncio.sleep(sleep)
        async with self._lock:
            self._in_flight -= 1
        return ha.InvokeResult(text=text, cost_usd=cost_per_call)


class TestBasicDrain:
    @pytest.mark.asyncio
    async def test_no_jobs_returns_empty_summary(self, monkeypatch):
        monkeypatch.setattr(ha, "CORTEX_HEADLESS_AGENTS", 1)
        summary = await dd.run_distill_drain_cycle([])
        assert summary.jobs_offered == 0
        assert summary.attempted == 0
        assert summary.results == []

    @pytest.mark.asyncio
    async def test_each_job_produces_one_attempted_result(self, monkeypatch):
        monkeypatch.setattr(ha, "CORTEX_HEADLESS_AGENTS", 1)
        monkeypatch.setattr(ha, "CORTEX_HEADLESS_CONCURRENCY", 4)
        monkeypatch.setattr(ha, "CORTEX_HEADLESS_BUDGET_SEC", 60.0)
        monkeypatch.setattr(ha, "CORTEX_HEADLESS_USD_BUDGET", 100.0)
        jobs = [_job(f"distill-of:{i}") for i in range(3)]
        stats = _FakeInvokeStats()

        summary = await dd.run_distill_drain_cycle(jobs, invoke=stats)

        assert summary.jobs_offered == 3
        assert summary.attempted == 3
        assert summary.failed == 0
        assert stats.calls == 3
        assert len(summary.results) == 3
        assert {r.status for r in summary.results} == {"attempted"}

    @pytest.mark.asyncio
    async def test_empty_response_is_failed_not_attempted(self, monkeypatch):
        monkeypatch.setattr(ha, "CORTEX_HEADLESS_AGENTS", 1)
        monkeypatch.setattr(ha, "CORTEX_HEADLESS_CONCURRENCY", 4)
        monkeypatch.setattr(ha, "CORTEX_HEADLESS_BUDGET_SEC", 60.0)
        monkeypatch.setattr(ha, "CORTEX_HEADLESS_USD_BUDGET", 100.0)
        stats = _FakeInvokeStats()

        async def invoke(prompt: str, **kw: Any) -> ha.InvokeResult:
            return await stats(prompt, text=None, **kw)

        summary = await dd.run_distill_drain_cycle([_job()], invoke=invoke)
        assert summary.attempted == 0
        assert summary.failed == 1
        assert summary.results[0].status == "failed"

    @pytest.mark.asyncio
    async def test_prompt_reused_verbatim_plus_reminder(self, monkeypatch):
        """build_distill_prompt's text is NOT reimplemented — the job's
        own `prompt` field is forwarded unchanged, only the advisory
        no-promotion reminder is appended."""
        monkeypatch.setattr(ha, "CORTEX_HEADLESS_AGENTS", 1)
        monkeypatch.setattr(ha, "CORTEX_HEADLESS_CONCURRENCY", 4)
        monkeypatch.setattr(ha, "CORTEX_HEADLESS_BUDGET_SEC", 60.0)
        monkeypatch.setattr(ha, "CORTEX_HEADLESS_USD_BUDGET", 100.0)
        stats = _FakeInvokeStats()
        job = _job()

        await dd.run_distill_drain_cycle([job], invoke=stats)

        assert len(stats.prompts_seen) == 1
        assert stats.prompts_seen[0].startswith(job["prompt"])
        assert "lesson_promotion" in stats.prompts_seen[0]


class TestSoloModeGuard:
    @pytest.mark.asyncio
    async def test_solo_mode_skips_every_job_without_invoking(self, monkeypatch):
        """CORTEX_HEADLESS_AGENTS=0 (--safe-mode) disables MCP servers in
        the child -- remember() could never reach the DB, so no claude -p
        call is spent."""
        monkeypatch.setattr(ha, "CORTEX_HEADLESS_AGENTS", 0)
        stats = _FakeInvokeStats()
        jobs = [_job("distill-of:1"), _job("distill-of:2")]

        summary = await dd.run_distill_drain_cycle(jobs, invoke=stats)

        assert stats.calls == 0
        assert summary.jobs_offered == 2
        assert summary.skipped_solo_mode == 2
        assert summary.attempted == 0
        assert all(r.status == "skipped-solo-mode" for r in summary.results)


class TestConcurrencyAndBudget:
    @pytest.mark.asyncio
    async def test_concurrency_never_exceeds_cap(self, monkeypatch):
        monkeypatch.setattr(ha, "CORTEX_HEADLESS_AGENTS", 1)
        monkeypatch.setattr(ha, "CORTEX_HEADLESS_CONCURRENCY", 2)
        monkeypatch.setattr(ha, "CORTEX_HEADLESS_BUDGET_SEC", 60.0)
        monkeypatch.setattr(ha, "CORTEX_HEADLESS_USD_BUDGET", 100.0)
        jobs = [_job(f"distill-of:{i}") for i in range(6)]
        stats = _FakeInvokeStats()

        async def invoke(prompt: str, **kw: Any) -> ha.InvokeResult:
            return await stats(prompt, sleep=0.05, **kw)

        await dd.run_distill_drain_cycle(jobs, invoke=invoke)
        assert stats.max_concurrent <= 2

    @pytest.mark.asyncio
    async def test_usd_budget_caps_calls(self, monkeypatch):
        monkeypatch.setattr(ha, "CORTEX_HEADLESS_AGENTS", 1)
        monkeypatch.setattr(ha, "CORTEX_HEADLESS_CONCURRENCY", 1)
        monkeypatch.setattr(ha, "CORTEX_HEADLESS_BUDGET_SEC", 60.0)
        monkeypatch.setattr(ha, "CORTEX_HEADLESS_USD_BUDGET", 1.0)
        jobs = [_job(f"distill-of:{i}") for i in range(5)]
        stats = _FakeInvokeStats()

        async def invoke(prompt: str, **kw: Any) -> ha.InvokeResult:
            # Concurrency=1 -> calls are serialized; 1.0 USD cap / 0.5
            # USD per call means only the first 2 calls should land.
            return await stats(prompt, cost_per_call=0.5, sleep=0.0, **kw)

        summary = await dd.run_distill_drain_cycle(jobs, invoke=invoke)

        assert summary.skipped_budget >= 1
        assert stats.calls <= 3  # budget check happens between calls, not mid-call
        assert summary.usd_spent <= 1.5  # bounded overshoot, CycleBudget's own contract

    @pytest.mark.asyncio
    async def test_wall_clock_budget_skips_remaining(self, monkeypatch):
        monkeypatch.setattr(ha, "CORTEX_HEADLESS_AGENTS", 1)
        monkeypatch.setattr(ha, "CORTEX_HEADLESS_CONCURRENCY", 1)
        monkeypatch.setattr(ha, "CORTEX_HEADLESS_BUDGET_SEC", 0.02)
        monkeypatch.setattr(ha, "CORTEX_HEADLESS_USD_BUDGET", 100.0)
        jobs = [_job(f"distill-of:{i}") for i in range(5)]
        stats = _FakeInvokeStats()

        async def invoke(prompt: str, **kw: Any) -> ha.InvokeResult:
            return await stats(prompt, cost_per_call=0.0, sleep=0.03, **kw)

        summary = await dd.run_distill_drain_cycle(jobs, invoke=invoke)
        assert summary.skipped_budget >= 1


class TestNeverCallsLessonPromotion:
    def test_module_never_imports_lesson_promotion(self):
        """Grep-level invariant check: the contractual 'no auto-promotion,
        ever' rule (design doc, lesson_promotion.py's own docstring) means
        this module must never reference the promotion handler at all."""
        import inspect

        source = inspect.getsource(dd)
        # The only permitted mention of "lesson_promotion" is inside the
        # advisory reminder STRING appended to prompts (prose, not code)
        # -- there must be no actual `import ... lesson_promotion` statement
        # and no call reaching its handler.
        assert "import lesson_promotion" not in source
        assert "from mcp_server.handlers.lesson_promotion" not in source
        assert "lesson_promotion.handler(" not in source
