from __future__ import annotations

import traceback
from typing import Any

from titan.logging.context import LoggingContext
from titan.logging.handlers import Handler
from titan.logging.models import LogEntry, LogLevel, now


class StructuredLogger:
    """A structured logger with automatic context propagation.

    Usage::

        logger = StructuredLogger("execution", "order_manager")
        logger.info("Order placed", order_id="ord-123")
        logger.error("Execution failed", duration_ms=150.2)
    """

    def __init__(
        self,
        module: str,
        component: str = "",
        handlers: list[Handler] | None = None,
    ) -> None:
        self._module = module
        self._component = component or module
        self._handlers: list[Handler] = handlers or []

    @property
    def module(self) -> str:
        return self._module

    @property
    def component(self) -> str:
        return self._component

    def add_handler(self, handler: Handler) -> None:
        self._handlers.append(handler)

    def remove_handlers(self) -> None:
        self._handlers.clear()

    def trace(self, message: str, **metadata: Any) -> None:
        self._log(LogLevel.TRACE, message, None, None, **metadata)

    def debug(self, message: str, **metadata: Any) -> None:
        self._log(LogLevel.DEBUG, message, None, None, **metadata)

    def info(self, message: str, **metadata: Any) -> None:
        self._log(LogLevel.INFO, message, None, None, **metadata)

    def warning(self, message: str, **metadata: Any) -> None:
        self._log(LogLevel.WARNING, message, None, None, **metadata)

    def error(
        self,
        message: str,
        exc_info: BaseException | None = None,
        **metadata: Any,
    ) -> None:
        self._log(LogLevel.ERROR, message, exc_info, None, **metadata)

    def critical(
        self,
        message: str,
        exc_info: BaseException | None = None,
        **metadata: Any,
    ) -> None:
        self._log(LogLevel.CRITICAL, message, exc_info, None, **metadata)

    def exception(
        self,
        message: str,
        exc_info: BaseException | None = None,
        **metadata: Any,
    ) -> None:
        self._log(LogLevel.ERROR, message, exc_info, None, **metadata)

    def duration(
        self,
        message: str,
        duration_ms: float,
        level: LogLevel = LogLevel.INFO,
        **metadata: Any,
    ) -> None:
        self._log(level, message, None, duration_ms, **metadata)

    def _log(
        self,
        level: LogLevel,
        message: str,
        exc_info: BaseException | None,
        duration_ms: float | None,
        **metadata: Any,
    ) -> None:
        exc_str: str | None = None
        if exc_info is not None:
            exc_str = "".join(
                traceback.format_exception(
                    type(exc_info), exc_info, exc_info.__traceback__
                )
            )

        ctx = LoggingContext.current()

        entry = LogEntry(
            timestamp=now(),
            level=level,
            module=self._module,
            component=self._component,
            message=message,
            metadata=metadata,
            exception=exc_str,
            duration_ms=duration_ms,
            pipeline_id=ctx.get("pipeline_id"),
            correlation_id=ctx.get("correlation_id"),
            request_id=ctx.get("request_id"),
            trade_id=ctx.get("trade_id"),
            order_id=ctx.get("order_id"),
            position_id=ctx.get("position_id"),
            runtime_id=ctx.get("runtime_id"),
        )

        for handler in self._handlers:
            handler.emit(entry)
