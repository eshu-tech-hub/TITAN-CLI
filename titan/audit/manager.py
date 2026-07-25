from __future__ import annotations

import threading
from typing import Any

from titan.audit.event import create_audit_event, validate_event
from titan.audit.exceptions import EventValidationError
from titan.audit.integrity import IntegrityEngine, IntegrityReport
from titan.audit.models import (
    AuditCategory,
    AuditEvent,
    AuditReport,
    AuditResult,
    AuditSeverity,
    AuditSource,
)
from titan.audit.query import AuditQuery, AuditQueryEngine
from titan.audit.storage import AuditStorage, InMemoryAuditStorage


class AuditManager:
    """Single authority for all TITAN audit records.

    Every subsystem must route audit events through this manager.
    No subsystem may write audit records directly.

    Responsibilities:
        - Receive audit events from any TITAN subsystem.
        - Validate events before persistence.
        - Assign monotonically increasing sequence numbers.
        - Compute and verify hash chains.
        - Persist events via the configured storage backend.
        - Generate audit reports.
        - Provide query access through :class:`AuditQueryEngine`.
    """

    def __init__(self, storage: AuditStorage | None = None) -> None:
        self._storage: AuditStorage = storage or InMemoryAuditStorage()
        self._integrity = IntegrityEngine()
        self._query_engine = AuditQueryEngine(self._storage)
        self._sequence_counter = 0
        self._last_hash = ""
        self._lock = threading.Lock()

    # ── Core recording ──

    def record(
        self,
        *,
        source: AuditSource,
        category: AuditCategory,
        severity: AuditSeverity,
        action: str,
        result: AuditResult = AuditResult.SUCCESS,
        correlation_id: str = "",
        pipeline_id: str = "",
        trade_id: str = "",
        order_id: str = "",
        position_id: str = "",
        runtime_id: str = "",
        user_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """Record a single audit event.

        Assigns sequence number, computes hash chain, validates, and
        persists the event.  Returns the fully hydrated :class:`AuditEvent`.
        """
        with self._lock:
            seq = self._sequence_counter + 1
            prev = self._last_hash

        event = create_audit_event(
            source=source,
            category=category,
            severity=severity,
            action=action,
            result=result,
            sequence_number=seq,
            correlation_id=correlation_id,
            pipeline_id=pipeline_id,
            trade_id=trade_id,
            order_id=order_id,
            position_id=position_id,
            runtime_id=runtime_id,
            user_id=user_id,
            previous_hash=prev,
            metadata=metadata,
        )

        errors = validate_event(event)
        if errors:
            raise EventValidationError(f"Event validation failed: {'; '.join(errors)}")

        with self._lock:
            self._sequence_counter = seq
            self._last_hash = event.event_hash

        self._storage.append(event)
        return event

    def record_batch(
        self,
        events: list[dict[str, Any]],
    ) -> list[AuditEvent]:
        """Record multiple audit events in a single batch.

        Each dict must contain at minimum: source, category, severity, action.
        Sequence numbers and hash chain are assigned automatically.
        """
        recorded: list[AuditEvent] = []
        for raw in events:
            event = self.record(
                source=AuditSource(raw["source"]),
                category=AuditCategory(raw["category"]),
                severity=AuditSeverity(raw["severity"]),
                action=raw["action"],
                result=AuditResult(raw.get("result", "success")),
                correlation_id=raw.get("correlation_id", ""),
                pipeline_id=raw.get("pipeline_id", ""),
                trade_id=raw.get("trade_id", ""),
                order_id=raw.get("order_id", ""),
                position_id=raw.get("position_id", ""),
                runtime_id=raw.get("runtime_id", ""),
                user_id=raw.get("user_id", ""),
                metadata=raw.get("metadata"),
            )
            recorded.append(event)
        return recorded

    # ── Query access ──

    @property
    def query(self) -> AuditQueryEngine:
        """Access the query engine for searching persisted events."""
        return self._query_engine

    def search(self, audit_query: AuditQuery) -> list[AuditEvent]:
        """Shorthand for :meth:`AuditQueryEngine.query`."""
        return self._query_engine.query(audit_query)

    # ── Integrity ──

    def verify_integrity(self) -> IntegrityReport:
        """Verify the full hash chain of all stored events."""
        events = self._storage.load_all()
        return self._integrity.verify(events)

    # ── Reporting ──

    def generate_report(self) -> AuditReport:
        """Generate a summary report of all audit events."""
        events = self._storage.load_all()
        total = len(events)

        if total == 0:
            return AuditReport(
                total_events=0,
                integrity_status="empty",
            )

        by_source: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        by_category: dict[str, int] = {}

        for event in events:
            by_source[event.source.value] = by_source.get(event.source.value, 0) + 1
            by_severity[event.severity.value] = (
                by_severity.get(event.severity.value, 0) + 1
            )
            by_category[event.category.value] = (
                by_category.get(event.category.value, 0) + 1
            )

        integrity = self.verify_integrity()
        first_ts = events[0].timestamp if events else None
        last_ts = events[-1].timestamp if events else None
        seq_first = events[0].sequence_number if events else 0
        seq_last = events[-1].sequence_number if events else 0

        return AuditReport(
            total_events=total,
            events_by_source=by_source,
            events_by_severity=by_severity,
            events_by_category=by_category,
            integrity_status="valid" if integrity.is_valid else "compromised",
            verification_failures=integrity.violation_count,
            first_event_time=first_ts,
            last_event_time=last_ts,
            sequence_range=(seq_first, seq_last),
        )

    # ── Accessors ──

    @property
    def event_count(self) -> int:
        return self._storage.count()

    @property
    def sequence_counter(self) -> int:
        with self._lock:
            return self._sequence_counter

    @property
    def last_hash(self) -> str:
        with self._lock:
            return self._last_hash

    @property
    def storage(self) -> AuditStorage:
        return self._storage
