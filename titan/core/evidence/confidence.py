from dataclasses import dataclass

from titan.core.evidence.exceptions import EvidenceValidationError

MIN_CONFIDENCE = 0.0
MAX_CONFIDENCE = 1.0


@dataclass(frozen=True, slots=True)
class Confidence:
    """Strongly typed confidence value from 0.0 to 1.0."""

    value: float

    def __post_init__(self) -> None:
        """Validate confidence range."""

        if not MIN_CONFIDENCE <= self.value <= MAX_CONFIDENCE:
            raise EvidenceValidationError("Confidence must be between 0.0 and 1.0.")

    def __float__(self) -> float:
        """Return confidence as a float."""

        return float(self.value)
