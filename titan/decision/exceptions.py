class DecisionError(Exception):
    """Base exception for Decision Engine failures."""


class DecisionValidationError(DecisionError, ValueError):
    """Raised when decision input or configuration violates domain constraints."""


class DecisionEngineError(DecisionError):
    """Raised when the Decision Engine cannot complete an operation."""


class DecisionInputError(DecisionError):
    """Raised when decision input data is invalid or missing required fields."""
