class RuntimeError(Exception):
    """Base exception for runtime errors."""


class StreamError(RuntimeError):
    """Raised when market stream operations fail."""


class StreamConnectionError(StreamError):
    """Raised when stream connection fails."""


class StreamReconnectError(StreamError):
    """Raised when stream reconnection fails."""


class SchedulerError(RuntimeError):
    """Raised when scheduler operations fail."""


class SubscriptionError(RuntimeError):
    """Raised when subscription operations fail."""


class HeartbeatError(RuntimeError):
    """Raised when heartbeat monitoring fails."""


class HealthError(RuntimeError):
    """Raised when health check operations fail."""
