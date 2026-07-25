class FusionError(Exception):
    """Base exception for Intelligence Fusion Engine failures."""


class FusionValidationError(FusionError, ValueError):
    """Raised when evidence or configuration violates fusion domain constraints."""


class FusionEngineError(FusionError):
    """Raised when the fusion engine cannot complete an operation."""
