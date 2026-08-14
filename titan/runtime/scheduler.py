from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Event, Lock, Thread, current_thread
from typing import Any, Callable
from uuid import uuid4
from titan.core.logger import logger

from titan.runtime.events import RuntimeEventBus
from titan.runtime.exceptions import SchedulerError
from titan.runtime.models import RuntimeEventType

PipelineRunner = Callable[..., Any]
@dataclass(slots=True)
class PipelineScheduler:
    """Schedules pipeline execution on a periodic or event-driven basis.

    Supports configurable intervals, market schedule awareness,
    and dynamic start/stop control. Runs in a dedicated, lifecycle-managed
    worker so periodic execution remains available without a foreground loop.

    Attributes:
        event_bus: Event bus for publishing scheduler events.
        runner: Callable that executes the pipeline.
        interval_seconds: Seconds between periodic pipeline runs.
        _paused: Whether the scheduler is paused.
        _execution_count: Total pipeline executions.
        _last_execution_time: When the pipeline last ran.
    """

    event_bus: RuntimeEventBus | None = None
    runner: PipelineRunner | None = None
    interval_seconds: float = 60.0
    _active: bool = field(default=False, init=False)
    _paused: bool = field(default=False, init=False)
    _execution_count: int = field(default=0, init=False)
    _last_execution_time: datetime | None = field(default=None, init=False)
    _execution_lock: Lock = field(default_factory=Lock, init=False)
    _stop_event: Event = field(default_factory=Event, init=False)
    _worker: Thread | None = field(default=None, init=False)

    def start(self) -> None:
        """Activate the scheduler.

        Raises:
            SchedulerError: If the scheduler is already active.
        """
        if self._active:
            raise SchedulerError("Scheduler is already active.")
        if self.runner is None:
            raise SchedulerError("No pipeline runner configured.")
        if self.interval_seconds <= 0:
            raise SchedulerError("Scheduler interval must be positive.")

        self._active = True
        self._paused = False
        self._stop_event.clear()
        self._worker = Thread(
            target=self._run,
            name="pipeline-scheduler",
        )
        self._worker.start()

    def stop(self) -> None:
        """Deactivate the scheduler."""
        self._active = False
        self._paused = False
        self._stop_event.set()
        if self._worker is not None and self._worker is not current_thread():
            self._worker.join(timeout=5.0)
            if self._worker.is_alive():
                raise SchedulerError("Scheduler worker did not stop within five seconds.")
        self._worker = None

    @property
    def is_active(self) -> bool:
        """Whether the scheduler is active."""
        return self._active

    @property
    def is_running(self) -> bool:
        """For compatibility with CLI and other tools."""
        return self._active and self._worker is not None and self._worker.is_alive()

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def execution_count(self) -> int:
        return self._execution_count

    @property
    def last_execution_time(self) -> datetime | None:
        return self._last_execution_time

    def pause(self) -> None:
        if not self.is_active:
            raise SchedulerError("Cannot pause: scheduler is not active.")
        self._paused = True

    def resume(self) -> None:
        if not self.is_active:
            raise SchedulerError("Cannot resume: scheduler is not active.")
        self._paused = False

    def tick(self) -> None:
        """Evaluate whether the pipeline should run based on the interval."""
        if not self._active or self._paused:
            return

        now = datetime.now(timezone.utc)
        if self._last_execution_time is None:
            self._run_pipeline()
            return

        elapsed = (now - self._last_execution_time).total_seconds()
        if elapsed >= self.interval_seconds:
            self._run_pipeline()

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.tick()
            except Exception as exc:
                logger.exception(f"Pipeline scheduler worker failed: {exc}")
            self._stop_event.wait(timeout=min(self.interval_seconds, 0.1))

    def execute_once(self) -> Any:
        if self.runner is None:
            raise SchedulerError("No pipeline runner configured.")
        return self._run_pipeline()

    def _run_pipeline(self) -> Any:
        """Execute the pipeline and publish events."""
        if not self._execution_lock.acquire(blocking=False):
            if self.event_bus is not None:
                self.event_bus.publish_type(
                    RuntimeEventType.SCHEDULER_ERROR,
                    "scheduler",
                    data={"error": "Pipeline execution skipped due to overlap"},
                )
            raise SchedulerError("Execution overlap prevented.")

        try:
            execution_id = str(uuid4())
            logger.info(f"Pipeline started: {execution_id}")

            if self.event_bus is not None:
                self.event_bus.publish_type(
                    RuntimeEventType.SCHEDULER_PIPELINE_STARTED,
                    "scheduler",
                    data={"execution_id": execution_id},
                )

            try:
                result = self.runner() if self.runner else None
                self._execution_count += 1
                self._last_execution_time = datetime.now(timezone.utc)
                logger.info(f"Pipeline completed: {execution_id}")

                if self.event_bus is not None:
                    self.event_bus.publish_type(
                        RuntimeEventType.SCHEDULER_PIPELINE_COMPLETED,
                        "scheduler",
                        data={
                            "execution_id": execution_id,
                            "count": self._execution_count,
                        },
                    )

                return result

            except Exception as e:
                if self.event_bus is not None:
                    self.event_bus.publish_type(
                        RuntimeEventType.SCHEDULER_PIPELINE_FAILED,
                        "scheduler",
                        data={
                            "execution_id": execution_id,
                            "error": str(e),
                        },
                    )
                raise
        finally:
            self._execution_lock.release()
