class BrokerError(Exception):
    """Base exception for all broker abstraction failures."""


class ConnectionError(BrokerError):
    """Raised when broker connection or reconnection fails."""


class AuthenticationError(BrokerError):
    """Raised when authentication or session credentials are invalid."""


class OrderError(BrokerError):
    """Raised when order placement, modification, or cancellation fails."""


class MarketDataError(BrokerError):
    """Raised when market data queries fail."""


class ValidationError(BrokerError):
    """Raised when a request or configuration fails domain validation."""
