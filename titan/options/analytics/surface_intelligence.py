from typing import Any

from titan.core.evidence import (
    Confidence,
    Evidence,
    EvidenceCategory,
    EvidenceSignal,
    Score,
)
from titan.options.analytics.models import (
    MarketBias,
    SkewAnalysis,
    SmileAnalysis,
    SurfaceAnomaly,
    SurfaceComponentScore,
    SurfaceConsistency,
    SurfaceConsistencyLevel,
    SurfaceExplanation,
    SurfaceHealth,
    SurfaceHealthLevel,
    SurfaceIntelligenceAnalysis,
    TermStructureAnalysis,
    VolatilityAnalysis,
    VolatilitySurfaceInput,
)
from titan.options.analytics.surface_anomalies import SurfaceAnomalyAnalyzer
from titan.options.analytics.surface_consistency import SurfaceConsistencyAnalyzer
from titan.options.analytics.surface_health import SurfaceHealthAnalyzer

NEUTRAL_SCORE = 50.0
SIGNAL_BULLISH = {EvidenceSignal.BULLISH, EvidenceSignal.VERY_BULLISH}
SIGNAL_BEARISH = {EvidenceSignal.BEARISH, EvidenceSignal.VERY_BEARISH}


class SurfaceIntelligenceAnalyzer:
    """Orchestrate volatility surface intelligence.

    Consumes VolatilityAnalysis, SmileAnalysis, SkewAnalysis, and
    TermStructureAnalysis to produce a unified institutional surface
    assessment. This is a pure orchestrator — it does not recalculate
    any volatility metric, smile, skew, or term structure computation.
    """

    name = "SurfaceIntelligenceAnalyzer"

    def __init__(
        self,
        health_analyzer: SurfaceHealthAnalyzer | None = None,
        consistency_analyzer: SurfaceConsistencyAnalyzer | None = None,
        anomaly_analyzer: SurfaceAnomalyAnalyzer | None = None,
    ) -> None:
        self._health = health_analyzer or SurfaceHealthAnalyzer()
        self._consistency = consistency_analyzer or SurfaceConsistencyAnalyzer()
        self._anomalies = anomaly_analyzer or SurfaceAnomalyAnalyzer()

    def analyze(
        self,
        volatility: VolatilityAnalysis | None = None,
        smile: SmileAnalysis | None = None,
        skew: SkewAnalysis | None = None,
        term_structure: TermStructureAnalysis | None = None,
    ) -> SurfaceIntelligenceAnalysis:
        surface = VolatilitySurfaceInput(
            volatility=volatility,
            smile=smile,
            skew=skew,
            term_structure=term_structure,
        )

        if all(v is None for v in (volatility, smile, skew, term_structure)):
            return self._empty_analysis("No volatility intelligence data provided.")

        health = self._health.analyze(surface)
        consistency = self._consistency.analyze(surface)
        anomaly_result = self._anomalies.analyze(surface)

        component_scores = self._build_component_scores(surface)
        overall_bias = self._derive_bias(component_scores)
        institutional_confidence = self._calculate_confidence(component_scores)
        warnings = self._combine_warnings(surface)

        analysis = SurfaceIntelligenceAnalysis(
            health=health.level,
            consistency=consistency.level,
            overall_bias=overall_bias,
            institutional_confidence=institutional_confidence,
            component_scores=component_scores,
            anomalies=anomaly_result.anomalies,
            warnings=warnings,
            metadata=self._metadata(surface, health, consistency),
        )

        evidence = self._to_evidence(analysis, component_scores)
        explanation = self._explanation(analysis, health, consistency, anomaly_result)

        object.__setattr__(analysis, "evidence", evidence)
        object.__setattr__(analysis, "explanation", explanation)

        return analysis

    def _build_component_scores(
        self,
        surface: VolatilitySurfaceInput,
    ) -> tuple[SurfaceComponentScore, ...]:
        scores: list[SurfaceComponentScore] = []

        vol_score, vol_conf, vol_sig = self._extract_component(surface.volatility)
        scores.append(
            SurfaceComponentScore(
                name="Volatility",
                score=vol_score,
                confidence=vol_conf,
                signal=vol_sig,
                available=surface.volatility is not None,
            )
        )

        smile_score, smile_conf, smile_sig = self._extract_component(surface.smile)
        scores.append(
            SurfaceComponentScore(
                name="Smile",
                score=smile_score,
                confidence=smile_conf,
                signal=smile_sig,
                available=surface.smile is not None,
            )
        )

        skew_score, skew_conf, skew_sig = self._extract_component(surface.skew)
        scores.append(
            SurfaceComponentScore(
                name="Skew",
                score=skew_score,
                confidence=skew_conf,
                signal=skew_sig,
                available=surface.skew is not None,
            )
        )

        ts_score, ts_conf, ts_sig = self._extract_component(surface.term_structure)
        scores.append(
            SurfaceComponentScore(
                name="Term Structure",
                score=ts_score,
                confidence=ts_conf,
                signal=ts_sig,
                available=surface.term_structure is not None,
            )
        )

        return tuple(scores)

    def _extract_component(
        self,
        component: object | None,
    ) -> tuple[float, float, EvidenceSignal | None]:
        if component is None:
            return NEUTRAL_SCORE, 0.0, None
        evidence = getattr(component, "evidence", None)
        if evidence is None:
            return NEUTRAL_SCORE, getattr(component, "confidence", 0.0), None
        return (
            float(getattr(evidence, "score", Score(NEUTRAL_SCORE))),
            float(getattr(evidence, "confidence", Confidence(0.0))),
            getattr(evidence, "signal", None),
        )

    def _derive_bias(
        self,
        scores: tuple[SurfaceComponentScore, ...],
    ) -> MarketBias:
        available = [s for s in scores if s.available and s.signal is not None]
        if not available:
            return MarketBias.UNKNOWN

        directional = [
            s for s in available if s.signal in SIGNAL_BULLISH | SIGNAL_BEARISH
        ]
        if not directional:
            return MarketBias.NEUTRAL

        bullish_count = sum(1 for s in directional if s.signal in SIGNAL_BULLISH)
        bearish_count = sum(1 for s in directional if s.signal in SIGNAL_BEARISH)

        if bullish_count > bearish_count:
            return MarketBias.BULLISH
        if bearish_count > bullish_count:
            return MarketBias.BEARISH

        return MarketBias.NEUTRAL

    def _calculate_confidence(
        self,
        scores: tuple[SurfaceComponentScore, ...],
    ) -> float:
        available = [s for s in scores if s.available]
        if not available:
            return 0.0
        confidences = [s.confidence for s in available]
        return sum(confidences) / len(confidences)

    def _combine_warnings(
        self,
        surface: VolatilitySurfaceInput,
    ) -> tuple[str, ...]:
        combined: list[str] = []
        components = [
            ("Volatility", surface.volatility),
            ("Smile", surface.smile),
            ("Skew", surface.skew),
            ("Term Structure", surface.term_structure),
        ]

        for name, comp in components:
            if comp is not None:
                warnings = getattr(comp, "warnings", ())
                for w in warnings:
                    combined.append(f"[{name}] {w}")

        return tuple(combined)

    def _metadata(
        self,
        surface: VolatilitySurfaceInput,
        health: SurfaceHealth,
        consistency: SurfaceConsistency,
    ) -> dict[str, Any]:
        return {
            "analyzer": self.name,
            "health": health.level.value,
            "consistency": consistency.level.value,
            "volatility_available": surface.volatility is not None,
            "smile_available": surface.smile is not None,
            "skew_available": surface.skew is not None,
            "term_structure_available": surface.term_structure is not None,
        }

    # ------------------------------------------------------------------
    # Evidence generation
    # ------------------------------------------------------------------

    def _evidence_signal(
        self,
        bias: MarketBias,
    ) -> EvidenceSignal:
        mapping = {
            MarketBias.BULLISH: EvidenceSignal.BULLISH,
            MarketBias.BEARISH: EvidenceSignal.BEARISH,
            MarketBias.NEUTRAL: EvidenceSignal.NEUTRAL,
        }
        return mapping.get(bias, EvidenceSignal.UNKNOWN)

    def _evidence_score(
        self,
        scores: tuple[SurfaceComponentScore, ...],
    ) -> float:
        available = [s for s in scores if s.available]
        if not available:
            return NEUTRAL_SCORE

        weighted_sum = sum(s.score * s.confidence for s in available)
        total_weight = sum(s.confidence for s in available)

        if total_weight <= 0:
            return NEUTRAL_SCORE
        return weighted_sum / total_weight

    def _evidence_reasons(
        self,
        analysis: SurfaceIntelligenceAnalysis,
    ) -> tuple[str, ...]:
        reasons: list[str] = []

        if analysis.health is not SurfaceHealthLevel.UNKNOWN:
            reasons.append(f"Surface health is {analysis.health.value}.")
        if analysis.consistency is not SurfaceConsistencyLevel.UNKNOWN:
            reasons.append(f"Surface consistency is {analysis.consistency.value}.")
        if analysis.overall_bias is not MarketBias.UNKNOWN:
            reasons.append(f"Overall surface bias is {analysis.overall_bias.value}.")

        available = [s for s in analysis.component_scores if s.available]
        if available:
            names = [s.name for s in available]
            reasons.append(
                f"Active components: {', '.join(names)} ({len(available)}/4)."
            )

        if analysis.anomalies:
            reasons.append(f"{len(analysis.anomalies)} surface anomaly/ies detected.")

        return tuple(reasons)

    def _to_evidence(
        self,
        analysis: SurfaceIntelligenceAnalysis,
        component_scores: tuple[SurfaceComponentScore, ...],
    ) -> Evidence:
        signal = self._evidence_signal(analysis.overall_bias)
        score = self._evidence_score(component_scores)
        confidence = analysis.institutional_confidence

        return Evidence(
            source="Volatility Surface",
            category=EvidenceCategory.OPTION_CHAIN,
            signal=signal,
            score=Score(score),
            confidence=Confidence(confidence),
            weight=1.0,
            reasons=self._evidence_reasons(analysis),
            warnings=analysis.warnings,
            metadata={
                "analyzer": self.name,
                "surface_health": analysis.health.value,
                "surface_consistency": analysis.consistency.value,
                "overall_bias": analysis.overall_bias.value,
                "anomaly_count": len(analysis.anomalies),
                "component_count": len([s for s in component_scores if s.available]),
            },
        )

    # ------------------------------------------------------------------
    # Explanation generation
    # ------------------------------------------------------------------

    def _explanation(
        self,
        analysis: SurfaceIntelligenceAnalysis,
        health: SurfaceHealth,
        consistency: SurfaceConsistency,
        anomaly_result: object,
    ) -> SurfaceExplanation:
        anomalies_list: tuple[SurfaceAnomaly, ...] = getattr(
            anomaly_result, "anomalies", ()
        )

        return SurfaceExplanation(
            overall_surface=self._overall_section(analysis),
            health=self._health_section(analysis, health),
            consistency=self._consistency_section(analysis, consistency),
            anomalies=self._anomalies_section(anomalies_list),
            institutional_interpretation=self._institutional_section(analysis),
            risk_assessment=self._risk_section(analysis),
        )

    def _overall_section(self, analysis: SurfaceIntelligenceAnalysis) -> str:
        parts: list[str] = ["Volatility Surface Intelligence Assessment:"]

        if analysis.health is not SurfaceHealthLevel.UNKNOWN:
            parts.append(f"Surface health is {analysis.health.value}.")
        if analysis.consistency is not SurfaceConsistencyLevel.UNKNOWN:
            parts.append(f"Cross-module consistency is {analysis.consistency.value}.")
        if analysis.overall_bias is not MarketBias.UNKNOWN:
            parts.append(f"Aggregated surface bias is {analysis.overall_bias.value}.")
        if analysis.institutional_confidence > 0:
            parts.append(
                f"Institutional confidence is {analysis.institutional_confidence:.0%}."
            )

        return " ".join(parts)

    def _health_section(
        self,
        analysis: SurfaceIntelligenceAnalysis,
        health: SurfaceHealth,
    ) -> str:
        parts: list[str] = ["Surface Health:"]

        parts.append(health.reason)

        if health.component_status:
            statuses = [
                f"{name}={status}" for name, status in health.component_status.items()
            ]
            parts.append(f"Component status: {', '.join(statuses)}.")

        return " ".join(parts)

    def _consistency_section(
        self,
        analysis: SurfaceIntelligenceAnalysis,
        consistency: SurfaceConsistency,
    ) -> str:
        parts: list[str] = ["Surface Consistency:"]

        parts.append(consistency.details)

        if consistency.conflicts:
            for conflict in consistency.conflicts:
                parts.append(f"Conflict: {conflict}")

        return " ".join(parts)

    def _anomalies_section(
        self,
        anomalies: tuple[SurfaceAnomaly, ...],
    ) -> str:
        if not anomalies:
            return "Surface Anomalies: No anomalies detected."

        parts: list[str] = [
            f"Surface Anomalies: {len(anomalies)} anomaly/ies detected."
        ]
        for i, anomaly in enumerate(anomalies, 1):
            parts.append(f"  [{i}] {anomaly.source}: {anomaly.description}")

        return " ".join(parts)

    def _institutional_section(self, analysis: SurfaceIntelligenceAnalysis) -> str:
        parts: list[str] = ["Institutional Interpretation:"]

        if analysis.health in (
            SurfaceHealthLevel.HEALTHY,
            SurfaceHealthLevel.GOOD,
        ):
            parts.append(
                "The volatility surface is functional and reliable. "
                "Standard volatility analytics apply."
            )
        elif analysis.health is SurfaceHealthLevel.CAUTION:
            parts.append(
                "Surface quality is degraded. Cross-reference surface "
                "intelligence with other market indicators before "
                "making trading decisions."
            )
        elif analysis.health in (
            SurfaceHealthLevel.UNHEALTHY,
            SurfaceHealthLevel.UNKNOWN,
        ):
            parts.append(
                "Surface quality is insufficient for reliable analysis. "
                "Seek alternative data sources or wait for market "
                "conditions to improve."
            )

        if analysis.overall_bias is MarketBias.BULLISH:
            parts.append(
                "Components consistently indicate bullish bias. "
                "Consider upside strategies with appropriate risk management."
            )
        elif analysis.overall_bias is MarketBias.BEARISH:
            parts.append(
                "Components consistently indicate bearish bias. "
                "Consider defensive positioning or tail-risk hedges."
            )
        elif analysis.consistency is SurfaceConsistencyLevel.INCONSISTENT:
            parts.append(
                "Conflicting signals across components suggest an "
                "uncertain or transitioning market regime. Exercise caution."
            )

        return " ".join(parts)

    def _risk_section(self, analysis: SurfaceIntelligenceAnalysis) -> str:
        parts: list[str] = ["Risk Assessment:"]

        if analysis.anomalies:
            parts.append(
                f"{len(analysis.anomalies)} surface anomaly/ies detected. "
                "Review anomaly details for specific risk factors."
            )

        if analysis.institutional_confidence < 0.5:
            parts.append(
                "Low institutional confidence reduces the reliability "
                "of surface-derived signals. Position sizing should "
                "account for increased uncertainty."
            )

        if analysis.consistency is SurfaceConsistencyLevel.INCONSISTENT:
            parts.append(
                "Cross-module inconsistency increases the risk of "
                "false signals. Avoid high-conviction positioning "
                "until agreement improves."
            )

        return " ".join(parts)

    def _empty_analysis(self, reason: str) -> SurfaceIntelligenceAnalysis:
        analysis = SurfaceIntelligenceAnalysis.neutral_placeholder()
        object.__setattr__(analysis, "warnings", (reason,))
        explanation = SurfaceExplanation(
            overall_surface="Volatility surface intelligence is unavailable.",
            health="Surface health cannot be determined: no data available.",
            consistency="Surface consistency cannot be determined: no data available.",
            anomalies="No anomalies to report.",
            institutional_interpretation="Institutional Interpretation: Surface data is unavailable.",
            risk_assessment="Risk Assessment: Surface data is unavailable.",
        )
        object.__setattr__(analysis, "explanation", explanation)
        return analysis
