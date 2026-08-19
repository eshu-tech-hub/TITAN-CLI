from collections.abc import Callable, Sequence
from typing import Any, cast

from titan.core.evidence import (
    Confidence,
    Evidence,
    EvidenceAggregator,
    EvidenceCategory,
    EvidenceSignal,
    Score,
)
from titan.options.analytics.base import OptionAnalyzer
from titan.options.analytics.models import (
    AnalysisResult,
    MarketBias,
    OptionChainAnalysis,
    OptionChainExplanation,
    OptionChainSnapshot,
)
from titan.options.analytics.oi import OpenInterestAnalyzer
from titan.options.analytics.pcr import PCRAnalyzer
from titan.options.analytics.support_resistance import SupportResistanceAnalyzer

DEFAULT_EVIDENCE_WEIGHT = 1.0
NEUTRAL_SCORE = 50.0
MAX_SCORE = 100.0
MIN_SCORE = 0.0
PERCENT_SCALE = 100.0


class OptionChainAnalyzer:
    """Coordinate option-chain analyzers into evidence-backed intelligence."""

    def __init__(self, analyzers: Sequence[OptionAnalyzer] | None = None) -> None:
        """Create the coordinator.

        Args:
            analyzers: Optional analyzer sequence. Defaults to the production
                M2.1.5 analyzers that emit non-placeholder intelligence.
        """

        self._analyzers = (
            tuple(analyzers)
            if analyzers is not None
            else (
                PCRAnalyzer(),
                SupportResistanceAnalyzer(),
                OpenInterestAnalyzer(),
            )
        )

    @property
    def analyzers(self) -> tuple[OptionAnalyzer, ...]:
        """Return configured analyzers."""

        return self._analyzers

    def analyze(self, snapshot: OptionChainSnapshot) -> OptionChainAnalysis:
        """Analyze an option-chain snapshot and aggregate universal evidence."""

        self._validate_snapshot(snapshot)
        results = tuple(analyzer.analyze(snapshot) for analyzer in self._analyzers)
        evidence = tuple(
            self._to_evidence(analyzer, result)
            for analyzer, result in zip(self._analyzers, results, strict=True)
        )
        aggregator = EvidenceAggregator()
        aggregator.extend(evidence)

        overall_score = aggregator.overall_score()
        overall_bias = self._bias_from_signal(aggregator.overall_signal())
        warnings = self._combined_warnings(results, evidence)
        metadata = self._metadata(results)
        explanation = self._explain(
            overall_bias, aggregator.overall_confidence(), evidence, warnings
        )

        return OptionChainAnalysis(
            overall_bias=overall_bias,
            confidence=aggregator.overall_confidence(),
            support=self._first_metadata_value(metadata, "support"),
            resistance=self._first_metadata_value(metadata, "resistance"),
            pcr=self._first_metadata_value(metadata, "pcr"),
            highest_put_strike=self._first_metadata_value(
                metadata, "highest_put_strike"
            ),
            highest_call_strike=self._first_metadata_value(
                metadata, "highest_call_strike"
            ),
            bullish_score=self._bullish_score(overall_score),
            bearish_score=self._bearish_score(overall_score),
            neutral_score=self._neutral_score(overall_score),
            warnings=warnings,
            evidence=evidence,
            explanation=explanation,
            metadata={
                "analyzer_results": metadata,
                "evidence_count": len(evidence),
                "score": overall_score,
            },
        )

    def _validate_snapshot(self, snapshot: OptionChainSnapshot) -> None:
        if not isinstance(snapshot, OptionChainSnapshot):
            raise TypeError("snapshot must be an OptionChainSnapshot.")
        if not snapshot.underlying.strip():
            raise ValueError("snapshot underlying cannot be empty.")

    def _to_evidence(
        self, analyzer: OptionAnalyzer, result: AnalysisResult
    ) -> Evidence:
        converter = getattr(analyzer, "to_evidence", None)
        if callable(converter):
            to_evidence = cast(Callable[[AnalysisResult], Evidence], converter)
            return to_evidence(result)

        return Evidence(
            source=analyzer.name,
            category=EvidenceCategory.OPTION_CHAIN,
            signal=self._signal_from_result(result),
            score=Score(result.score),
            confidence=Confidence(result.confidence),
            weight=DEFAULT_EVIDENCE_WEIGHT,
            reasons=result.reasons,
            warnings=result.warnings,
            metadata=result.metadata,
        )

    def _signal_from_result(self, result: AnalysisResult) -> EvidenceSignal:
        market_bias = result.metadata.get("market_bias")

        if market_bias is MarketBias.BULLISH or result.bullish:
            return EvidenceSignal.BULLISH
        if market_bias is MarketBias.BEARISH or result.bearish:
            return EvidenceSignal.BEARISH
        if market_bias is MarketBias.NEUTRAL or result.neutral:
            return EvidenceSignal.NEUTRAL
        return EvidenceSignal.UNKNOWN

    def _bias_from_signal(self, signal: EvidenceSignal) -> MarketBias:
        if signal in (EvidenceSignal.VERY_BULLISH, EvidenceSignal.BULLISH):
            return MarketBias.BULLISH
        if signal in (EvidenceSignal.VERY_BEARISH, EvidenceSignal.BEARISH):
            return MarketBias.BEARISH
        if signal is EvidenceSignal.NEUTRAL:
            return MarketBias.NEUTRAL
        return MarketBias.UNKNOWN

    def _combined_warnings(
        self,
        results: tuple[AnalysisResult, ...],
        evidence: tuple[Evidence, ...],
    ) -> tuple[str, ...]:
        warnings = [warning for result in results for warning in result.warnings]
        warnings.extend(warning for item in evidence for warning in item.warnings)
        return tuple(dict.fromkeys(warnings))

    def _metadata(
        self, results: tuple[AnalysisResult, ...]
    ) -> dict[str, dict[str, Any]]:
        return {
            analyzer.name: dict(result.metadata)
            for analyzer, result in zip(self._analyzers, results, strict=True)
        }

    def _first_metadata_value(
        self,
        metadata: dict[str, dict[str, Any]],
        key: str,
    ) -> Any:
        for analyzer_metadata in metadata.values():
            value = analyzer_metadata.get(key)
            if value is not None:
                return value
        return None

    def _bullish_score(self, score: float) -> float:
        return min(MAX_SCORE, max(MIN_SCORE, score))

    def _bearish_score(self, score: float) -> float:
        return min(MAX_SCORE, max(MIN_SCORE, MAX_SCORE - score))

    def _neutral_score(self, score: float) -> float:
        distance_from_neutral = abs(score - NEUTRAL_SCORE)
        return min(MAX_SCORE, max(MIN_SCORE, MAX_SCORE - (distance_from_neutral * 2.0)))

    def _explain(
        self,
        bias: MarketBias,
        confidence: float,
        evidence: tuple[Evidence, ...],
        warnings: tuple[str, ...],
    ) -> OptionChainExplanation:
        key_points = tuple(
            f"{item.source}: {reason}" for item in evidence for reason in item.reasons
        )
        summary = (
            f"Option chain bias is {bias.value} with "
            f"{confidence * PERCENT_SCALE:.0f}% confidence."
        )

        return OptionChainExplanation(
            summary=summary,
            key_points=key_points,
            warnings=warnings,
        )
