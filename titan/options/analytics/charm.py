"""Charm Exposure (CHE) Intelligence Engine Orchestrator.

Provides institutional Charm intelligence using supplied option analytics.
Charm measures how option delta changes with the passage of time (dDelta/dt)
— a critical input for understanding dealer delta-decay hedging pressure.

Pure orchestrator — no broker imports, no API calls, no Black-Scholes.
Consumes supplied Charm, Greeks, and analysis objects only.

Integrates with:
  - Evidence Engine
  - Intelligence Fusion Engine
  - Dealer Positioning Intelligence
  - Gamma Exposure Intelligence
  - Vanna Exposure Intelligence
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
    CharmExposureAnalysis,
    CharmExposureInput,
    CharmExplanation,
    CharmPressure,
    CharmPressureLevel,
    CharmRegime,
    CharmRegimeType,
    DealerPositioningAnalysis,
    GammaExposureAnalysis,
    GreeksAnalysis,
    OptionChainAnalysis,
    OptionChainSnapshot,
    SurfaceIntelligenceAnalysis,
    VannaExposureAnalysis,
)
from titan.options.analytics.charm_pressure import CharmPressureAnalyzer
from titan.options.analytics.charm_regime import CharmRegimeAnalyzer

POSITIVE_CHARM_SCORE = 60.0
NEGATIVE_CHARM_SCORE = 40.0
NEUTRAL_SCORE = 50.0

CONFIDENCE_LOW = 0.3
CONFIDENCE_MODERATE = 0.5
CONFIDENCE_HIGH = 0.7

DECAY_LOW_THRESHOLD = 0.3
DECAY_MODERATE_THRESHOLD = 0.5
DECAY_HIGH_THRESHOLD = 0.7


class CharmExposureAnalyzer:
    """Orchestrate charm exposure intelligence.

    Consumes DealerPositioningAnalysis, GammaExposureAnalysis,
    VannaExposureAnalysis, GreeksAnalysis, SurfaceIntelligenceAnalysis,
    OptionChainAnalysis, and OptionChainSnapshot to produce a unified
    institutional assessment of charm exposure.  Pure orchestrator —
    does not recalculate any option metric or greek.
    """

    name = "CharmExposureAnalyzer"

    def __init__(
        self,
        regime_analyzer: CharmRegimeAnalyzer | None = None,
        pressure_analyzer: CharmPressureAnalyzer | None = None,
    ) -> None:
        self._regime = regime_analyzer or CharmRegimeAnalyzer()
        self._pressure = pressure_analyzer or CharmPressureAnalyzer()

    def analyze(
        self,
        dealer_positioning: DealerPositioningAnalysis | None = None,
        gamma_exposure: GammaExposureAnalysis | None = None,
        vanna_exposure: VannaExposureAnalysis | None = None,
        greeks: GreeksAnalysis | None = None,
        surface: SurfaceIntelligenceAnalysis | None = None,
        option_chain: OptionChainAnalysis | None = None,
        option_chain_snapshot: OptionChainSnapshot | None = None,
    ) -> CharmExposureAnalysis:
        """Execute charm exposure analysis.

        Args:
            dealer_positioning: Dealer positioning analysis.
            gamma_exposure: Gamma exposure analysis.
            vanna_exposure: Vanna exposure analysis.
            greeks: Combined Greeks intelligence.
            surface: Volatility surface intelligence.
            option_chain: Combined option-chain intelligence.
            option_chain_snapshot: Raw option-chain snapshot with
                per-strike charm, gamma, and OI data.

        Returns:
            Combined CharmExposureAnalysis.
        """

        input_data = CharmExposureInput(
            dealer_positioning=dealer_positioning,
            gamma_exposure=gamma_exposure,
            vanna_exposure=vanna_exposure,
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
                vanna_exposure,
                greeks,
                surface,
                option_chain,
                option_chain_snapshot,
            )
        ):
            return self._empty_analysis("No charm exposure inputs provided.")

        regime = self._regime.analyze(input_data)
        pressure = self._pressure.analyze(input_data, regime)
        net_charm = regime.net_charm
        dealer_delta_decay = self._dealer_delta_decay(regime, pressure)
        near_expiry_risk = pressure.near_expiry_risk
        confidence = self._calculate_confidence(regime, pressure)

        analysis = CharmExposureAnalysis(
            net_charm=net_charm,
            regime=regime,
            pressure=pressure,
            dealer_delta_decay=dealer_delta_decay,
            near_expiry_risk=near_expiry_risk,
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
    # Dealer delta decay
    # ------------------------------------------------------------------

    def _dealer_delta_decay(
        self,
        regime: CharmRegime,
        pressure: CharmPressure,
    ) -> float:
        """Compute dealer delta decay magnitude (0-1)."""
        score = pressure.time_sensitivity

        if pressure.near_expiry_risk:
            score = min(1.0, score + 0.15)

        if regime.net_charm is not None and regime.confidence > 0.5:
            if abs(regime.net_charm) > 1e-8:
                score = min(1.0, score + 0.1)

        return score

    # ------------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------------

    def _calculate_confidence(
        self,
        regime: CharmRegime,
        pressure: CharmPressure,
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

    def _combine_warnings(self, input_data: CharmExposureInput) -> tuple[str, ...]:
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

        if input_data.vanna_exposure is None:
            msg = "Vanna exposure analysis not available."
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

    def _metadata(self, input_data: CharmExposureInput) -> dict[str, Any]:
        return {
            "analyzer": self.name,
            "gamma_exposure_available": input_data.gamma_exposure is not None,
            "vanna_exposure_available": input_data.vanna_exposure is not None,
            "dealer_positioning_available": input_data.dealer_positioning is not None,
            "greeks_available": input_data.greeks is not None,
            "surface_available": input_data.surface is not None,
            "snapshot_available": input_data.option_chain_snapshot is not None,
        }

    # ------------------------------------------------------------------
    # Evidence generation
    # ------------------------------------------------------------------

    def _evidence_signal(self, regime_type: CharmRegimeType) -> EvidenceSignal:
        mapping = {
            CharmRegimeType.POSITIVE: EvidenceSignal.BULLISH,
            CharmRegimeType.NEGATIVE: EvidenceSignal.BEARISH,
            CharmRegimeType.BALANCED: EvidenceSignal.NEUTRAL,
        }
        return mapping.get(regime_type, EvidenceSignal.UNKNOWN)

    def _evidence_score(self, analysis: CharmExposureAnalysis) -> float:
        base = NEUTRAL_SCORE

        if analysis.regime.regime_type is CharmRegimeType.POSITIVE:
            base = POSITIVE_CHARM_SCORE
        elif analysis.regime.regime_type is CharmRegimeType.NEGATIVE:
            base = NEGATIVE_CHARM_SCORE

        adj = 0.0
        if analysis.pressure.pressure_level in (
            CharmPressureLevel.HIGH,
            CharmPressureLevel.EXTREME,
        ):
            adj += 5.0

        return max(0.0, min(100.0, base + adj))

    def _evidence_reasons(
        self,
        analysis: CharmExposureAnalysis,
    ) -> tuple[str, ...]:
        reasons: list[str] = []

        reasons.append(f"Charm regime is {analysis.regime.regime_type.value}.")
        if analysis.net_charm is not None:
            reasons.append(f"Net charm exposure is {analysis.net_charm:.4f}.")
        reasons.append(f"Charm pressure is {analysis.pressure.pressure_level.value}.")
        reasons.append(f"Dealer delta decay: {analysis.dealer_delta_decay:.2f}.")
        if analysis.near_expiry_risk:
            reasons.append("Near-expiry charm risk is elevated.")

        return tuple(reasons)

    def _to_evidence(self, analysis: CharmExposureAnalysis) -> Evidence:
        signal = self._evidence_signal(analysis.regime.regime_type)
        score = self._evidence_score(analysis)
        confidence = analysis.confidence

        return Evidence(
            source="Charm Exposure",
            category=EvidenceCategory.OPTION_CHAIN,
            signal=signal,
            score=Score(score),
            confidence=Confidence(confidence),
            weight=1.0,
            reasons=self._evidence_reasons(analysis),
            warnings=analysis.warnings,
            metadata={
                "analyzer": self.name,
                "charm_regime": analysis.regime.regime_type.value,
                "net_charm": analysis.net_charm,
                "pressure_level": analysis.pressure.pressure_level.value,
                "dealer_delta_decay": analysis.dealer_delta_decay,
                "near_expiry_risk": analysis.near_expiry_risk,
            },
        )

    # ------------------------------------------------------------------
    # Explanation generation
    # ------------------------------------------------------------------

    def _explanation(
        self,
        analysis: CharmExposureAnalysis,
    ) -> CharmExplanation:
        return CharmExplanation(
            overall_charm=self._overall_section(analysis),
            dealer_delta_decay=self._decay_section(analysis),
            time_decay_impact=self._time_decay_section(analysis),
            near_expiry_risk=self._expiry_section(analysis),
            institutional_interpretation=self._institutional_section(analysis),
            risk_assessment=self._risk_section(analysis),
        )

    def _overall_section(self, analysis: CharmExposureAnalysis) -> str:
        parts: list[str] = ["Overall Charm Exposure:"]

        regime = analysis.regime.regime_type

        if regime is CharmRegimeType.POSITIVE:
            parts.append(
                "Net charm is positive. Dealer delta increases with "
                "the passage of time, requiring dealers to buy delta "
                "to maintain hedges."
            )
        elif regime is CharmRegimeType.NEGATIVE:
            parts.append(
                "Net charm is negative. Dealer delta decays with "
                "the passage of time, requiring dealers to sell "
                "delta to maintain hedges."
            )
        elif regime is CharmRegimeType.BALANCED:
            parts.append(
                "Net charm is balanced. Dealer delta is relatively "
                "stable with respect to time decay."
            )
        else:
            parts.append("Charm regime cannot be determined from available data.")

        if analysis.net_charm is not None:
            parts.append(f"Net charm exposure: {analysis.net_charm:.4f}.")

        return " ".join(parts)

    def _decay_section(self, analysis: CharmExposureAnalysis) -> str:
        parts: list[str] = ["Dealer Delta Decay:"]

        decay = analysis.dealer_delta_decay

        if decay >= DECAY_HIGH_THRESHOLD:
            parts.append(
                "Dealer delta is decaying rapidly with time. "
                "Frequent delta rebalancing is expected as "
                "options approach expiry."
            )
        elif decay >= DECAY_MODERATE_THRESHOLD:
            parts.append(
                "Dealer delta shows moderate time decay. "
                "Some delta rebalancing is expected."
            )
        elif decay >= DECAY_LOW_THRESHOLD:
            parts.append(
                "Dealer delta shows low time decay. "
                "Minimal delta rebalancing is expected from "
                "time decay alone."
            )
        else:
            parts.append(
                "Dealer delta decay cannot be assessed from " "available data."
            )

        return " ".join(parts)

    def _time_decay_section(self, analysis: CharmExposureAnalysis) -> str:
        parts: list[str] = ["Time Decay Impact on Dealer Hedging:"]

        time_sens = analysis.pressure.time_sensitivity
        regime = analysis.regime.regime_type

        if time_sens < CONFIDENCE_LOW:
            parts.append(
                "Time decay is unlikely to materially affect "
                "dealer hedging pressure."
            )
        elif regime is CharmRegimeType.POSITIVE:
            parts.append(
                "As time passes, dealer delta increases, "
                "creating systematic buy pressure. This effect "
                "is most pronounced for ITM options with "
                "high open interest."
            )
        elif regime is CharmRegimeType.NEGATIVE:
            parts.append(
                "As time passes, dealer delta decreases, "
                "creating systematic sell pressure. This effect "
                "is most pronounced for OTM options with "
                "high open interest."
            )
        else:
            parts.append(
                "The relationship between time decay and dealer "
                "hedging flow cannot be determined."
            )

        if analysis.near_expiry_risk:
            parts.append(
                "With expiry approaching, charm-driven hedging "
                "accelerates. Delta decay per unit time increases "
                "as time-to-expiry approaches zero."
            )

        return " ".join(parts)

    def _expiry_section(self, analysis: CharmExposureAnalysis) -> str:
        parts: list[str] = ["Near-Expiry Risk:"]

        if analysis.near_expiry_risk:
            parts.append(
                "Near-expiry charm risk is elevated. Options "
                "approaching expiry experience accelerated delta "
                "decay, which can trigger rapid dealer hedging "
                "flows."
            )
            if analysis.regime.regime_type is CharmRegimeType.POSITIVE:
                parts.append(
                    "Positive charm near expiry means dealer "
                    "delta increases sharply, requiring aggressive "
                    "delta buying as expiry approaches."
                )
            elif analysis.regime.regime_type is CharmRegimeType.NEGATIVE:
                parts.append(
                    "Negative charm near expiry means dealer "
                    "delta decreases sharply, requiring aggressive "
                    "delta selling as expiry approaches."
                )
        else:
            parts.append(
                "Near-expiry charm risk is not elevated. "
                "Sufficient time remains before expiry for "
                "orderly delta decay."
            )

        return " ".join(parts)

    def _institutional_section(self, analysis: CharmExposureAnalysis) -> str:
        parts: list[str] = ["Institutional Interpretation:"]

        regime = analysis.regime.regime_type
        pressure = analysis.pressure
        time_sens = pressure.time_sensitivity

        if regime is CharmRegimeType.POSITIVE and time_sens >= CONFIDENCE_MODERATE:
            parts.append(
                "Positive charm with elevated time sensitivity "
                "suggests systematic dealer delta buying over "
                "time. This creates a structural bid that "
                "intensifies near expiry."
            )
        elif regime is CharmRegimeType.NEGATIVE and time_sens >= CONFIDENCE_MODERATE:
            parts.append(
                "Negative charm with elevated time sensitivity "
                "suggests systematic dealer delta selling over "
                "time. This creates structural supply that "
                "intensifies near expiry."
            )
        elif regime is CharmRegimeType.POSITIVE:
            parts.append(
                "Positive charm provides a gradual structural "
                "bid through dealer delta rebalancing."
            )
        elif regime is CharmRegimeType.NEGATIVE:
            parts.append(
                "Negative charm provides gradual structural "
                "supply through dealer delta rebalancing."
            )
        else:
            parts.append(
                "Charm exposure is insufficiently characterised "
                "to draw institutional conclusions."
            )

        if analysis.near_expiry_risk and analysis.confidence >= CONFIDENCE_MODERATE:
            parts.append(
                "Near-expiry charm risk amplifies these effects. "
                "Monitor dealer hedging activity closely in the "
                "final days before expiry."
            )

        if analysis.confidence < CONFIDENCE_LOW:
            parts.append(
                "Low confidence suggests limited data availability. "
                "Interpret with caution."
            )

        return " ".join(parts)

    def _risk_section(self, analysis: CharmExposureAnalysis) -> str:
        parts: list[str] = ["Risk Assessment:"]

        pressure = analysis.pressure

        if pressure.pressure_level in (
            CharmPressureLevel.HIGH,
            CharmPressureLevel.EXTREME,
        ):
            parts.append(
                "Elevated charm pressure increases the risk of "
                "time-driven hedging cascades. Consider position "
                "sizing that accounts for accelerated delta decay "
                "near expiry."
            )

        if analysis.near_expiry_risk:
            parts.append(
                "Near-expiry conditions amplify charm-driven "
                "hedging. Delta decay accelerates, potentially "
                "causing larger-than-expected dealer flows."
            )

        if pressure.time_sensitivity >= CONFIDENCE_HIGH:
            parts.append(
                "High time sensitivity means dealer delta "
                "changes significantly with each passing day. "
                "Monitor open interest shifts near key strikes."
            )

        if not parts:
            parts.append("No material charm-driven risk factors identified.")

        return " ".join(parts)

    # ------------------------------------------------------------------
    # Empty / fallback analysis
    # ------------------------------------------------------------------

    def _empty_analysis(self, reason: str) -> CharmExposureAnalysis:
        analysis = CharmExposureAnalysis.neutral_placeholder()
        object.__setattr__(analysis, "warnings", (reason,))
        explanation = CharmExplanation(
            overall_charm="Charm exposure assessment unavailable: no inputs provided.",
            dealer_delta_decay="Dealer delta decay assessment unavailable: no inputs provided.",
            time_decay_impact="Time decay impact assessment unavailable: no inputs provided.",
            near_expiry_risk="Near-expiry risk assessment unavailable: no inputs provided.",
            institutional_interpretation="Institutional Interpretation: Charm exposure data is unavailable.",
            risk_assessment="Risk Assessment: Charm exposure data is unavailable.",
        )
        object.__setattr__(analysis, "explanation", explanation)
        return analysis
