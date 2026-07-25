from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class CircuitBreakerState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class RetryMode(str, Enum):
    IMMEDIATE = "immediate"
    FIXED_DELAY = "fixed_delay"
    LINEAR_BACKOFF = "linear_backoff"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    EXPONENTIAL_JITTER = "exponential_jitter"


class RecoveryStrategy(str, Enum):
    RETRY = "retry"
    RESTART = "restart"
    RECONNECT = "reconnect"
    FAILOVER = "failover"
    SHUTDOWN = "shutdown"
    ESCALATE = "escalate"


class RecoveryLevel(int, Enum):
    """
    Escalating sequence of recovery actions.
    Level 1: Retry operation.
    Level 2: Restart subsystem.
    Level 3: Restart Runtime Engine.
    Level 4: Graceful shutdown.
    """

    RETRY = 1
    RESTART_SUBSYSTEM = 2
    RESTART_ENGINE = 3
    GRACEFUL_SHUTDOWN = 4


class RecoveryStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ComponentType(str, Enum):
    PIPELINE = "pipeline"
    BROKER_SESSION = "broker_session"
    MARKET_STREAM = "market_stream"
    EXECUTION_ENGINE = "execution_engine"
    PORTFOLIO = "portfolio"
    MONITORING = "monitoring"
    ALERTING = "alerting"
    RISK_MODULE = "risk_module"
    CONFIGURATION = "configuration"
    BACKTESTING = "backtesting"
    PAPER_TRADING = "paper_trading"
    LOGGING = "logging"


class ShutdownStage(str, Enum):
    NOT_STARTED = "not_started"
    STOPPING_PIPELINE = "stopping_pipeline"
    CANCELLING_WORKERS = "cancelling_workers"
    FLUSHING_LOGS = "flushing_logs"
    PERSISTING_CHECKPOINTS = "persisting_checkpoints"
    CLOSING_BROKER = "closing_broker"
    RELEASING_RESOURCES = "releasing_resources"
    COMPLETED = "completed"


class ReconnectStrategy(str, Enum):
    IMMEDIATE = "immediate"
    SEQUENTIAL = "sequential"
    GRACEFUL = "graceful"


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    mode: RetryMode = RetryMode.EXPONENTIAL_BACKOFF
    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    timeout_seconds: float = 0.0
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,)
    jitter_factor: float = 0.1


@dataclass(frozen=True, slots=True)
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout_seconds: float = 30.0
    success_threshold: int = 3
    half_open_max_calls: int = 1


@dataclass(frozen=True, slots=True)
class RecoveryRequest:
    component: ComponentType
    strategy: RecoveryStrategy
    failure_reason: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
    retry_policy: RetryPolicy | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    request_id: str = ""


@dataclass(frozen=True, slots=True)
class RecoveryAttempt:
    attempt_number: int
    strategy: RecoveryStrategy
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    status: RecoveryStatus = RecoveryStatus.PENDING
    error: str = ""
    duration_seconds: float = 0.0


@dataclass(frozen=True, slots=True)
class RecoveryReport:
    request_id: str
    component: ComponentType
    strategy: RecoveryStrategy
    status: RecoveryStatus
    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    duration_seconds: float = 0.0
    recovered_components: tuple[str, ...] = field(default_factory=tuple)
    failure_reason: str = ""
    error: str = ""
    attempts: tuple[RecoveryAttempt, ...] = field(default_factory=tuple)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Checkpoint:
    checkpoint_id: str
    component: ComponentType
    state_data: Mapping[str, Any]
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RuntimeStateSnapshot:
    pipeline_progress: Mapping[str, Any] = field(default_factory=dict)
    current_stage: str = ""
    open_orders: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)
    portfolio_snapshot: Mapping[str, Any] = field(default_factory=dict)
    runtime_config: Mapping[str, Any] = field(default_factory=dict)
    monitoring_status: Mapping[str, Any] = field(default_factory=dict)
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True, slots=True)
class BrokerSessionState:
    is_connected: bool = False
    session_id: str = ""
    last_heartbeat: datetime | None = None
    subscriptions: tuple[str, ...] = field(default_factory=tuple)
    reconnect_attempts: int = 0
    error: str = ""


@dataclass(frozen=True, slots=True)
class ShutdownPlan:
    stage: ShutdownStage = ShutdownStage.NOT_STARTED
    timeout_per_stage: float = 30.0
    force_timeout_seconds: float = 120.0
    preserve_checkpoints: bool = True
    close_broker_sessions: bool = True
    flush_logs: bool = True
    cancel_workers: bool = True
