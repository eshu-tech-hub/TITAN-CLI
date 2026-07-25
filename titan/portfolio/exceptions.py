class PortfolioError(Exception):
    """Base exception for Portfolio Intelligence Engine failures."""


class PortfolioValidationError(PortfolioError, ValueError):
    """Raised when portfolio input or configuration violates domain constraints."""


class PortfolioEngineError(PortfolioError):
    """Raised when the Portfolio Engine cannot complete an operation."""


class PortfolioInputError(PortfolioError):
    """Raised when portfolio input data is invalid or missing required fields."""
