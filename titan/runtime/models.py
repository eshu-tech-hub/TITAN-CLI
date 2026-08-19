from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum, auto
from typing import Any

from titan.brokers.models import ConnectionStatus, Exchange


class RuntimeStatus(Enum):
    """Operational status of the runtime engine."""

    STOPPED = auto()
    STARTING = auto()
    RUNNING = auto()
    PAUSED = auto()
    STOPPING = auto()
    ERROR = auto()


class RuntimeEventType(Enum):
    """Types of events published on the runtime event bus."""

    # Runtime lifecycle events
    RUNTIME_STARTED = auto()
    RUNTIME_STOPPED = auto()
    RUNTIME_PAUSED = auto()
    RUNTIME_RESUMED = auto()
    RUNTIME_ERROR = auto()

    # Stream events
    STREAM_CONNECTED = auto()
    STREAM_DISCONNECTED = auto()
    STREAM_RECONNECTED = auto()
    STREAM_ERROR = auto()
    STREAM_QUOTE = auto()
    STREAM_HEARTBEAT = auto()

    # Subscription events
    SUBSCRIPTION_ADDED = auto()
    SUBSCRIPTION_REMOVED = auto()
    SUBSCRIPTION_ERROR = auto()

    # Scheduler events
    SCHEDULER_TICK = auto()
    SCHEDULER_PIPELINE_STARTED = auto()
    SCHEDULER_PIPELINE_COMPLETED = auto()
    SCHEDULER_PIPELINE_FAILED = auto()
    SCHEDULER_ERROR = auto()

    # Heartbeat events
    HEARTBEAT_TICK = auto()
    HEARTBEAT_MISSED = auto()
    HEARTBEAT_RESTORED = auto()

    # Broker events
    BROKER_CONNECTED = auto()
    BROKER_DISCONNECTED = auto()
    BROKER_ERROR = auto()

    # Pipeline events
    PIPELINE_EXECUTED = auto()
    PIPELINE_FAILED = auto()

    # Health events
    HEALTH_OK = auto()
    HEALTH_WARNING = auto()
    HEALTH_CRITICAL = auto()


class SubscriptionType(Enum):
    """Types of market data subscriptions."""

    SYMBOL = auto()
    OPTION_CHAIN = auto()
    INDEX = auto()
    WATCHLIST = auto()
    MARKET_DEPTH = auto()


class HealthStatus(Enum):
    """Health status of a runtime component."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class RuntimeEvent:
    """An event published on the runtime event bus.

    Attributes:
        event_type: Type of event.
        source: Component that produced the event.
        timestamp: When the event occurred.
        data: Optional event payload.
    """

    event_type: RuntimeEventType
    source: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    data: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Subscription:
    """A market data subscription.

    Attributes:
        symbol: Trading symbol.
        exchange: Exchange.
        subscription_type: Type of subscription.
        enabled: Whether the subscription is active.
        metadata: Additional subscription metadata.
    """

    symbol: str
    exchange: Exchange
    subscription_type: SubscriptionType = SubscriptionType.SYMBOL
    enabled: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ComponentHealth:
    """Health snapshot of a single runtime component.

    Attributes:
        component_name: Name of the component.
        status: Current health status.
        status_changed_at: When the status last changed.
        last_update: When the component last reported.
        latency_ms: Current latency in milliseconds.
        error: Current error message if unhealthy.
        metadata: Additional health metadata.
    """

    component_name: str
    status: HealthStatus = HealthStatus.UNKNOWN
    status_changed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_update: datetime | None = None
    latency_ms: float = 0.0
    error: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RuntimeHealth:
    component_health: tuple[ComponentHealth, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class SchedulerStatus:
    active: bool = False
    pipeline_executions: int = 0
    last_pipeline_time: datetime | None = None


@dataclass(frozen=True, slots=True)
class BrokerStatus:
    connection: ConnectionStatus = ConnectionStatus.DISCONNECTED


@dataclass(frozen=True, slots=True)
class MarketStatus:
    stream_status: str = "disconnected"
    active_subscriptions: int = 0
    last_quote_time: datetime | None = None


@dataclass(frozen=True, slots=True)
class JournalStatus:
    pass


@dataclass(frozen=True, slots=True)
class ResourceStatus:
    pass


@dataclass(frozen=True, slots=True)
class PerformanceStatus:
    uptime_seconds: float = 0.0


@dataclass(frozen=True, slots=True)
class RecoveryStatus:
    pass


@dataclass(frozen=True, slots=True)
class PaperBrokerStatus:
    active: bool = False


@dataclass(frozen=True, slots=True)
class PortfolioStatus:
    pass


@dataclass(frozen=True, slots=True)
class RuntimeReport:
    """Snapshot of runtime state for monitoring."""

    runtime_status: RuntimeStatus
    health: RuntimeHealth = field(default_factory=RuntimeHealth)
    scheduler: SchedulerStatus = field(default_factory=SchedulerStatus)
    broker: BrokerStatus = field(default_factory=BrokerStatus)
    market: MarketStatus = field(default_factory=MarketStatus)
    journal: JournalStatus = field(default_factory=JournalStatus)
    resource: ResourceStatus = field(default_factory=ResourceStatus)
    performance: PerformanceStatus = field(default_factory=PerformanceStatus)
    recovery: RecoveryStatus = field(default_factory=RecoveryStatus)
    paper: PaperBrokerStatus = field(default_factory=PaperBrokerStatus)
    portfolio: PortfolioStatus = field(default_factory=PortfolioStatus)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def uptime_seconds(self) -> float:
        """Return runtime uptime using the legacy report-level API."""
        return self.performance.uptime_seconds

    @property
    def broker_status(self) -> ConnectionStatus:
        """Legacy flat accessor for broker connection status."""
        return self.broker.connection

    @property
    def stream_status(self) -> str:
        """Legacy flat accessor for market stream status."""
        return self.market.stream_status

    @property
    def scheduler_active(self) -> bool:
        """Legacy flat accessor for scheduler active flag."""
        return self.scheduler.active

    @property
    def pipeline_executions(self) -> int:
        """Legacy flat accessor for scheduler pipeline executions."""
        return self.scheduler.pipeline_executions

    @property
    def component_health(self) -> tuple[ComponentHealth, ...]:
        """Legacy flat accessor for component health tuple."""
        return self.health.component_health

    @property
    def warnings(self) -> tuple[str, ...]:
        """Legacy flat accessor for health warnings."""
        return self.health.warnings

    @property
    def errors(self) -> tuple[str, ...]:
        """Legacy flat accessor for health errors."""
        return self.health.errors
