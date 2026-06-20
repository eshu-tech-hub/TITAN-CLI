class TitanError(Exception):
    """Base exception for TITAN."""


class ConfigurationError(TitanError):
    """Configuration related errors."""


class BrokerError(TitanError):
    """Broker related errors."""


class AuthenticationError(BrokerError):
    """Authentication failed."""


class NetworkError(BrokerError):
    """Network communication failed."""


class MarketDataError(TitanError):
    """Market data retrieval failed."""


class RiskError(TitanError):
    """Risk engine blocked an operation."""