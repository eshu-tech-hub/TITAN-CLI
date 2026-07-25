from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class AuditSource(StrEnum):
    """Origin of an audit event."""

    CONFIGURATION = "configuration"
    RUNTIME = "runtime"
    MONITORING = "monitoring"
    ALERTING = "alerting"
    RECOVERY = "recovery"
    PIPELINE = "pipeline"
    DECISION = "decision"
    RISK = "risk"
    PORTFOLIO = "portfolio"
    EXECUTION = "execution"
    OMS = "oms"
    BROKER = "broker"
    PAPER_TRADING = "paper_trading"
    BACKTESTING = "backtesting"
    USER = "user"


class AuditCategory(StrEnum):
    """Category of an audit event."""

    CONFIG_CHANGE = "config_change"
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    CONNECTION = "connection"
    DISCONNECTION = "disconnection"
    DATA_RECEIVED = "data_received"
    DATA_PROCESSED = "data_processed"
    PIPELINE_EXECUTED = "pipeline_executed"
    PIPELINE_FAILED = "pipeline_failed"
    TRADE_QUALIFIED = "trade_qualified"
    TRADE_REJECTED = "trade_rejected"
    ORDER_PLACED = "order_placed"
    ORDER_FILLED = "order_filled"
    ORDER_CANCELLED = "order_cancelled"
    ORDER_REJECTED = "order_rejected"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    RISK_BREACH = "risk_breach"
    RISK_WARNING = "risk_warning"
    RISK_OK = "risk_ok"
    ALERT_TRIGGERED = "alert_triggered"
    ALERT_RESOLVED = "alert_resolved"
    RECOVERY_INITIATED = "recovery_initiated"
    RECOVERY_COMPLETED = "recovery_completed"
    CHECKPOINT_SAVED = "checkpoint_saved"
    HEALTH_CHECK = "health_check"
    USER_ACTION = "user_action"
    ERROR = "error"


class AuditSeverity(StrEnum):
    """Severity level of an audit event."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditResult(StrEnum):
    """Outcome of an audited action."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    SKIPPED = "skipped"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """Immutable record of a single audited action.

    Every field is set at construction time and never mutated.
    The hash chain fields (event_hash, previous_hash) provide
    tamper detection once the event is persisted.
    """

    event_id: str
    timestamp: datetime
    sequence_number: int
    source: AuditSource
    category: AuditCategory
    severity: AuditSeverity
    action: str
    result: AuditResult
    correlation_id: str = ""
    pipeline_id: str = ""
    trade_id: str = ""
    order_id: str = ""
    position_id: str = ""
    runtime_id: str = ""
    user_id: str = ""
    event_hash: str = ""
    previous_hash: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "sequence_number": self.sequence_number,
            "source": self.source.value,
            "category": self.category.value,
            "severity": self.severity.value,
            "action": self.action,
            "result": self.result.value,
            "correlation_id": self.correlation_id,
            "pipeline_id": self.pipeline_id,
            "trade_id": self.trade_id,
            "order_id": self.order_id,
            "position_id": self.position_id,
            "runtime_id": self.runtime_id,
            "user_id": self.user_id,
            "event_hash": self.event_hash,
            "previous_hash": self.previous_hash,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuditEvent:
        """Deserialize from a dictionary."""
        ts = data["timestamp"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        return cls(
            event_id=data["event_id"],
            timestamp=ts,
            sequence_number=data["sequence_number"],
            source=AuditSource(data["source"]),
            category=AuditCategory(data["category"]),
            severity=AuditSeverity(data["severity"]),
            action=data["action"],
            result=AuditResult(data["result"]),
            correlation_id=data.get("correlation_id", ""),
            pipeline_id=data.get("pipeline_id", ""),
            trade_id=data.get("trade_id", ""),
            order_id=data.get("order_id", ""),
            position_id=data.get("position_id", ""),
            runtime_id=data.get("runtime_id", ""),
            user_id=data.get("user_id", ""),
            event_hash=data.get("event_hash", ""),
            previous_hash=data.get("previous_hash", ""),
            metadata=data.get("metadata", {}),
        )


@dataclass(frozen=True, slots=True)
class AuditReport:
    """Summary report of audit event statistics."""

    total_events: int = 0
    events_by_source: dict[str, int] = field(default_factory=dict)
    events_by_severity: dict[str, int] = field(default_factory=dict)
    events_by_category: dict[str, int] = field(default_factory=dict)
    integrity_status: str = "unknown"
    verification_failures: int = 0
    first_event_time: datetime | None = None
    last_event_time: datetime | None = None
    sequence_range: tuple[int, int] = (0, 0)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
