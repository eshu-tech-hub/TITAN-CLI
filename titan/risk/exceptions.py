class RiskError(Exception):
    """Base exception for Risk Intelligence Engine failures."""


class RiskValidationError(RiskError, ValueError):
    """Raised when risk input or configuration violates domain constraints."""


class RiskEngineError(RiskError):
    """Raised when the Risk Engine cannot complete an operation."""


class RiskInputError(RiskError):
    """Raised when risk input data is invalid or missing required fields."""
