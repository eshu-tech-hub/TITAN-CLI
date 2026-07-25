from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from titan.recovery.exceptions import RecoveryStateError
from titan.recovery.models import RuntimeStateSnapshot

StateCaptureFunc = Callable[[], Mapping[str, Any]]


@dataclass(slots=True)
class StateManager:
    _capture_funcs: dict[str, StateCaptureFunc] = field(
        default_factory=dict, init=False
    )
    _restore_funcs: dict[str, Callable[[Mapping[str, Any]], None]] = field(
        default_factory=dict, init=False
    )
    _lock: Lock = field(default_factory=Lock, init=False)
    _last_snapshot: RuntimeStateSnapshot | None = None

    def register_capture(self, key: str, func: StateCaptureFunc) -> None:
        with self._lock:
            self._capture_funcs[key] = func

    def register_restore(
        self, key: str, func: Callable[[Mapping[str, Any]], None]
    ) -> None:
        with self._lock:
            self._restore_funcs[key] = func

    def unregister(self, key: str) -> None:
        with self._lock:
            self._capture_funcs.pop(key, None)
            self._restore_funcs.pop(key, None)

    def capture(self) -> RuntimeStateSnapshot:
        captured: dict[str, Any] = {}
        errors: list[str] = []

        with self._lock:
            funcs = dict(self._capture_funcs)

        for key, func in funcs.items():
            try:
                captured[key] = func()
            except Exception as exc:
                errors.append(f"{key}: {exc}")

        snapshot = RuntimeStateSnapshot(
            pipeline_progress=captured.get("pipeline_progress", {}),
            current_stage=captured.get("current_stage", ""),
            open_orders=tuple(captured.get("open_orders", [])),
            portfolio_snapshot=captured.get("portfolio_snapshot", {}),
            runtime_config=captured.get("runtime_config", {}),
            monitoring_status=captured.get("monitoring_status", {}),
            captured_at=datetime.now(timezone.utc),
        )

        with self._lock:
            self._last_snapshot = snapshot

        if errors:
            raise RecoveryStateError(f"Partial state capture: {'; '.join(errors)}")

        return snapshot

    def restore(self, snapshot: RuntimeStateSnapshot | None = None) -> None:
        target = snapshot or self._last_snapshot
        if target is None:
            raise RecoveryStateError("No snapshot available to restore")

        errors: list[str] = []

        with self._lock:
            funcs = dict(self._restore_funcs)

        for key, func in funcs.items():
            data = getattr(target, key, None)
            if data is not None:
                try:
                    func(data)
                except Exception as exc:
                    errors.append(f"{key}: {exc}")

        if errors:
            raise RecoveryStateError(f"Partial state restore: {'; '.join(errors)}")

    @property
    def last_snapshot(self) -> RuntimeStateSnapshot | None:
        return self._last_snapshot

    def clear(self) -> None:
        with self._lock:
            self._capture_funcs.clear()
            self._restore_funcs.clear()
            self._last_snapshot = None
