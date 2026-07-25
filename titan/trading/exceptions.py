class TradeQualificationError(Exception):
    """Base exception for trade qualification engine failures."""


class TradeQualificationInputError(TradeQualificationError, ValueError):
    """Raised when input to the trade qualification engine is invalid."""


class TradeQualificationEngineError(TradeQualificationError):
    """Raised when the trade qualification engine cannot complete processing."""
