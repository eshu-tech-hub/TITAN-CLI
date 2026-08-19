from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from typing import Any

from titan.recovery.exceptions import RecoveryCheckpointError
from titan.recovery.models import Checkpoint, ComponentType


@dataclass(slots=True)
class CheckpointManager:
    _checkpoints: dict[str, tuple[int, Checkpoint]] = field(
        default_factory=dict, init=False
    )
    _lock: Lock = field(default_factory=Lock, init=False)
    _counter: int = field(default=0, init=False)

    def save(
        self,
        checkpoint_id: str,
        component: ComponentType,
        state_data: Mapping[str, Any],
        version: str = "1.0.0",
        metadata: Mapping[str, Any] | None = None,
    ) -> Checkpoint:
        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            component=component,
            state_data=dict(state_data),
            version=version,
            created_at=datetime.now(UTC),
            metadata=dict(metadata) if metadata else {},
        )
        with self._lock:
            self._counter += 1
            self._checkpoints[checkpoint_id] = (self._counter, checkpoint)
        return checkpoint

    def load(self, checkpoint_id: str) -> Checkpoint:
        with self._lock:
            cp_tuple = self._checkpoints.get(checkpoint_id)
            if cp_tuple is None:
                raise RecoveryCheckpointError(f"Checkpoint not found: {checkpoint_id}")
            return cp_tuple[1]

    def delete(self, checkpoint_id: str) -> None:
        with self._lock:
            if checkpoint_id not in self._checkpoints:
                raise RecoveryCheckpointError(f"Checkpoint not found: {checkpoint_id}")
            del self._checkpoints[checkpoint_id]

    def list_by_component(self, component: ComponentType) -> tuple[Checkpoint, ...]:
        with self._lock:
            return tuple(
                cp for _, cp in self._checkpoints.values() if cp.component == component
            )

    def list_all(self) -> tuple[Checkpoint, ...]:
        with self._lock:
            return tuple(cp for _, cp in self._checkpoints.values())

    def count(self) -> int:
        with self._lock:
            return len(self._checkpoints)

    def clear(self) -> None:
        with self._lock:
            self._checkpoints.clear()

    def latest(self, component: ComponentType) -> Checkpoint | None:
        with self._lock:
            matches = [
                (counter, cp)
                for counter, cp in self._checkpoints.values()
                if cp.component == component
            ]
        if not matches:
            return None
        return max(matches, key=lambda t: (t[1].created_at, t[0]))[1]
