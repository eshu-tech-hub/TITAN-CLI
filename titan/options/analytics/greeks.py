from collections.abc import Sequence
from typing import Any

from titan.core.evidence import (
    Confidence,
    Evidence,
    EvidenceAggregator,
    EvidenceCategory,
    EvidenceSignal,
    Score,
)
from titan.options.analytics.base import OptionAnalyzer
from titan.options.analytics.delta import DeltaAnalyzer
from titan.options.analytics.gamma import GammaAnalyzer
from titan.options.analytics.models import (
    AnalysisResult,
    GreeksAnalysis,
    GreeksExplanation,
    MarketBias,
    OptionChainSnapshot,
)
from titan.options.analytics.theta import ThetaAnalyzer
from titan.options.analytics.vega import VegaAnalyzer

DEFAULT_SCORE = 50.0
PERCENT_SCALE = 100.0


class GreeksAnalyzer:
    """Coordinate broker-independent Greeks intelligence."""

    def __init__(self, analyzers: Sequence[OptionAnalyzer] | None = None) -> None:
        """Create the Greeks coordinator."""

        self._analyzers = (
            tuple(analyzers)
            if analyzers is not None
            else (
                DeltaAnalyzer(),
                GammaAnalyzer(),
                ThetaAnalyzer(),
                VegaAnalyzer(),
            )
        )

    @property
    def analyzers(self) -> tuple[OptionAnalyzer, ...]:
        """Return configured Greek analyzers."""

        return self._analyzers

    def analyze(self, snapshot: OptionChainSnapshot) -> GreeksAnalysis:
        """Analyze supplied Greeks and return evidence-backed output."""

        self._validate_snapshot(snapshot)
        results = tuple(analyzer.analyze(snapshot) for analyzer in self._analyzers)
        component_evidence = tuple(
            self._component_evidence(analyzer, result)
            for analyzer, result in zip(self._analyzers, results, strict=True)
        )
        aggregator = EvidenceAggregator()
        aggregator.extend(component_evidence)

        warnings = self._warnings(results)
        metadata = self._metadata(results)
        overall_bias = self._bias_from_signal(aggregator.overall_signal())
        evidence = self._overall_evidence(
            aggregator,
            component_evidence,
            warnings,
            metadata,
        )
        explanation = self._explanation(
            results, overall_bias, aggregator.overall_confidence(), warnings
        )

        return GreeksAnalysis(
            net_delta=self._value(metadata, "DeltaAnalyzer", "net_delta"),
            net_gamma=self._value(metadata, "GammaAnalyzer", "net_gamma"),
            net_theta=self._value(metadata, "ThetaAnalyzer", "net_theta"),
            net_vega=self._value(metadata, "VegaAnalyzer", "net_vega"),
            average_delta=self._value(metadata, "DeltaAnalyzer", "average_delta"),
            average_gamma=self._value(metadata, "GammaAnalyzer", "average_gamma"),
            average_theta=self._value(metadata, "ThetaAnalyzer", "average_theta"),
            average_vega=self._value(metadata, "VegaAnalyzer", "average_vega"),
            overall_bias=overall_bias,
            confidence=aggregator.overall_confidence(),
            warnings=warnings,
            metadata={
                "analyzer_results": metadata,
                "component_evidence": component_evidence,
                "future_extensions": (
                    "gamma_exposure",
                    "dealer_positioning",
                    "volatility_surface",
                    "volatility_smile",
                    "volatility_skew",
                    "charm",
                    "vanna",
                    "vomma",
                ),
            },
            evidence=evidence,
            explanation=explanation,
        )

    def to_evidence(self, analysis: GreeksAnalysis) -> Evidence:
        """Return the aggregate Greeks evidence from an analysis."""

        if not isinstance(analysis, GreeksAnalysis):
            raise TypeError("analysis must be a GreeksAnalysis.")
        if analysis.evidence is None:
            raise ValueError("GreeksAnalysis does not contain evidence.")
        return analysis.evidence

    def _validate_snapshot(self, snapshot: OptionChainSnapshot) -> None:
        if not isinstance(snapshot, OptionChainSnapshot):
            raise TypeError("snapshot must be an OptionChainSnapshot.")
        if not snapshot.underlying.strip():
            raise ValueError("snapshot underlying cannot be empty.")

    def _component_evidence(
        self,
        analyzer: OptionAnalyzer,
        result: AnalysisResult,
    ) -> Evidence:
        converter = getattr(analyzer, "to_evidence", None)
        if not callable(converter):
            return Evidence(
                source="Greeks",
                category=EvidenceCategory.OPTION_CHAIN,
                signal=self._signal_from_result(result),
                score=Score(result.score),
                confidence=Confidence(result.confidence),
                weight=1.0,
                reasons=result.reasons,
                warnings=result.warnings,
                metadata=result.metadata,
            )
        return Evidence(
            source="Greeks",
            category=EvidenceCategory.OPTION_CHAIN,
            signal=self._signal_from_result(result),
            score=Score(result.score),
            confidence=Confidence(result.confidence),
            weight=1.0,
            reasons=result.reasons,
            warnings=result.warnings,
            metadata=result.metadata,
        )

    def _overall_evidence(
        self,
        aggregator: EvidenceAggregator,
        component_evidence: tuple[Evidence, ...],
        warnings: tuple[str, ...],
        metadata: dict[str, dict[str, Any]],
    ) -> Evidence:
        return Evidence(
            source="Greeks",
            category=EvidenceCategory.OPTION_CHAIN,
            signal=aggregator.overall_signal(),
            score=Score(aggregator.overall_score()),
            confidence=Confidence(aggregator.overall_confidence()),
            weight=1.0,
            reasons=self._reasons(component_evidence),
            warnings=warnings,
            metadata={
                "analyzer_results": metadata,
                "component_count": len(component_evidence),
            },
        )

    def _explanation(
        self,
        results: tuple[AnalysisResult, ...],
        overall_bias: MarketBias,
        confidence: float,
        warnings: tuple[str, ...],
    ) -> GreeksExplanation:
        sections = {
            analyzer.name: self._section(analyzer, result)
            for analyzer, result in zip(self._analyzers, results, strict=True)
        }
        return GreeksExplanation(
            delta=sections.get("DeltaAnalyzer", "Delta analysis unavailable."),
            gamma=sections.get("GammaAnalyzer", "Gamma analysis unavailable."),
            theta=sections.get("ThetaAnalyzer", "Theta analysis unavailable."),
            vega=sections.get("VegaAnalyzer", "Vega analysis unavailable."),
            overall=(
                f"Overall Greeks bias is {overall_bias.value} with "
                f"{confidence * PERCENT_SCALE:.0f}% confidence."
            ),
            warnings=warnings,
        )

    def _section(self, analyzer: OptionAnalyzer, result: AnalysisResult) -> str:
        explainer = getattr(analyzer, "explanation", None)
        if callable(explainer):
            return str(explainer(result))
        if not result.reasons:
            return f"{analyzer.name} produced no explanation reasons."
        return " ".join(result.reasons)

    def _metadata(
        self, results: tuple[AnalysisResult, ...]
    ) -> dict[str, dict[str, Any]]:
        return {
            analyzer.name: dict(result.metadata)
            for analyzer, result in zip(self._analyzers, results, strict=True)
        }

    def _warnings(self, results: tuple[AnalysisResult, ...]) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(warning for result in results for warning in result.warnings)
        )

    def _reasons(self, component_evidence: tuple[Evidence, ...]) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                reason for evidence in component_evidence for reason in evidence.reasons
            )
        )

    def _value(
        self,
        metadata: dict[str, dict[str, Any]],
        analyzer_name: str,
        key: str,
    ) -> float | None:
        value = metadata.get(analyzer_name, {}).get(key)
        if value is None:
            return None
        return float(value)

    def _bias_from_signal(self, signal: EvidenceSignal) -> MarketBias:
        if signal in (EvidenceSignal.VERY_BULLISH, EvidenceSignal.BULLISH):
            return MarketBias.BULLISH
        if signal in (EvidenceSignal.VERY_BEARISH, EvidenceSignal.BEARISH):
            return MarketBias.BEARISH
        if signal is EvidenceSignal.NEUTRAL:
            return MarketBias.NEUTRAL
        return MarketBias.UNKNOWN

    def _signal_from_result(self, result: AnalysisResult) -> EvidenceSignal:
        if result.bullish:
            return EvidenceSignal.BULLISH
        if result.bearish:
            return EvidenceSignal.BEARISH
        if result.neutral:
            return EvidenceSignal.NEUTRAL
        return EvidenceSignal.UNKNOWN
