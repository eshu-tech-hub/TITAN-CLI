from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class AlertLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


_LEVEL_ORDER: dict[AlertLevel, int] = {
    AlertLevel.INFO: 0,
    AlertLevel.WARNING: 1,
    AlertLevel.ERROR: 2,
    AlertLevel.CRITICAL: 3,
    AlertLevel.EMERGENCY: 4,
}


def level_rank(level: AlertLevel) -> int:
    return _LEVEL_ORDER.get(level, 0)


class AlertSource(str, Enum):
    RUNTIME = "runtime"
    PIPELINE = "pipeline"
    MONITORING = "monitoring"
    BROKER = "broker"
    OMS = "oms"
    EXECUTION = "execution"
    PORTFOLIO = "portfolio"
    RISK = "risk"
    CONFIGURATION = "configuration"
    LOGGING = "logging"
    PAPER_TRADING = "paper_trading"
    BACKTESTING = "backtesting"
    SYSTEM = "system"


class AlertStatus(str, Enum):
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"
    ESCALATED = "escalated"


class ChannelType(str, Enum):
    CONSOLE = "console"
    EMAIL = "email"
    TELEGRAM = "telegram"
    SLACK = "slack"
    WEBHOOK = "webhook"


class AlertRuleType(str, Enum):
    THRESHOLD = "threshold"
    STATE_CHANGE = "state_change"
    PATTERN = "pattern"
    CUSTOM = "custom"


class NotificationResult(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass(frozen=True, slots=True)
class Alert:
    alert_id: str
    level: AlertLevel
    source: AlertSource
    title: str
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: AlertStatus = AlertStatus.NEW
    acknowledged_at: datetime | None = None
    acknowledged_by: str = ""
    resolved_at: datetime | None = None
    resolved_by: str = ""
    escalated_at: datetime | None = None
    escalation_count: int = 0
    rule_name: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class AlertRule:
    name: str
    condition: Callable[[Alert], bool]
    level: AlertLevel = AlertLevel.WARNING
    source: AlertSource | None = None
    cooldown_seconds: float = 300.0
    suppress_duplicates: bool = True
    max_escalations: int = 3
    escalation_delay_seconds: float = 600.0
    enabled: bool = True
    description: str = ""


@dataclass(frozen=True, slots=True)
class AlertRuleResult:
    rule_name: str
    matched: bool
    alert: Alert | None = None
    escalated: bool = False
    suppressed: bool = False
    reason: str = ""


@dataclass(frozen=True, slots=True)
class ChannelConfig:
    channel_type: ChannelType
    enabled: bool = True
    min_level: AlertLevel = AlertLevel.WARNING
    config: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class NotificationAttempt:
    channel: ChannelType
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    result: NotificationResult = NotificationResult.SUCCESS
    error: str = ""
    retry_count: int = 0


@dataclass(frozen=True, slots=True)
class AlertHistoryEntry:
    alert: Alert
    notifications: tuple[NotificationAttempt, ...] = field(default_factory=tuple)
    rule_results: tuple[AlertRuleResult, ...] = field(default_factory=tuple)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True, slots=True)
class AlertReport:
    total_alerts: int = 0
    active_alerts: int = 0
    critical_alerts: int = 0
    acknowledged_alerts: int = 0
    resolved_alerts: int = 0
    suppressed_alerts: int = 0
    escalated_alerts: int = 0
    alerts_by_source: Mapping[str, int] = field(default_factory=dict)
    alerts_by_level: Mapping[str, int] = field(default_factory=dict)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
