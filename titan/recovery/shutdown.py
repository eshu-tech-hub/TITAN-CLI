from collections.abc import Callable
from dataclasses import dataclass, field
from threading import Lock
from time import monotonic

from titan.recovery.exceptions import RecoveryShutdownError
from titan.recovery.models import ShutdownPlan, ShutdownStage

ShutdownHook = Callable[[], None]


@dataclass(slots=True)
class GracefulShutdown:
    _plan: ShutdownPlan = field(default_factory=ShutdownPlan)
    _hooks: dict[ShutdownStage, list[ShutdownHook]] = field(
        default_factory=dict, init=False
    )
    _current_stage: ShutdownStage = ShutdownStage.NOT_STARTED
    _lock: Lock = field(default_factory=Lock, init=False)

    @property
    def plan(self) -> ShutdownPlan:
        return self._plan

    @property
    def current_stage(self) -> ShutdownStage:
        return self._current_stage

    def register_hook(self, stage: ShutdownStage, hook: ShutdownHook) -> None:
        with self._lock:
            if stage not in self._hooks:
                self._hooks[stage] = []
            self._hooks[stage].append(hook)

    def unregister_hook(self, stage: ShutdownStage, hook: ShutdownHook) -> None:
        with self._lock:
            if stage in self._hooks:
                self._hooks[stage] = [h for h in self._hooks[stage] if h is not hook]

    def execute(self) -> None:
        stages = [
            ShutdownStage.STOPPING_PIPELINE,
            ShutdownStage.CANCELLING_WORKERS,
            ShutdownStage.FLUSHING_LOGS,
            ShutdownStage.PERSISTING_CHECKPOINTS,
            ShutdownStage.CLOSING_BROKER,
            ShutdownStage.RELEASING_RESOURCES,
        ]

        start = monotonic()

        for stage in stages:
            with self._lock:
                self._current_stage = stage

            elapsed = monotonic() - start
            if elapsed >= self._plan.force_timeout_seconds:
                raise RecoveryShutdownError(
                    f"Shutdown timed out at stage {stage.value} "
                    f"after {self._plan.force_timeout_seconds}s"
                )

            self._execute_stage(stage)

        with self._lock:
            self._current_stage = ShutdownStage.COMPLETED

    def _execute_stage(self, stage: ShutdownStage) -> None:
        hooks = list(self._hooks.get(stage, []))
        deadline = monotonic() + self._plan.timeout_per_stage
        errors: list[str] = []

        for hook in hooks:
            if monotonic() >= deadline:
                errors.append(
                    f"Stage {stage.value} timed out after {self._plan.timeout_per_stage}s"
                )
                break
            try:
                hook()
            except Exception as exc:
                errors.append(f"{stage.value}: {exc}")

        if errors:
            raise RecoveryShutdownError(
                f"Shutdown stage {stage.value} failed: {'; '.join(errors)}"
            )

    def abort(self) -> None:
        with self._lock:
            self._current_stage = ShutdownStage.NOT_STARTED

    def reset(self) -> None:
        with self._lock:
            self._current_stage = ShutdownStage.NOT_STARTED
            self._hooks.clear()
