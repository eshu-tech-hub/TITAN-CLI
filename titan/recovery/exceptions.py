class RecoveryError(Exception):
    """Base exception for recovery and fault tolerance errors."""


class RecoveryInputError(RecoveryError, ValueError):
    """Invalid input to a recovery component."""


class RecoveryStrategyError(RecoveryError):
    """Recovery strategy execution failed."""


class RecoveryTimeoutError(RecoveryError):
    """A recovery operation exceeded its timeout."""


class RecoveryStateError(RecoveryError):
    """Runtime state capture or restoration failed."""


class RecoveryCheckpointError(RecoveryError):
    """Checkpoint persistence or restoration failed."""


class RecoveryCircuitBreakerError(RecoveryError):
    """Circuit breaker operation failed."""


class RecoveryReconnectError(RecoveryError):
    """Broker reconnection failed."""


class RecoveryShutdownError(RecoveryError):
    """Graceful shutdown operation failed."""


class RecoveryRetryError(RecoveryError):
    """All retry attempts exhausted."""
