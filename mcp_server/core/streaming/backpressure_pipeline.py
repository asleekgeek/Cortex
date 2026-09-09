"""Backpressure pipeline — bounded-queue producer/consumer with constant peak RAM.

source: ADR-0269
"""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass, field
from typing import Any, Callable

from mcp_server.core.streaming.ports import BatchSink, StreamSource


@dataclass
class PipelineResult:
    """Outcome of one pipeline run (mutated under a lock by all threads)."""

    rows_in: int = 0
    rows_written: int = 0
    batches: int = 0
    errors: list[str] = field(default_factory=list)


class _Sentinel:
    """Poison pill — one is enqueued per worker to signal end-of-stream."""


_SENTINEL = _Sentinel()


def compute_queue_cap(
    ram_budget_bytes: int, b_max: int, row_bytes: int, reserve: int = 1
) -> int:
    """``Q_cap = floor(RAM_budget / (b_max * row_bytes)) - reserve``.

    source: ADR-0269"""
    if b_max <= 0 or row_bytes <= 0:
        raise ValueError("b_max and row_bytes must be positive")
    if ram_budget_bytes <= 0:
        raise ValueError("ram_budget_bytes must be positive")
    cap = ram_budget_bytes // (b_max * row_bytes) - reserve
    return max(1, cap)


@dataclass
class BackpressurePipeline:
    """Runs ``source -> bounded queue -> c x sink`` with bounded peak RAM.

    ``sink_factory`` builds ONE sink per worker — each worker owns its own
    connection (sharing a connection across threads is unsafe). The factory is
    injected by the handler (composition root) and binds the appropriate pool.

    source: ADR-0269"""

    source: StreamSource
    sink_factory: Callable[[], BatchSink]
    max_batch: int
    queue_cap: int
    concurrency: int = 2


def backpressure_pipeline_run(pipeline: "BackpressurePipeline") -> PipelineResult:
    """Drain the source through the workers; block until fully flushed.

    Postcondition: on return, every row the source yielded has been handed
    to a sink and durably committed (the staged barrier later phases rely
    on) OR surfaced in ``result.errors``.
    """
    q: queue.Queue[Any] = queue.Queue(maxsize=pipeline.queue_cap)
    result = PipelineResult()
    lock = threading.Lock()
    # source: ADR-0269

    producer = threading.Thread(
        target=_bp_produce, args=(pipeline, q, result, lock), name="bp-producer"
    )
    workers = [
        threading.Thread(
            target=_bp_consume, args=(pipeline, q, result, lock), name=f"bp-worker-{i}"
        )
        for i in range(pipeline.concurrency)
    ]
    producer.start()
    for w in workers:
        w.start()
    producer.join()
    for w in workers:
        w.join()
    return result


def _bp_produce(
    pipeline: "BackpressurePipeline",
    q: "queue.Queue[Any]",
    result: PipelineResult,
    lock: threading.Lock,
) -> None:
    try:
        for batch in pipeline.source.stream(pipeline.max_batch):
            q.put(batch)  # source: ADR-0269
            with lock:
                result.rows_in += len(batch)
                result.batches += 1
    except Exception as exc:  # noqa: BLE001 — source: ADR-0269
        with lock:
            result.errors.append(f"producer: {exc!r}")
    finally:
        # source: ADR-0269

        for _ in range(pipeline.concurrency):
            q.put(_SENTINEL)


def _bp_consume(
    pipeline: "BackpressurePipeline",
    q: "queue.Queue[Any]",
    result: PipelineResult,
    lock: threading.Lock,
) -> None:
    sink = _bp_build_sink(pipeline, result, lock)
    try:
        while True:
            item = q.get()
            if item is _SENTINEL:
                return  # consumed our one sentinel — stop
            if sink is None:
                continue  # setup failed; drain to our sentinel, don't hang
            _bp_write_one(sink, item, result, lock)
    finally:
        if sink is not None:
            _bp_close(sink, result, lock)


def _bp_build_sink(
    pipeline: "BackpressurePipeline", result: PipelineResult, lock: threading.Lock
) -> BatchSink | None:
    try:
        return pipeline.sink_factory()
    except Exception as exc:  # noqa: BLE001
        with lock:
            result.errors.append(f"worker-setup: {exc!r}")
        return None


def _bp_write_one(
    sink: BatchSink,
    item: list[Any],
    result: PipelineResult,
    lock: threading.Lock,
) -> None:
    try:
        written = sink.write_batch(item)
        with lock:
            result.rows_written += written
    except Exception as exc:  # noqa: BLE001
        with lock:
            result.errors.append(f"worker: {exc!r}")


def _bp_close(sink: BatchSink, result: PipelineResult, lock: threading.Lock) -> None:
    try:
        sink.close()
    except Exception as exc:  # noqa: BLE001
        with lock:
            result.errors.append(f"worker-close: {exc!r}")
