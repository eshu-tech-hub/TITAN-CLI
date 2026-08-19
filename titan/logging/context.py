from __future__ import annotations

import contextvars
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, ClassVar


class LoggingContext:
    """Thread-safe context propagation for structured logging fields.

    Uses ``contextvars`` so that each thread and async task has its own
    independent context. This is automatically propagated across
    ``asyncio`` tasks and thread boundaries.

    Usage::

        # Bind a value for the current context
        LoggingContext.bind(pipeline_id="pl-123", trade_id="tr-456")

        # Get all current context values
        ctx = LoggingContext.current()

        # Temporarily override within a scope
        with LoggingContext.scope(trade_id="tr-789"):
            ...

        # Clear all context values
        LoggingContext.clear()
    """

    _pipeline_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
        "pipeline_id", default=None
    )
    _correlation_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
        "correlation_id", default=None
    )
    _request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
        "request_id", default=None
    )
    _trade_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
        "trade_id", default=None
    )
    _order_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
        "order_id", default=None
    )
    _position_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
        "position_id", default=None
    )
    _runtime_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
        "runtime_id", default=None
    )
    _extra: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar(
        "extra", default={}
    )

    _FIELDS: ClassVar[dict[str, contextvars.ContextVar[str | None]]] = {
        "pipeline_id": _pipeline_id,
        "correlation_id": _correlation_id,
        "request_id": _request_id,
        "trade_id": _trade_id,
        "order_id": _order_id,
        "position_id": _position_id,
        "runtime_id": _runtime_id,
    }

    @classmethod
    def current(cls) -> dict[str, Any]:
        """Return all bound context values as a dict."""
        result: dict[str, Any] = {}
        for name, var in cls._FIELDS.items():
            value = var.get()
            if value is not None:
                result[name] = value
        extra = cls._extra.get()
        if extra:
            result.update(extra)
        return result

    @classmethod
    def bind(cls, **kwargs: Any) -> None:
        """Bind context values for the current execution context.

        Raises:
            ContextBindingError: If an unknown field is provided.
        """
        for key, value in kwargs.items():
            if key in cls._FIELDS:
                cls._FIELDS[key].set(value)
            elif key == "extra":
                cls._extra.set(value)
            else:
                extra = cls._extra.get().copy()
                extra[key] = value
                cls._extra.set(extra)

    @classmethod
    def get(cls, key: str) -> Any | None:
        """Get a single context value by key."""
        if key in cls._FIELDS:
            return cls._FIELDS[key].get()
        extra = cls._extra.get()
        return extra.get(key)

    @classmethod
    def clear(cls) -> None:
        """Clear all context values."""
        for var in cls._FIELDS.values():
            var.set(None)
        cls._extra.set({})

    @classmethod
    @contextmanager
    def scope(cls, **kwargs: Any) -> Iterator[None]:
        """Temporarily bind context values within a scope.

        On exit, the previous values are restored.
        """
        saved = cls.current()
        try:
            cls.bind(**kwargs)
            yield
        finally:
            cls.clear()
            cls.bind(**saved)
