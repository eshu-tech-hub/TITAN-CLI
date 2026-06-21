class BrokerError(Exception):
    """Base broker exception."""


class AuthenticationError(BrokerError):
    """Authentication failed."""


class SessionExpiredError(BrokerError):
    """Session expired."""


class MarketDataError(BrokerError):
    """Market data unavailable."""