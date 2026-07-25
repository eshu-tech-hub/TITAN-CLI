from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping

from titan.core.evidence.confidence import Confidence
from titan.core.evidence.exceptions import EvidenceValidationError
from titan.core.evidence.models import EvidenceCategory, EvidenceSignal
from titan.core.evidence.score import Score

MIN_WEIGHT = 0.0


@dataclass(frozen=True, slots=True)
class Evidence:
    """Universal communication object shared by TITAN modules.

    Attributes:
        source: Producer name or subsystem identifier.
        category: Universal evidence category.
        signal: Directional signal.
        score: Normalized score from 0 to 100.
        confidence: Confidence from 0.0 to 1.0.
        weight: Non-negative aggregation weight.
        reasons: Human-readable reasons supporting the evidence.
        warnings: Non-fatal warnings from the producer.
        metadata: Additional producer-owned context.
        timestamp: Evidence creation or observation timestamp.
    """

    source: str
    category: EvidenceCategory
    signal: EvidenceSignal
    score: Score
    confidence: Confidence
    weight: float = 1.0
    reasons: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """Validate evidence invariants."""

        if not self.source.strip():
            raise EvidenceValidationError("Evidence source cannot be empty.")
        if self.weight < MIN_WEIGHT:
            raise EvidenceValidationError("Evidence weight cannot be negative.")
        if not isinstance(self.category, EvidenceCategory):
            raise EvidenceValidationError("Evidence category is invalid.")
        if not isinstance(self.signal, EvidenceSignal):
            raise EvidenceValidationError("Evidence signal is invalid.")
        if not isinstance(self.score, Score):
            raise EvidenceValidationError("Evidence score must be a Score object.")
        if not isinstance(self.confidence, Confidence):
            raise EvidenceValidationError(
                "Evidence confidence must be a Confidence object."
            )
        if not isinstance(self.timestamp, datetime):
            raise EvidenceValidationError("Evidence timestamp must be a datetime.")
