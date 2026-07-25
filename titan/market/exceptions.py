class MarketDataError(Exception):
    """Base exception for market data layer failures."""


class MarketDataProviderError(MarketDataError):
    """Raised when a market data provider fails to satisfy a request."""


class MarketDataValidationError(MarketDataError, ValueError):
    """Raised when normalized market data violates domain rules."""


class SymbolValidationError(MarketDataValidationError):
    """Raised when a symbol is missing required identity fields."""


class TimeframeValidationError(MarketDataValidationError):
    """Raised when a timeframe is unsupported or missing."""
