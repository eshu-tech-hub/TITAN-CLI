from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Mapping

from titan.pipeline.stages import PipelineStage


class PipelineStatus(str, Enum):
    """Final status of a pipeline execution."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    ABORTED = "aborted"


@dataclass(frozen=True, slots=True)
class StageTiming:
    """Timing and result information for a single pipeline stage."""

    stage: PipelineStage
    start_time: datetime
    end_time: datetime
    duration_ms: float
    success: bool
    error: str | None = None

    @property
    def duration_s(self) -> float:
        return self.duration_ms / 1000.0


@dataclass(frozen=True, slots=True)
class PipelineReport:
    """Complete report generated after pipeline execution."""

    pipeline_id: str
    symbol: str
    exchange: str
    status: PipelineStatus
    stages: tuple[StageTiming, ...]
    evidence_count: int
    decision_action: str | None
    orders_submitted: int
    orders_accepted: int
    orders_rejected: int
    broker_order_ids: tuple[str, ...]
    execution_result: str | None
    warnings: tuple[str, ...]
    errors: tuple[str, ...]
    start_time: datetime
    end_time: datetime
    total_duration_ms: float
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def total_duration_s(self) -> float:
        return self.total_duration_ms / 1000.0

    @property
    def success(self) -> bool:
        return self.status == PipelineStatus.SUCCESS

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0
