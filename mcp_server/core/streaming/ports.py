"""Streaming pipeline ports — producer/consumer contracts.

source: ADR-0271"""

from __future__ import annotations

from typing import Iterator, Protocol, TypeVar, runtime_checkable

T = TypeVar("T")


@runtime_checkable
class StreamSource(Protocol[T]):
    """A bounded-batch producer.

    source: ADR-0271"""

    def stream(self, max_batch: int) -> Iterator[list[T]]:
        """Yield successive batches of at most ``max_batch`` items."""
        ...


@runtime_checkable
class BatchSink(Protocol[T]):
    """A batch consumer that durably writes one batch and releases it.

    Contract:
      - On normal return from ``write_batch``, every row in ``batch`` is
        durably committed and the underlying connection holds NO open
        transaction (commit state must not leak across the abstraction).
      - The sink MUST NOT retain references to rows after return — one batch
        in, one batch written, one batch's worth of RAM.
      - On failure ``write_batch`` raises; the batch is rolled back atomically
        (all-or-nothing). Under ``autocommit=True`` this requires the adapter
        to wrap the write in an explicit ``with conn.transaction():``.
      - ``write_batch`` returns the number of rows persisted; after dedup /
        ``ON CONFLICT DO NOTHING`` this may be smaller than ``len(batch)``.
    """

    def write_batch(self, batch: list[T]) -> int:
        """Durably write ``batch``; return the count persisted."""
        ...

    def close(self) -> None:
        """Release any borrowed resource (e.g. return a pooled connection).

        Idempotent — safe to call once per sink after its worker finishes.
        """
        ...
