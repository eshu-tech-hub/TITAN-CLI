from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum

# ── Enums ──


class EnvironmentProfile(StrEnum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PAPER_TRADING = "paper"
    BACKTESTING = "backtesting"
    PRODUCTION = "production"


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class BrokerProvider(StrEnum):
    PAPER = "paper"
    ANGEL_ONE = "angel_one"


# ── App ──


@dataclass(frozen=True, slots=True)
class AppConfig:
    name: str = "TITAN"
    version: str = "1.0.0"
    environment: str = "development"
    log_level: str = "INFO"
    data_dir: str = "./data"
    config_dir: str = "./config"


# ── Broker ──


@dataclass(frozen=True, slots=True)
class BrokerConfig:
    provider: str = "paper"
    api_key: str = ""
    client_id: str = ""
    pin: str = ""
    totp_secret: str = ""
    access_token: str = ""
    paper_initial_cash: Decimal = Decimal(100000)
    connection_timeout_seconds: float = 30.0
    max_retries: int = 3


# ── Runtime ──


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    pipeline_interval_seconds: float = 60.0
    heartbeat_interval_seconds: float = 10.0
    stream_enabled: bool = False
    scheduler_enabled: bool = True
    heartbeat_enabled: bool = True
    max_pipeline_executions: int = 0


# ── Risk ──


@dataclass(frozen=True, slots=True)
class RiskConfig:
    max_position_size: Decimal = Decimal(100000)
    max_drawdown_percent: Decimal = Decimal("20.0")
    max_daily_loss: Decimal = Decimal(50000)
    max_leverage: Decimal = Decimal("1.0")
    margin_call_threshold_percent: Decimal = Decimal("50.0")
    stop_loss_percent: Decimal = Decimal("5.0")


# ── Execution ──


@dataclass(frozen=True, slots=True)
class ExecutionConfig:
    max_retries: int = 3
    retry_delay_seconds: float = 5.0
    order_timeout_seconds: float = 30.0
    default_slippage_percent: Decimal = Decimal("0.1")
    default_commission_flat: Decimal = Decimal(10)
    default_commission_percent: Decimal = Decimal("0.01")


# ── Logging ──


@dataclass(frozen=True, slots=True)
class LoggingConfig:
    level: str = "INFO"
    file: str = "./logs/titan.log"
    max_size_mb: int = 100
    backup_count: int = 5
    format_template: str = "{time} | {level} | {name} | {message}"


# ── Monitoring ──


@dataclass(frozen=True, slots=True)
class MonitoringConfig:
    enabled: bool = False
    collector_interval_seconds: float = 60.0
    health_check_interval_seconds: float = 30.0
    snapshot_retention: int = 100
    prometheus_enabled: bool = False
    prometheus_port: int = 8000
    max_failures_stored: int = 100


# ── Top-Level Config ──


@dataclass(frozen=True, slots=True)
class TitanConfig:
    profile: str = "development"
    app: AppConfig = field(default_factory=AppConfig)
    broker: BrokerConfig = field(default_factory=BrokerConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    custom: dict[str, object] = field(default_factory=dict)


# ── Report ──


@dataclass(frozen=True, slots=True)
class ConfigurationReport:
    profile: str
    sources: tuple[str, ...]
    validation_status: str
    warnings: tuple[str, ...]
    errors: tuple[str, ...]
    config: TitanConfig | None = None
