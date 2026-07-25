from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from titan.recovery.exceptions import RecoveryCheckpointError
from titan.recovery.models import Checkpoint, ComponentType


@dataclass(slots=True)
class CheckpointManager:
    _checkpoints: dict[str, Checkpoint] = field(default_factory=dict, init=False)
    _lock: Lock = field(default_factory=Lock, init=False)

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
            created_at=datetime.now(timezone.utc),
            metadata=dict(metadata) if metadata else {},
        )
        with self._lock:
            self._checkpoints[checkpoint_id] = checkpoint
        return checkpoint

    def load(self, checkpoint_id: str) -> Checkpoint:
        with self._lock:
            cp = self._checkpoints.get(checkpoint_id)
            if cp is None:
                raise RecoveryCheckpointError(f"Checkpoint not found: {checkpoint_id}")
            return cp

    def delete(self, checkpoint_id: str) -> None:
        with self._lock:
            if checkpoint_id not in self._checkpoints:
                raise RecoveryCheckpointError(f"Checkpoint not found: {checkpoint_id}")
            del self._checkpoints[checkpoint_id]

    def list_by_component(self, component: ComponentType) -> tuple[Checkpoint, ...]:
        with self._lock:
            return tuple(
                cp for cp in self._checkpoints.values() if cp.component == component
            )

    def list_all(self) -> tuple[Checkpoint, ...]:
        with self._lock:
            return tuple(self._checkpoints.values())

    def count(self) -> int:
        with self._lock:
            return len(self._checkpoints)

    def clear(self) -> None:
        with self._lock:
            self._checkpoints.clear()

    def latest(self, component: ComponentType) -> Checkpoint | None:
        candidates = self.list_by_component(component)
        if not candidates:
            return None
        return max(candidates, key=lambda cp: cp.created_at)
