"""Adaptive batch-size controller — AIMD congestion control for batch writes.

source: ADR-0267"""

from __future__ import annotations

from dataclasses import dataclass

# source: ADR-0267

# source: ADR-0267
_MD_FACTOR = 0.5


@dataclass
class AdaptiveBatchController:
    """AIMD state machine; the SOLE owner of the live batch size ``B``.

    source: ADR-0267"""

    b_min: int
    b_max: int
    w_target_s: float
    ai_step: int = 0  # resolved to b_min in __post_init__ when left 0
    _b: int = 0

    def __post_init__(self) -> None:
        if not 0 < self.b_min <= self.b_max:
            raise ValueError(
                f"require 0 < b_min <= b_max, got {self.b_min}, {self.b_max}"
            )
        if self.w_target_s <= 0:
            raise ValueError(f"w_target_s must be positive, got {self.w_target_s}")
        if self.ai_step <= 0:
            self.ai_step = self.b_min
        self._b = self.b_min


def adaptive_batch_controller_batch_size(controller: "AdaptiveBatchController") -> int:
    """The current batch size ``B`` (b_min <= B <= b_max).

    source: ADR-0267"""
    return controller._b


def adaptive_batch_controller_observe(
    controller: "AdaptiveBatchController", latency_s: float
) -> int:
    """Update B from one observed batch-write latency; return the new B.

    source: ADR-0267"""
    if latency_s <= controller.w_target_s:
        controller._b = min(controller.b_max, controller._b + controller.ai_step)
    else:
        controller._b = max(controller.b_min, int(controller._b * _MD_FACTOR))
    assert (
        controller.b_min <= controller._b <= controller.b_max
    )  # invariant (precond 4)
    return controller._b
