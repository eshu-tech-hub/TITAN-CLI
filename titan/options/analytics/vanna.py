"""Vanna Exposure (VEX) Intelligence Engine Orchestrator.

Provides institutional Vanna intelligence using supplied option analytics.
Vanna measures dealer delta sensitivity to changes in implied volatility
— a critical input for understanding volatility-driven hedging pressure.

Pure orchestrator — no broker imports, no API calls, no Black-Scholes.
Consumes supplied Vanna, Greeks, and analysis objects only.

Integrates with:
  - Evidence Engine
  - Intelligence Fusion Engine
  - Dealer Positioning Intelligence
  - Gamma Exposure Intelligence
"""

from typing import Any

from titan.core.evidence import (
    Confidence,
    Evidence,
    EvidenceCategory,
    EvidenceSignal,
    Score,
)

from titan.options.analytics.models import (
    DealerPositioningAnalysis,
    GammaExposureAnalysis,
    GreeksAnalysis,
    OptionChainAnalysis,
    OptionChainSnapshot,
    SurfaceIntelligenceAnalysis,
    VannaExposureAnalysis,
    VannaExposureInput,
    VannaExplanation,
    VannaPressure,
    VannaPressureLevel,
    VannaRegime,
    VannaRegimeType,
)
from titan.options.analytics.vanna_pressure import VannaPressureAnalyzer
from titan.options.analytics.vanna_regime import VannaRegimeAnalyzer

POSITIVE_VANNA_SCORE = 65.0
NEGATIVE_VANNA_SCORE = 35.0
NEUTRAL_SCORE = 50.0

CONFIDENCE_LOW = 0.3
CONFIDENCE_MODERATE = 0.5
CONFIDENCE_HIGH = 0.7


