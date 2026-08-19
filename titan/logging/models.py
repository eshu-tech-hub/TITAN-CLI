from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class LogLevel(StrEnum):
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    @staticmethod
    def from_int(level: int) -> LogLevel:
        if level >= 50:
            return LogLevel.CRITICAL
        if level >= 40:
            return LogLevel.ERROR
        if level >= 30:
            return LogLevel.WARNING
        if level >= 20:
            return LogLevel.INFO
        if level >= 10:
            return LogLevel.DEBUG
        return LogLevel.TRACE

    def to_int(self) -> int:
        return _LEVEL_MAP[self]


_LEVEL_MAP: dict[LogLevel, int] = {
    LogLevel.TRACE: 5,
    LogLevel.DEBUG: 10,
    LogLevel.INFO: 20,
    LogLevel.WARNING: 30,
    LogLevel.ERROR: 40,
    LogLevel.CRITICAL: 50,
}


@dataclass(frozen=True, slots=True)
class LogEntry:
    timestamp: datetime
    level: LogLevel
    module: str
    component: str
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)
    exception: str | None = None
    duration_ms: float | None = None

    pipeline_id: str | None = None
    correlation_id: str | None = None
    request_id: str | None = None
    trade_id: str | None = None
    order_id: str | None = None
    position_id: str | None = None
    runtime_id: str | None = None


class HandlerType(StrEnum):
    CONSOLE = "console"
    FILE = "file"
    JSON_FILE = "json_file"


class FormatterType(StrEnum):
    CONSOLE = "console"
    JSON = "json"
    COMPACT = "compact"


@dataclass(frozen=True, slots=True)
class HandlerConfig:
    handler_type: HandlerType
    level: LogLevel = LogLevel.DEBUG
    formatter: FormatterType = FormatterType.CONSOLE
    file_path: str = ""
    max_size_mb: int = 100
    backup_count: int = 5
    encoding: str = "utf-8"
    colorize: bool = True


@dataclass(frozen=True, slots=True)
class LoggingConfig:
    level: LogLevel = LogLevel.INFO
    handlers: tuple[HandlerConfig, ...] = (
        HandlerConfig(
            handler_type=HandlerType.CONSOLE,
            level=LogLevel.INFO,
            formatter=FormatterType.CONSOLE,
        ),
        HandlerConfig(
            handler_type=HandlerType.FILE,
            level=LogLevel.DEBUG,
            formatter=FormatterType.CONSOLE,
            file_path="./logs/titan.log",
        ),
    )
    component: str = "titan"


@dataclass(frozen=True, slots=True)
class LoggingReport:
    level: LogLevel
    component_count: int
    handlers: tuple[HandlerConfig, ...]
    dropped_messages: int = 0
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


def now() -> datetime:
    return datetime.now(UTC)
