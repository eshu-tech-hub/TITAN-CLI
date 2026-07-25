from dataclasses import dataclass

from titan.core.evidence.exceptions import EvidenceValidationError

MIN_SCORE = 0.0
MAX_SCORE = 100.0


@dataclass(frozen=True, slots=True)
class Score:
    """Strongly typed evidence score from 0 to 100."""

    value: float

    def __post_init__(self) -> None:
        """Validate score range."""

        if not MIN_SCORE <= self.value <= MAX_SCORE:
            raise EvidenceValidationError("Score must be between 0 and 100.")

    def __float__(self) -> float:
        """Return score as a float."""

        return float(self.value)
