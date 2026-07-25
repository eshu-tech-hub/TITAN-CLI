class EvidenceError(Exception):
    """Base exception for evidence engine failures."""


class EvidenceValidationError(EvidenceError, ValueError):
    """Raised when an evidence object or value violates domain constraints."""


class EvidenceAggregationError(EvidenceError):
    """Raised when evidence aggregation cannot be completed."""
