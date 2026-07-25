from collections.abc import Callable
from dataclasses import dataclass, field
from threading import Lock

from titan.recovery.models import (
    ComponentType,
    RecoveryStatus,
)

HealthCheckFunc = Callable[[], bool]
RecoveryTrigger = Callable[[ComponentType, str], RecoveryStatus]


@dataclass(slots=True)
class HealthRecovery:
    _recovery_trigger: RecoveryTrigger | None = None
    _auto_recovery_enabled: bool = True
    _health_checks: dict[str, tuple[HealthCheckFunc, ComponentType]] = field(
        default_factory=dict, init=False
    )
    _recovery_history: dict[str, RecoveryStatus] = field(
        default_factory=dict, init=False
    )
    _lock: Lock = field(default_factory=Lock, init=False)

    @property
    def auto_recovery_enabled(self) -> bool:
        return self._auto_recovery_enabled

    def set_auto_recovery(self, enabled: bool) -> None:
        with self._lock:
            self._auto_recovery_enabled = enabled

    def set_recovery_trigger(self, trigger: RecoveryTrigger) -> None:
        with self._lock:
            self._recovery_trigger = trigger

    def register_health_check(
        self,
        check_id: str,
        check_func: HealthCheckFunc,
        component: ComponentType,
    ) -> None:
        with self._lock:
            self._health_checks[check_id] = (check_func, component)

    def unregister_health_check(self, check_id: str) -> None:
        with self._lock:
            self._health_checks.pop(check_id, None)

    def run_health_checks(self) -> dict[str, bool]:
        with self._lock:
            checks = dict(self._health_checks)

        results: dict[str, bool] = {}
        failures: list[str] = []

        for check_id, (check_func, component) in checks.items():
            try:
                healthy = check_func()
            except Exception:
                healthy = False
            results[check_id] = healthy

            if not healthy:
                failures.append(check_id)
                if self._auto_recovery_enabled:
                    self._attempt_auto_recovery(check_id, component)

        return results

    def _attempt_auto_recovery(self, check_id: str, component: ComponentType) -> None:
        trigger = self._recovery_trigger
        if trigger is None:
            return

        try:
            status = trigger(component, f"Health check failed: {check_id}")
            with self._lock:
                self._recovery_history[check_id] = status
        except Exception:
            with self._lock:
                self._recovery_history[check_id] = RecoveryStatus.FAILED

    def get_recovery_history(
        self, check_id: str | None = None
    ) -> dict[str, RecoveryStatus]:
        with self._lock:
            if check_id is not None:
                return (
                    {check_id: self._recovery_history[check_id]}
                    if check_id in self._recovery_history
                    else {}
                )
            return dict(self._recovery_history)

    def clear_history(self) -> None:
        with self._lock:
            self._recovery_history.clear()

    def reset(self) -> None:
        with self._lock:
            self._health_checks.clear()
            self._recovery_history.clear()
            self._recovery_trigger = None
            self._auto_recovery_enabled = True
