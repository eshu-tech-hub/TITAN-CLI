from dataclasses import dataclass, field

from titan.core.evidence.confidence import Confidence
from titan.core.evidence.evidence import Evidence
from titan.core.evidence.exceptions import EvidenceValidationError
from titan.core.evidence.models import EvidenceCategory, EvidenceSignal
from titan.core.evidence.score import Score

from titan.intelligence.fusion.exceptions import (
    FusionEngineError,
    FusionValidationError,
)
from titan.intelligence.fusion.explanation import FusionExplainer
from titan.intelligence.fusion.models import (
    ConflictType,
    EvidenceConflict,
    IntelligenceFusion,
)
from titan.intelligence.fusion.validator import (
    check_missing_categories,
    has_excessive_confidence,
    has_low_confidence,
    validate_evidence_list,
)
from titan.intelligence.fusion.weighting import (
    EqualWeightProvider,
    WeightProvider,
)

REQUIRED_CATEGORIES: tuple[EvidenceCategory, ...] = (
    EvidenceCategory.OPTION_CHAIN,
    EvidenceCategory.INDICATOR,
    EvidenceCategory.PRICE_ACTION,
)


@dataclass(slots=True)
class FusionEngine:
    """Central intelligence fusion engine.

    Fuses evidence from multiple intelligence modules into a unified
    IntelligenceFusion object. Knows only Evidence — never imports
    Option, Indicator, Broker, News, or Market modules.

    Attributes:
        weight_provider: Strategy for computing evidence weights.
        _evidence: Internal evidence storage.
        _explainer: Generates structured explanations.
    """

    weight_provider: WeightProvider = field(default_factory=EqualWeightProvider)
    _evidence: list[Evidence] = field(default_factory=list)
    _explainer: FusionExplainer = field(default_factory=FusionExplainer)

    def add_evidence(self, evidence: Evidence) -> None:
        """Add a single evidence item.

        Args:
            evidence: The evidence item to fuse.

        Raises:
            FusionEngineError: If evidence is invalid or already present.
        """

        try:
            validate_evidence_list([evidence])
        except (EvidenceValidationError, FusionValidationError) as exc:
            raise FusionEngineError(str(exc)) from exc

        if self._is_duplicate(evidence):
            raise FusionEngineError(
                f"Duplicate evidence from source '{evidence.source}' "
                f"in category '{evidence.category.value}'."
            )

        self._evidence.append(evidence)

    def remove_evidence(
        self,
        source: str,
        category: EvidenceCategory | None = None,
    ) -> int:
        """Remove evidence items matching the given source and optional category.

        Args:
            source: Source identifier to match.
            category: If provided, only remove evidence with this category.

        Returns:
            Number of evidence items removed.
        """

        before = len(self._evidence)
        self._evidence = [
            e
            for e in self._evidence
            if not (e.source == source and (category is None or e.category == category))
        ]
        return before - len(self._evidence)

    def clear(self) -> None:
        """Remove all evidence from the engine."""

        self._evidence.clear()

    def validate(self) -> list[str]:
        """Validate all current evidence and return non-fatal warnings.

        Returns:
            List of warning messages.
        """

        warnings: list[str] = []

        for evidence in self._evidence:
            if has_low_confidence(evidence):
                warnings.append(
                    f"Low confidence from '{evidence.source}': "
                    f"{float(evidence.confidence):.2f}"
                )
            if has_excessive_confidence(evidence):
                warnings.append(
                    f"Excessive confidence from '{evidence.source}': "
                    f"{float(evidence.confidence):.2f}"
                )

        return warnings

    def fuse(self) -> IntelligenceFusion:
        """Execute fusion: aggregate, detect conflicts, and produce result.

        Returns:
            A complete IntelligenceFusion object.

        Raises:
            FusionEngineError: If fusion cannot be completed.
        """

        if not self._evidence:
            return self._empty_fusion()

        weighted_evidence = self._apply_weights()

        overall_score = self._calculate_overall_score(weighted_evidence)
        overall_confidence = self._calculate_overall_confidence(weighted_evidence)
        overall_signal = self._determine_signal(overall_score)

        conflicts = self._detect_conflicts()
        missing = self._detect_missing_categories()

        warnings = self.validate()

        supporting_evidence = self._get_supporting_evidence(
            weighted_evidence, overall_signal
        )

        fusion = IntelligenceFusion(
            overall_score=Score(overall_score),
            overall_confidence=Confidence(overall_confidence),
            overall_signal=overall_signal,
            supporting_evidence=supporting_evidence,
            conflicting_evidence=conflicts,
            missing_categories=missing,
            warnings=tuple(warnings),
            metadata={
                "evidence_count": len(self._evidence),
                "weighted_count": len(weighted_evidence),
            },
            evidence_count=len(self._evidence),
        )

        return fusion

    def summary(self) -> Evidence:
        """Return an aggregate evidence summary of all current evidence.

        Returns:
            A synthetic Evidence object summarizing the fused state.
        """

        if not self._evidence:
            return Evidence(
                source="FusionEngine",
                category=EvidenceCategory.SYSTEM,
                signal=EvidenceSignal.UNKNOWN,
                score=Score(50.0),
                confidence=Confidence(0.0),
                weight=1.0,
                reasons=("No evidence loaded in FusionEngine.",),
                warnings=("No evidence items available.",),
                metadata={"count": 0},
            )

        fusion = self.fuse()
        return Evidence(
            source="FusionEngine",
            category=EvidenceCategory.SYSTEM,
            signal=fusion.overall_signal,
            score=fusion.overall_score,
            confidence=fusion.overall_confidence,
            weight=1.0,
            reasons=(f"Fused {len(self._evidence)} evidence items.",),
            warnings=fusion.warnings,
            metadata={
                "count": len(self._evidence),
                "conflicts": len(fusion.conflicting_evidence),
                "missing": len(fusion.missing_categories),
            },
        )

    def to_explanation(self) -> str:
        """Generate a structured explanation of the current fusion state.

        Returns:
            A structured multi-section explanation string.
        """

        fusion = self.fuse()
        return self._explainer.explain(fusion)

    def _is_duplicate(self, evidence: Evidence) -> bool:
        return any(
            e.source == evidence.source and e.category == evidence.category
            for e in self._evidence
        )

    def _apply_weights(self) -> list[tuple[Evidence, float]]:
        weighted: list[tuple[Evidence, float]] = []

        for evidence in self._evidence:
            weight = self.weight_provider.get_weight(evidence)

            if weight <= 0.0:
                continue

            weighted.append((evidence, weight))

        return weighted

    def _calculate_overall_score(
        self, evidence_items: list[tuple[Evidence, float]]
    ) -> float:
        if not evidence_items:
            return 50.0

        if not evidence_items:
            return 50.0

        weighted_total = sum(float(e.score) * w for e, w in evidence_items)
        total_weight = sum(w for _, w in evidence_items)

        if total_weight == 0.0:
            return 50.0

        return weighted_total / total_weight

    def _calculate_overall_confidence(
        self, evidence_items: list[tuple[Evidence, float]]
    ) -> float:
        if not evidence_items:
            return 0.0

        weighted_total = sum(float(e.confidence) * w for e, w in evidence_items)
        total_weight = sum(w for _, w in evidence_items)

        if total_weight == 0.0:
            return 0.0

        return weighted_total / total_weight

    def _determine_signal(self, score: float) -> EvidenceSignal:
        if score >= 80.0:
            return EvidenceSignal.VERY_BULLISH
        if score >= 60.0:
            return EvidenceSignal.BULLISH
        if score <= 20.0:
            return EvidenceSignal.VERY_BEARISH
        if score <= 40.0:
            return EvidenceSignal.BEARISH
        return EvidenceSignal.NEUTRAL

    def _detect_conflicts(self) -> tuple[EvidenceConflict, ...]:
        conflicts: list[EvidenceConflict] = []

        bullish_vs_bearish = self._detect_directional_conflicts()
        conflicts.extend(bullish_vs_bearish)

        low_conf = self._detect_low_confidence_items()
        conflicts.extend(low_conf)

        return tuple(conflicts)

    def _detect_directional_conflicts(self) -> list[EvidenceConflict]:
        bullish: list[Evidence] = [
            e
            for e in self._evidence
            if e.signal in (EvidenceSignal.BULLISH, EvidenceSignal.VERY_BULLISH)
        ]
        bearish: list[Evidence] = [
            e
            for e in self._evidence
            if e.signal in (EvidenceSignal.BEARISH, EvidenceSignal.VERY_BEARISH)
        ]

        if bullish and bearish:
            return [
                EvidenceConflict(
                    conflict_type=ConflictType.BULLISH_VS_BEARISH,
                    reason=(
                        f"{len(bullish)} bullish evidence item(s) conflict "
                        f"with {len(bearish)} bearish evidence item(s)."
                    ),
                    evidence_items=tuple(bullish + bearish),
                )
            ]

        return []

    def _detect_low_confidence_items(self) -> list[EvidenceConflict]:
        low_conf_items = tuple(e for e in self._evidence if has_low_confidence(e))

        if low_conf_items:
            return [
                EvidenceConflict(
                    conflict_type=ConflictType.LOW_CONFIDENCE,
                    reason=(
                        f"{len(low_conf_items)} evidence item(s) "
                        "have very low confidence."
                    ),
                    evidence_items=low_conf_items,
                )
            ]

        return []

    def _detect_missing_categories(self) -> tuple[EvidenceCategory, ...]:
        return check_missing_categories(self._evidence, REQUIRED_CATEGORIES)

    def _get_supporting_evidence(
        self,
        evidence_items: list[tuple[Evidence, float]],
        overall_signal: EvidenceSignal,
    ) -> tuple[Evidence, ...]:
        if overall_signal in (
            EvidenceSignal.BULLISH,
            EvidenceSignal.VERY_BULLISH,
        ):
            return tuple(
                e
                for e, _ in evidence_items
                if e.signal in (EvidenceSignal.BULLISH, EvidenceSignal.VERY_BULLISH)
            )

        if overall_signal in (
            EvidenceSignal.BEARISH,
            EvidenceSignal.VERY_BEARISH,
        ):
            return tuple(
                e
                for e, _ in evidence_items
                if e.signal in (EvidenceSignal.BEARISH, EvidenceSignal.VERY_BEARISH)
            )

        return tuple(e for e, _ in evidence_items)

    def _sort_by_confidence(
        self, evidence_items: list[tuple[Evidence, float]]
    ) -> list[tuple[Evidence, float]]:
        return sorted(
            evidence_items,
            key=lambda pair: (
                float(pair[0].confidence),
                float(pair[0].score),
            ),
            reverse=True,
        )

    def _empty_fusion(self) -> IntelligenceFusion:
        return IntelligenceFusion(
            overall_score=Score(50.0),
            overall_confidence=Confidence(0.0),
            overall_signal=EvidenceSignal.UNKNOWN,
            supporting_evidence=(),
            warnings=("No evidence to fuse.",),
            metadata={"evidence_count": 0, "weighted_count": 0},
            evidence_count=0,
        )
