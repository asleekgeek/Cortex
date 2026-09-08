"""Constant-memory streaming pipeline — ports and pure orchestration.

source: ADR-0266"""

from __future__ import annotations

from mcp_server.core.streaming.adaptive_controller import (
    AdaptiveBatchController,
    adaptive_batch_controller_batch_size,
    adaptive_batch_controller_observe,
)
from mcp_server.core.streaming.backpressure_pipeline import (
    BackpressurePipeline,
    PipelineResult,
    backpressure_pipeline_run,
    compute_queue_cap,
)
from mcp_server.core.streaming.ports import BatchSink, StreamSource

__all__ = [
    "AdaptiveBatchController",
    "adaptive_batch_controller_batch_size",
    "adaptive_batch_controller_observe",
    "BackpressurePipeline",
    "PipelineResult",
    "backpressure_pipeline_run",
    "compute_queue_cap",
    "BatchSink",
    "StreamSource",
]
