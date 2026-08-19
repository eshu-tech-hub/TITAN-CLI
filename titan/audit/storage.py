from __future__ import annotations

import json
import threading
from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path

from titan.audit.exceptions import StorageError
from titan.audit.models import AuditEvent


class AuditStorage(ABC):
    """Abstract interface for audit event persistence."""

    @abstractmethod
    def append(self, event: AuditEvent) -> None:
        """Persist a single audit event.  Must never delete or modify."""

    @abstractmethod
    def append_batch(self, events: Sequence[AuditEvent]) -> None:
        """Persist a batch of audit events atomically."""

    @abstractmethod
    def load_all(self) -> list[AuditEvent]:
        """Return all stored events in sequence order."""

    @abstractmethod
    def count(self) -> int:
        """Return the number of stored events."""

    @abstractmethod
    def clear(self) -> None:
        """Remove all stored events.  Used only in testing."""


class InMemoryAuditStorage(AuditStorage):
    """Thread-safe in-memory audit storage.

    Suitable for testing, development, and short-lived sessions.
    """

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []
        self._lock = threading.Lock()

    def append(self, event: AuditEvent) -> None:
        with self._lock:
            self._events.append(event)

    def append_batch(self, events: Sequence[AuditEvent]) -> None:
        with self._lock:
            self._events.extend(events)

    def load_all(self) -> list[AuditEvent]:
        with self._lock:
            return list(self._events)

    def count(self) -> int:
        with self._lock:
            return len(self._events)

    def clear(self) -> None:
        with self._lock:
            self._events.clear()


class JsonLinesAuditStorage(AuditStorage):
    """Persistent audit storage using JSON Lines (JSONL) format.

    Each line is a self-contained JSON object representing one AuditEvent.
    The file is append-only by design; no line is ever removed or modified.
    """

    def __init__(self, file_path: str | Path) -> None:
        self._path = Path(file_path)
        self._lock = threading.Lock()
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            if not self._path.exists():
                self._path.touch()
        except OSError as exc:
            raise StorageError(
                f"Failed to initialise JSONL storage at {self._path}: {exc}"
            ) from exc

    def append(self, event: AuditEvent) -> None:
        line = json.dumps(event.to_dict(), default=str) + "\n"
        with self._lock:
            try:
                with self._path.open("a", encoding="utf-8") as fh:
                    fh.write(line)
            except OSError as exc:
                raise StorageError(
                    f"Failed to append event {event.event_id}: {exc}"
                ) from exc

    def append_batch(self, events: Sequence[AuditEvent]) -> None:
        lines = [json.dumps(e.to_dict(), default=str) + "\n" for e in events]
        with self._lock:
            try:
                with self._path.open("a", encoding="utf-8") as fh:
                    fh.writelines(lines)
            except OSError as exc:
                raise StorageError(f"Failed to append batch: {exc}") from exc

    def load_all(self) -> list[AuditEvent]:
        with self._lock:
            return self._read_all()

    def count(self) -> int:
        with self._lock:
            return self._count_lines()

    def clear(self) -> None:
        with self._lock:
            try:
                self._path.write_text("", encoding="utf-8")
            except OSError as exc:
                raise StorageError(f"Failed to clear storage: {exc}") from exc

    def _read_all(self) -> list[AuditEvent]:
        events: list[AuditEvent] = []
        try:
            with self._path.open("r", encoding="utf-8") as fh:
                for line_no, line in enumerate(fh, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        events.append(AuditEvent.from_dict(data))
                    except (json.JSONDecodeError, KeyError, ValueError) as exc:
                        raise StorageError(
                            f"Corrupt line {line_no} in {self._path}: {exc}"
                        ) from exc
        except OSError as exc:
            raise StorageError(f"Failed to read {self._path}: {exc}") from exc
        return events

    def _count_lines(self) -> int:
        try:
            count = 0
            with self._path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        count += 1
            return count
        except OSError as exc:
            raise StorageError(
                f"Failed to count events in {self._path}: {exc}"
            ) from exc
