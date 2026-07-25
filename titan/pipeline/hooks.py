from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from titan.pipeline.models import PipelineReport
from titan.pipeline.stages import PipelineStage


@dataclass(slots=True)
class PipelineHooks:
    """Hook points for pipeline lifecycle events.

    All hooks are no-op by default. Override individual hooks
    for metrics, logging, notifications, or dashboard updates.
    """

    before_stage: Callable[[PipelineStage, Any], None] | None = None
    after_stage: Callable[[PipelineStage, Any, Any, float], None] | None = None
    on_error: Callable[[PipelineStage, Any, Exception], None] | None = None
    on_retry: Callable[[PipelineStage, Any, Exception, int], None] | None = None
    on_abort: Callable[[Any], None] | None = None
    on_complete: Callable[[Any, PipelineReport], None] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def run_before_stage(self, stage: PipelineStage, context: Any) -> None:
        if self.before_stage is not None:
            self.before_stage(stage, context)

    def run_after_stage(
        self, stage: PipelineStage, context: Any, result: Any, duration_ms: float
    ) -> None:
        if self.after_stage is not None:
            self.after_stage(stage, context, result, duration_ms)

    def run_on_error(
        self, stage: PipelineStage, context: Any, error: Exception
    ) -> None:
        if self.on_error is not None:
            self.on_error(stage, context, error)

    def run_on_retry(
        self, stage: PipelineStage, context: Any, error: Exception, attempt: int
    ) -> None:
        if self.on_retry is not None:
            self.on_retry(stage, context, error, attempt)

    def run_on_abort(self, context: Any) -> None:
        if self.on_abort is not None:
            self.on_abort(context)

    def run_on_complete(self, context: Any, report: PipelineReport) -> None:
        if self.on_complete is not None:
            self.on_complete(context, report)
