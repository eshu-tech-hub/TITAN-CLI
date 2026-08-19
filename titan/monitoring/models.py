from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class MetricType(str, Enum):
    GAUGE = "gauge"
    COUNTER = "counter"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class MetricUnit(str, Enum):
    MILLISECONDS = "ms"
    SECONDS = "s"
    PERCENT = "%"
    COUNT = "count"
    BYTES = "bytes"
    MEGABYTES = "mb"
    GIGABYTES = "gb"
    BITS_PER_SECOND = "bps"
    MEGABITS_PER_SECOND = "mbps"
    NONE = "none"


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    OFFLINE = "offline"


class Subsystem(str, Enum):
    MARKET = "market"
    BROKER = "broker"
    EXECUTION = "execution"
    RISK = "risk"
    PIPELINE = "pipeline"
    PORTFOLIO = "portfolio"
    DECISION = "decision"
    RUNTIME = "runtime"
    EVENTS = "events"
    INTELLIGENCE = "intelligence"
    TRADING = "trading"
    CONFIG = "config"
    MONITORING = "monitoring"
    PAPER = "paper"
    BACKTESTING = "backtesting"


class CollectorType(str, Enum):
    PERIODIC = "periodic"
    EVENT_DRIVEN = "event_driven"
    CUSTOM = "custom"


@dataclass(frozen=True, slots=True)
class MetricValue:
    name: str
    value: float
    type: MetricType = MetricType.GAUGE
    unit: MetricUnit = MetricUnit.NONE
    tags: Mapping[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    description: str = ""


@dataclass(frozen=True, slots=True)
class MetricSnapshot:
    metrics: tuple[MetricValue, ...] = field(default_factory=tuple)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    source: str = "unknown"


@dataclass(frozen=True, slots=True)
class SubsystemHealth:
    subsystem: Subsystem
    status: HealthStatus = HealthStatus.HEALTHY
    message: str = ""
    last_healthy: datetime | None = None
    last_check: datetime = field(default_factory=lambda: datetime.now(UTC))
    latency_ms: float = 0.0
    failures: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SystemHealth:
    subsystems: tuple[SubsystemHealth, ...] = field(default_factory=tuple)
    overall: HealthStatus = HealthStatus.HEALTHY
    healthy_count: int = 0
    warning_count: int = 0
    critical_count: int = 0
    offline_count: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class TelemetrySnapshot:
    metrics: tuple[MetricValue, ...] = field(default_factory=tuple)
    health: SystemHealth | None = None
    failed_collections: int = 0
    total_collections: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class CollectorDescriptor:
    name: str
    type: CollectorType
    collect: Callable[[], tuple[MetricValue, ...]]
    interval_seconds: float = 60.0
    enabled: bool = True
    description: str = ""


@dataclass(frozen=True, slots=True)
class DashboardMetricSummary:
    name: str
    current: float
    min: float
    max: float
    avg: float
    unit: MetricUnit = MetricUnit.NONE
    trend: str = "stable"


@dataclass(frozen=True, slots=True)
class DashboardStatus:
    system_health: SystemHealth | None = None
    metric_summaries: tuple[DashboardMetricSummary, ...] = field(default_factory=tuple)
    recent_failures: tuple[str, ...] = field(default_factory=tuple)
    active_collectors: int = 0
    total_collections: int = 0
    failed_collections: int = 0
    uptime_seconds: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class MonitoringReport:
    system_health: SystemHealth | None = None
    metrics: tuple[MetricValue, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    recommendations: tuple[str, ...] = field(default_factory=tuple)
    collector_count: int = 0
    failed_collections: int = 0
    total_collections: int = 0
    uptime_seconds: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
