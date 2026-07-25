from __future__ import annotations


class LoggingError(Exception):
    """Base exception for logging framework errors."""


class LoggerNotFoundError(LoggingError):
    """Requested logger does not exist."""


class HandlerRegistrationError(LoggingError):
    """Handler could not be registered."""


class LoggingConfigurationError(LoggingError):
    """Logging framework is misconfigured."""


class ContextBindingError(LoggingError):
    """Failed to bind context value."""
