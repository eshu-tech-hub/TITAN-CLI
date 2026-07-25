from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

from titan.logging.models import LogEntry, LogLevel


class Formatter(ABC):
    """Abstract base for all log formatters."""

    @abstractmethod
    def format(self, entry: LogEntry) -> str: ...


class ConsoleFormatter(Formatter):
    """Human-readable colored console output.

    Uses ANSI escape codes for log level coloring.
    """

    _LEVEL_COLORS: dict[LogLevel, str] = {
        LogLevel.TRACE: "\x1b[37m",  # white
        LogLevel.DEBUG: "\x1b[36m",  # cyan
        LogLevel.INFO: "\x1b[32m",  # green
        LogLevel.WARNING: "\x1b[33m",  # yellow
        LogLevel.ERROR: "\x1b[31m",  # red
        LogLevel.CRITICAL: "\x1b[41m",  # red background
    }
    _RESET = "\x1b[0m"

    def __init__(self, colorize: bool = True) -> None:
        self._colorize = colorize

    def format(self, entry: LogEntry) -> str:
        ts = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        level_str = entry.level.value.ljust(8)
        ctx = self._format_context(entry)

        if self._colorize:
            color = self._LEVEL_COLORS.get(entry.level, self._RESET)
            level_colored = f"{color}{level_str}{self._RESET}"
            return (
                f"{ts} | {level_colored} | {entry.component:<12} | "
                f"{entry.message}{ctx}"
            )

        return f"{ts} | {level_str} | {entry.component:<12} | " f"{entry.message}{ctx}"

    def _format_context(self, entry: LogEntry) -> str:
        parts = []
        if entry.pipeline_id:
            parts.append(f"pipeline={entry.pipeline_id}")
        if entry.correlation_id:
            parts.append(f"correlation={entry.correlation_id}")
        if entry.trade_id:
            parts.append(f"trade={entry.trade_id}")
        if entry.order_id:
            parts.append(f"order={entry.order_id}")
        if entry.position_id:
            parts.append(f"position={entry.position_id}")
        if entry.request_id:
            parts.append(f"request={entry.request_id}")
        if entry.runtime_id:
            parts.append(f"runtime={entry.runtime_id}")
        if entry.duration_ms is not None:
            parts.append(f"duration={entry.duration_ms:.1f}ms")
        if entry.metadata:
            for k, v in entry.metadata.items():
                parts.append(f"{k}={v}")
        if entry.exception:
            parts.append(f"exception={entry.exception}")
        if parts:
            return " [" + " ".join(parts) + "]"
        return ""


class JSONFormatter(Formatter):
    """Structured JSON output. One object per line."""

    def format(self, entry: LogEntry) -> str:
        obj: dict[str, Any] = {
            "timestamp": entry.timestamp.isoformat(),
            "level": entry.level.value,
            "component": entry.component,
            "message": entry.message,
        }
        if entry.module:
            obj["module"] = entry.module
        if entry.pipeline_id:
            obj["pipeline_id"] = entry.pipeline_id
        if entry.correlation_id:
            obj["correlation_id"] = entry.correlation_id
        if entry.request_id:
            obj["request_id"] = entry.request_id
        if entry.trade_id:
            obj["trade_id"] = entry.trade_id
        if entry.order_id:
            obj["order_id"] = entry.order_id
        if entry.position_id:
            obj["position_id"] = entry.position_id
        if entry.runtime_id:
            obj["runtime_id"] = entry.runtime_id
        if entry.duration_ms is not None:
            obj["duration_ms"] = entry.duration_ms
        if entry.metadata:
            obj["metadata"] = entry.metadata
        if entry.exception:
            obj["exception"] = entry.exception
        return json.dumps(obj, default=str, ensure_ascii=False)


class CompactFormatter(Formatter):
    """Minimal single-line output for high-throughput logging."""

    def format(self, entry: LogEntry) -> str:
        ts = entry.timestamp.strftime("%H:%M:%S")
        level_char = entry.level.value[0]
        return f"{ts} {level_char} {entry.component} {entry.message}"
