from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from titan.audit.models import (
    AuditCategory,
    AuditEvent,
    AuditSeverity,
    AuditSource,
)
from titan.audit.storage import AuditStorage


@dataclass(frozen=True, slots=True)
class AuditQuery:
    """Declarative filter for querying audit events.

    All fields are optional.  Only non-default fields are applied as
    filters.  Multiple fields are combined with AND logic.
    """

    source: AuditSource | None = None
    category: AuditCategory | None = None
    severity: AuditSeverity | None = None
    correlation_id: str | None = None
    pipeline_id: str | None = None
    trade_id: str | None = None
    order_id: str | None = None
    position_id: str | None = None
    runtime_id: str | None = None
    user_id: str | None = None
    time_from: datetime | None = None
    time_to: datetime | None = None
    sequence_from: int | None = None
    sequence_to: int | None = None


class AuditQueryEngine:
    """Search engine for audit events backed by any :class:`AuditStorage`.

    Queries are executed in-memory against the full event set.
    For production use with large volumes, consider a database-backed
    storage implementation that pushes filters to the query layer.
    """

    def __init__(self, storage: AuditStorage) -> None:
        self._storage = storage

    def query(self, audit_query: AuditQuery) -> list[AuditEvent]:
        """Execute a query and return matching events in sequence order."""
        events = self._storage.load_all()
        return self._apply_filters(events, audit_query)

    def query_by_source(self, source: AuditSource) -> list[AuditEvent]:
        return self.query(AuditQuery(source=source))

    def query_by_category(self, category: AuditCategory) -> list[AuditEvent]:
        return self.query(AuditQuery(category=category))

    def query_by_severity(self, severity: AuditSeverity) -> list[AuditEvent]:
        return self.query(AuditQuery(severity=severity))

    def query_by_trade_id(self, trade_id: str) -> list[AuditEvent]:
        return self.query(AuditQuery(trade_id=trade_id))

    def query_by_order_id(self, order_id: str) -> list[AuditEvent]:
        return self.query(AuditQuery(order_id=order_id))

    def query_by_pipeline_id(self, pipeline_id: str) -> list[AuditEvent]:
        return self.query(AuditQuery(pipeline_id=pipeline_id))

    def query_by_runtime_id(self, runtime_id: str) -> list[AuditEvent]:
        return self.query(AuditQuery(runtime_id=runtime_id))

    def query_by_correlation_id(self, correlation_id: str) -> list[AuditEvent]:
        return self.query(AuditQuery(correlation_id=correlation_id))

    def query_time_range(
        self, time_from: datetime, time_to: datetime
    ) -> list[AuditEvent]:
        return self.query(AuditQuery(time_from=time_from, time_to=time_to))

    def count(self, audit_query: AuditQuery | None = None) -> int:
        """Count events matching the query (or all events if None)."""
        if audit_query is None:
            return self._storage.count()
        return len(self.query(audit_query))

    @staticmethod
    def _apply_filters(
        events: Sequence[AuditEvent], query: AuditQuery
    ) -> list[AuditEvent]:
        result: list[AuditEvent] = []
        for event in events:
            if not AuditQueryEngine._matches(event, query):
                continue
            result.append(event)
        return result

    @staticmethod
    def _matches(event: AuditEvent, query: AuditQuery) -> bool:
        if query.source is not None and event.source != query.source:
            return False
        if query.category is not None and event.category != query.category:
            return False
        if query.severity is not None and event.severity != query.severity:
            return False
        if (
            query.correlation_id is not None
            and event.correlation_id != query.correlation_id
        ):
            return False
        if query.pipeline_id is not None and event.pipeline_id != query.pipeline_id:
            return False
        if query.trade_id is not None and event.trade_id != query.trade_id:
            return False
        if query.order_id is not None and event.order_id != query.order_id:
            return False
        if query.position_id is not None and event.position_id != query.position_id:
            return False
        if query.runtime_id is not None and event.runtime_id != query.runtime_id:
            return False
        if query.user_id is not None and event.user_id != query.user_id:
            return False
        if query.time_from is not None and event.timestamp < query.time_from:
            return False
        if query.time_to is not None and event.timestamp > query.time_to:
            return False
        if (
            query.sequence_from is not None
            and event.sequence_number < query.sequence_from
        ):
            return False
        return not (query.sequence_to is not None and event.sequence_number > query.sequence_to)