class VannaExposureAnalyzer:
    """Orchestrate vanna exposure intelligence.

    Consumes DealerPositioningAnalysis, GammaExposureAnalysis,
    GreeksAnalysis, SurfaceIntelligenceAnalysis, OptionChainAnalysis,
    and OptionChainSnapshot to produce a unified institutional
    assessment of vanna exposure.  Pure orchestrator — does not
    recalculate any option metric or greek.
    """

    name = "VannaExposureAnalyzer"

    def __init__(
        self,
        regime_analyzer: VannaRegimeAnalyzer | None = None,
        pressure_analyzer: VannaPressureAnalyzer | None = None,
    ) -> None:
        self._regime = regime_analyzer or VannaRegimeAnalyzer()
        self._pressure = pressure_analyzer or VannaPressureAnalyzer()

    def analyze(
        self,
        dealer_positioning: DealerPositioningAnalysis | None = None,
        gamma_exposure: GammaExposureAnalysis | None = None,
        greeks: GreeksAnalysis | None = None,
        surface: SurfaceIntelligenceAnalysis | None = None,
        option_chain: OptionChainAnalysis | None = None,
        option_chain_snapshot: OptionChainSnapshot | None = None,
    ) -> VannaExposureAnalysis:
        """Execute vanna exposure analysis.

        Args:
            dealer_positioning: Dealer positioning analysis.
            gamma_exposure: Gamma exposure analysis.
            greeks: Combined Greeks intelligence.
            surface: Volatility surface intelligence.
            option_chain: Combined option-chain intelligence.
            option_chain_snapshot: Raw option-chain snapshot with
                per-strike vanna, gamma, and OI data.

        Returns:
            Combined VannaExposureAnalysis.
        """

        input_data = VannaExposureInput(
            dealer_positioning=dealer_positioning,
            gamma_exposure=gamma_exposure,
            greeks=greeks,
            surface=surface,
            option_chain=option_chain,
            option_chain_snapshot=option_chain_snapshot,
        )

        if all(
            v is None
            for v in (
                dealer_positioning,
                gamma_exposure,
                greeks,
                surface,
                option_chain,
                option_chain_snapshot,
            )
        ):
            return self._empty_analysis("No vanna exposure inputs provided.")

        regime = self._regime.analyze(input_data)
        pressure = self._pressure.analyze(input_data, regime)
        net_vanna = regime.net_vanna
        confidence = self._calculate_confidence(regime, pressure)

        analysis = VannaExposureAnalysis(
            net_vanna=net_vanna,
            regime=regime,
            pressure=pressure,
            confidence=confidence,
            warnings=self._combine_warnings(input_data),
            metadata=self._metadata(input_data),
        )

        evidence = self._to_evidence(analysis)
        explanation = self._explanation(analysis)

        object.__setattr__(analysis, "evidence", evidence)
        object.__setattr__(analysis, "explanation", explanation)

        return analysis

    # ------------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------------

    def _calculate_confidence(
        self,
        regime: VannaRegime,
        pressure: VannaPressure,
    ) -> float:
        confidences: list[float] = []
        weights: list[float] = []

        if regime.confidence > 0:
            confidences.append(regime.confidence)
            weights.append(0.5)

        if pressure.confidence > 0:
            confidences.append(pressure.confidence)
            weights.append(0.5)

        if not confidences:
            return 0.0

        total = sum(c * w for c, w in zip(confidences, weights))
        total_w = sum(weights)
        return total / total_w if total_w > 0 else 0.0

    # ------------------------------------------------------------------
    # Warnings
    # ------------------------------------------------------------------

    def _combine_warnings(self, input_data: VannaExposureInput) -> tuple[str, ...]:
        combined: list[str] = []
        seen: set[str] = set()

        if input_data.option_chain_snapshot is None:
            msg = "Option chain snapshot not available."
            if msg not in seen:
                combined.append(msg)
                seen.add(msg)

        if input_data.gamma_exposure is None:
            msg = "Gamma exposure analysis not available."
            if msg not in seen:
                combined.append(msg)
                seen.add(msg)

        if input_data.dealer_positioning is None:
            msg = "Dealer positioning analysis not available."
            if msg not in seen:
                combined.append(msg)
                seen.add(msg)

        return tuple(combined)

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def _metadata(self, input_data: VannaExposureInput) -> dict[str, Any]:
        return {
            "analyzer": self.name,
            "gamma_exposure_available": input_data.gamma_exposure is not None,
            "dealer_positioning_available": input_data.dealer_positioning is not None,
            "greeks_available": input_data.greeks is not None,
            "surface_available": input_data.surface is not None,
            "snapshot_available": input_data.option_chain_snapshot is not None,
        }

    # ------------------------------------------------------------------
    # Evidence generation
    # ------------------------------------------------------------------

    def _evidence_signal(self, regime_type: VannaRegimeType) -> EvidenceSignal:
        mapping = {
            VannaRegimeType.POSITIVE: EvidenceSignal.BULLISH,
            VannaRegimeType.NEGATIVE: EvidenceSignal.BEARISH,
            VannaRegimeType.BALANCED: EvidenceSignal.NEUTRAL,
        }
        return mapping.get(regime_type, EvidenceSignal.UNKNOWN)

    def _evidence_score(self, analysis: VannaExposureAnalysis) -> float:
        base = NEUTRAL_SCORE

        if analysis.regime.regime_type is VannaRegimeType.POSITIVE:
            base = POSITIVE_VANNA_SCORE
        elif analysis.regime.regime_type is VannaRegimeType.NEGATIVE:
            base = NEGATIVE_VANNA_SCORE

        adj = 0.0
        if analysis.pressure.pressure_level in (
            VannaPressureLevel.HIGH,
            VannaPressureLevel.EXTREME,
        ):
            adj += 5.0

        return max(0.0, min(100.0, base + adj))

    def _evidence_reasons(self, analysis: VannaExposureAnalysis) -> tuple[str, ...]:
        reasons: list[str] = []

        reasons.append(f"Vanna regime is {analysis.regime.regime_type.value}.")
        if analysis.net_vanna is not None:
            reasons.append(f"Net vanna exposure is {analysis.net_vanna:.4f}.")
        reasons.append(f"Vanna pressure is {analysis.pressure.pressure_level.value}.")
        reasons.append(
            f"IV sensitivity: {analysis.pressure.iv_sensitivity:.2f}, "
            f"price sensitivity: {analysis.pressure.price_sensitivity:.2f}."
        )

        return tuple(reasons)

    def _to_evidence(self, analysis: VannaExposureAnalysis) -> Evidence:
        signal = self._evidence_signal(analysis.regime.regime_type)
        score = self._evidence_score(analysis)
        confidence = analysis.confidence

        return Evidence(
            source="Vanna Exposure",
            category=EvidenceCategory.OPTION_CHAIN,
            signal=signal,
            score=Score(score),
            confidence=Confidence(confidence),
            weight=1.0,
            reasons=self._evidence_reasons(analysis),
            warnings=analysis.warnings,
            metadata={
                "analyzer": self.name,
                "vanna_regime": analysis.regime.regime_type.value,
                "net_vanna": analysis.net_vanna,
                "pressure_level": analysis.pressure.pressure_level.value,
                "iv_sensitivity": analysis.pressure.iv_sensitivity,
                "price_sensitivity": analysis.pressure.price_sensitivity,
            },
        )

    # ------------------------------------------------------------------
    # Explanation generation
    # ------------------------------------------------------------------

    def _explanation(self, analysis: VannaExposureAnalysis) -> VannaExplanation:
        return VannaExplanation(
            overall_vanna=self._overall_section(analysis),
            dealer_sensitivity=self._sensitivity_section(analysis),
            iv_impact=self._iv_impact_section(analysis),
            price_impact=self._price_impact_section(analysis),
            institutional_interpretation=self._institutional_section(analysis),
            risk_assessment=self._risk_section(analysis),
        )

    def _overall_section(self, analysis: VannaExposureAnalysis) -> str:
        parts: list[str] = ["Overall Vanna Exposure:"]

        regime = analysis.regime.regime_type

        if regime is VannaRegimeType.POSITIVE:
            parts.append(
                "Net vanna is positive. Dealers are positioned such that "
                "rising implied volatility increases their net delta, "
                "requiring additional short hedging. This creates "
                "volatility-driven selling pressure."
            )
        elif regime is VannaRegimeType.NEGATIVE:
            parts.append(
                "Net vanna is negative. Dealers are positioned such that "
                "rising implied volatility decreases their net delta, "
                "requiring additional long hedging. This creates "
                "volatility-driven buying pressure."
            )
        elif regime is VannaRegimeType.BALANCED:
            parts.append(
                "Net vanna is balanced. Dealer delta is relatively "
                "insensitive to changes in implied volatility."
            )
        else:
            parts.append("Vanna regime cannot be determined from available data.")

        if analysis.net_vanna is not None:
            parts.append(f"Net vanna exposure: {analysis.net_vanna:.4f}.")

        return " ".join(parts)

    def _sensitivity_section(self, analysis: VannaExposureAnalysis) -> str:
        parts: list[str] = ["Dealer Sensitivity:"]

        pressure = analysis.pressure

        if pressure.iv_sensitivity >= CONFIDENCE_HIGH:
            parts.append(
                "Dealers have high sensitivity to IV changes. "
                "Movements in implied volatility are expected to "
                "generate significant dealer hedging flow."
            )
        elif pressure.iv_sensitivity >= CONFIDENCE_MODERATE:
            parts.append("Dealers have moderate sensitivity to IV changes.")
        elif pressure.iv_sensitivity >= CONFIDENCE_LOW:
            parts.append("Dealers have low sensitivity to IV changes.")
        else:
            parts.append("Dealer sensitivity to IV changes cannot be assessed.")

        if pressure.price_sensitivity >= CONFIDENCE_HIGH:
            parts.append(
                "Dealers have high sensitivity to price changes, "
                "indicating short gamma conditions amplify the "
                "vanna effect."
            )
        elif pressure.price_sensitivity >= CONFIDENCE_MODERATE:
            parts.append("Dealers have moderate sensitivity to price changes.")
        elif pressure.price_sensitivity >= CONFIDENCE_LOW:
            parts.append("Dealers have low sensitivity to price changes.")
        else:
            parts.append("Dealer sensitivity to price changes cannot be assessed.")

        return " ".join(parts)

    def _iv_impact_section(self, analysis: VannaExposureAnalysis) -> str:
        parts: list[str] = ["IV Impact on Dealer Hedging:"]

        iv_sens = analysis.pressure.iv_sensitivity
        regime = analysis.regime.regime_type

        if iv_sens < CONFIDENCE_LOW:
            parts.append(
                "Implied volatility changes are unlikely to "
                "materially affect dealer hedging pressure."
            )
        elif regime is VannaRegimeType.POSITIVE:
            parts.append(
                "Rising IV increases dealer net delta, creating "
                "sell pressure. Falling IV decreases dealer net "
                "delta, creating buy pressure. This suggests IV "
                "peaks may coincide with selling into strength."
            )
        elif regime is VannaRegimeType.NEGATIVE:
            parts.append(
                "Rising IV decreases dealer net delta, creating "
                "buy pressure. Falling IV increases dealer net "
                "delta, creating sell pressure. This suggests IV "
                "peaks may coincide with buying the dip."
            )
        else:
            parts.append(
                "The relationship between IV changes and dealer "
                "hedging flow cannot be determined."
            )

        return " ".join(parts)

    def _price_impact_section(self, analysis: VannaExposureAnalysis) -> str:
        parts: list[str] = ["Price Impact on Dealer Hedging:"]

        price_sens = analysis.pressure.price_sensitivity
        regime = analysis.regime.regime_type

        if price_sens < CONFIDENCE_LOW:
            parts.append(
                "Price changes are unlikely to materially affect "
                "dealer vanna exposure."
            )
        elif regime is VannaRegimeType.POSITIVE:
            parts.append(
                "Falling prices reduce IV (typically), which "
                "decreases dealer net delta and may trigger buy "
                "pressure. Rising prices increase IV (typically), "
                "which may trigger sell pressure."
            )
        elif regime is VannaRegimeType.NEGATIVE:
            parts.append(
                "Falling prices reduce IV (typically), which "
                "increases dealer net delta and may trigger sell "
                "pressure. Rising prices increase IV (typically), "
                "which may trigger buy pressure."
            )
        else:
            parts.append(
                "The relationship between price changes and dealer "
                "hedging flow cannot be determined."
            )

        return " ".join(parts)

    def _institutional_section(self, analysis: VannaExposureAnalysis) -> str:
        parts: list[str] = ["Institutional Interpretation:"]

        regime = analysis.regime.regime_type
        pressure = analysis.pressure
        iv_sens = pressure.iv_sensitivity
        price_sens = pressure.price_sensitivity

        if regime is VannaRegimeType.POSITIVE and iv_sens >= CONFIDENCE_MODERATE:
            parts.append(
                "Positive vanna with elevated IV sensitivity "
                "suggests that IV spikes create selling pressure. "
                "This is a contrarian signal when IV is already "
                "elevated — dealer hedging may accelerate mean "
                "reversion in IV."
            )
        elif regime is VannaRegimeType.NEGATIVE and iv_sens >= CONFIDENCE_MODERATE:
            parts.append(
                "Negative vanna with elevated IV sensitivity "
                "suggests that IV spikes create buying pressure. "
                "This can support prices during vol shocks and "
                "may indicate put protection is being bought "
                "by dealers."
            )
        elif regime is VannaRegimeType.POSITIVE:
            parts.append(
                "Positive vanna provides a structural dampening "
                "effect on IV spikes through dealer hedging flows."
            )
        elif regime is VannaRegimeType.NEGATIVE:
            parts.append(
                "Negative vanna indicates dealers are positioned "
                "to amplify IV moves through their hedging flows."
            )
        else:
            parts.append(
                "Vanna exposure is insufficiently characterised "
                "to draw institutional conclusions."
            )

        if price_sens >= CONFIDENCE_HIGH and analysis.confidence >= CONFIDENCE_MODERATE:
            parts.append(
                "Combined vanna-gamma amplification risk is "
                "elevated. Monitor closely for acceleration "
                "through key levels."
            )

        if analysis.confidence < CONFIDENCE_LOW:
            parts.append(
                "Low confidence suggests limited data availability. "
                "Interpret with caution."
            )

        return " ".join(parts)

    def _risk_section(self, analysis: VannaExposureAnalysis) -> str:
        parts: list[str] = ["Risk Assessment:"]

        pressure = analysis.pressure

        if pressure.pressure_level in (
            VannaPressureLevel.HIGH,
            VannaPressureLevel.EXTREME,
        ):
            parts.append(
                "Elevated vanna pressure increases the risk of "
                "volatility-driven hedging cascades. Consider "
                "position sizing that accounts for potential IV "
                "spikes triggering dealer hedging flows."
            )

        if (
            analysis.regime.regime_type is VannaRegimeType.NEGATIVE
            and pressure.price_sensitivity >= CONFIDENCE_MODERATE
        ):
            parts.append(
                "Negative vanna combined with price sensitivity "
                "suggests that a vol spike during a sell-off could "
                "generate additional buying pressure, creating a "
                "potential V-shaped recovery pattern."
            )

        if pressure.iv_sensitivity >= CONFIDENCE_HIGH:
            parts.append(
                "High IV sensitivity means dealer hedging flows "
                "are likely to amplify IV moves. Monitor IV "
                "term structure for signs of stress."
            )

        if not parts:
            parts.append("No material vanna-driven risk factors identified.")

        return " ".join(parts)

    # ------------------------------------------------------------------
    # Empty / fallback analysis
    # ------------------------------------------------------------------

    def _empty_analysis(self, reason: str) -> VannaExposureAnalysis:
        analysis = VannaExposureAnalysis.neutral_placeholder()
        object.__setattr__(analysis, "warnings", (reason,))
        explanation = VannaExplanation(
            overall_vanna="Vanna exposure assessment unavailable: no inputs provided.",
            dealer_sensitivity="Dealer sensitivity assessment unavailable: no inputs provided.",
            iv_impact="IV impact assessment unavailable: no inputs provided.",
            price_impact="Price impact assessment unavailable: no inputs provided.",
            institutional_interpretation="Institutional Interpretation: Vanna exposure data is unavailable.",
            risk_assessment="Risk Assessment: Vanna exposure data is unavailable.",
        )
        object.__setattr__(analysis, "explanation", explanation)
        return analysis
