class ExecutionError(Exception):
    """Base exception for all order management failures."""


class OrderNotFoundError(ExecutionError):
    """Raised when an order ID is not found in the order book."""


class InvalidStateTransitionError(ExecutionError):
    """Raised when an illegal order state transition is attempted."""


class OrderValidationError(ExecutionError):
    """Raised when an order or execution request fails validation."""


class BrokerUnavailableError(ExecutionError):
    """Raised when the target broker is not connected or unreachable."""


class RouteNotFoundError(ExecutionError):
    """Raised when no broker route is available for an order type."""
