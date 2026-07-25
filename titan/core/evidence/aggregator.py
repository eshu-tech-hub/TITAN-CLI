from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field

from titan.core.evidence.confidence import Confidence
from titan.core.evidence.evidence import Evidence
from titan.core.evidence.exceptions import EvidenceValidationError
from titan.core.evidence.models import EvidenceCategory, EvidenceSignal
from titan.core.evidence.score import Score

MIN_BULLISH_SCORE = 60.0
MIN_VERY_BULLISH_SCORE = 80.0
MAX_BEARISH_SCORE = 40.0
MAX_VERY_BEARISH_SCORE = 20.0
UNKNOWN_CONFIDENCE = 0.0
DEFAULT_SCORE = 50.0


@dataclass(slots=True)
class EvidenceAggregator:
    """Aggregates universal Evidence objects without producer knowledge."""

    _items: list[Evidence] = field(default_factory=list)

    def add(self, evidence: Evidence) -> None:
        """Add one evidence item.

        Args:
            evidence: Evidence object to include.

        Raises:
            EvidenceValidationError: If the input is not Evidence.
        """

        if not isinstance(evidence, Evidence):
            raise EvidenceValidationError("Aggregator only accepts Evidence objects.")
        self._items.append(evidence)

    def extend(self, evidence_items: Sequence[Evidence]) -> None:
        """Add multiple evidence items.

        Args:
            evidence_items: Evidence objects to include.
        """

        for evidence in evidence_items:
            self.add(evidence)

    def clear(self) -> None:
        """Remove all evidence items."""

        self._items.clear()

    def summary(self) -> Evidence:
        """Return aggregate evidence summary.

        Returns:
            A synthetic Evidence object summarizing all current evidence.
        """

        return Evidence(
            source="EvidenceAggregator",
            category=EvidenceCategory.SYSTEM,
            signal=self.overall_signal(),
            score=Score(self.overall_score()),
            confidence=Confidence(self.overall_confidence()),
            weight=1.0,
            reasons=(f"Aggregated {len(self._items)} evidence items.",),
            warnings=() if self._items else ("No evidence items available.",),
            metadata={"count": len(self._items)},
        )

    def overall_score(self) -> float:
        """Return weighted average score."""

        if not self._items:
            return DEFAULT_SCORE

        weighted_total = sum(float(item.score) * item.weight for item in self._items)
        total_weight = sum(item.weight for item in self._items)

        if total_weight == 0:
            return DEFAULT_SCORE

        return weighted_total / total_weight

    def overall_confidence(self) -> float:
        """Return weighted average confidence."""

        if not self._items:
            return UNKNOWN_CONFIDENCE

        weighted_total = sum(
            float(item.confidence) * item.weight for item in self._items
        )
        total_weight = sum(item.weight for item in self._items)

        if total_weight == 0:
            return UNKNOWN_CONFIDENCE

        return weighted_total / total_weight

    def overall_signal(self) -> EvidenceSignal:
        """Determine aggregate signal from the weighted average score."""

        score = self.overall_score()

        if not self._items:
            return EvidenceSignal.UNKNOWN
        if score >= MIN_VERY_BULLISH_SCORE:
            return EvidenceSignal.VERY_BULLISH
        if score >= MIN_BULLISH_SCORE:
            return EvidenceSignal.BULLISH
        if score <= MAX_VERY_BEARISH_SCORE:
            return EvidenceSignal.VERY_BEARISH
        if score <= MAX_BEARISH_SCORE:
            return EvidenceSignal.BEARISH
        return EvidenceSignal.NEUTRAL

    def group_by_category(self) -> dict[EvidenceCategory, tuple[Evidence, ...]]:
        """Group evidence items by category.

        Returns:
            Evidence items keyed by category.
        """

        grouped: dict[EvidenceCategory, list[Evidence]] = defaultdict(list)

        for evidence in self._items:
            grouped[evidence.category].append(evidence)

        return {
            category: tuple(
                sorted(items, key=lambda evidence: evidence.timestamp, reverse=True)
            )
            for category, items in grouped.items()
        }
