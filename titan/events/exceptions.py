class EventIntelligenceError(Exception):
    """Base exception for Event Intelligence errors."""


class EventValidationError(EventIntelligenceError):
    """Raised when event data validation fails."""


class EventAnalysisError(EventIntelligenceError):
    """Raised when event analysis processing fails."""
