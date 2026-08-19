"""Gamma Exposure (GEX) Intelligence Engine Orchestrator.

Estimates institutional dealer gamma exposure using supplied analytics
and produces institutional-grade Gamma Exposure intelligence.

Pure orchestrator — no broker imports, no API calls, no Black-Scholes.
Consumes supplied Greeks and Open Interest only.

Integrates with:
  - Evidence Engine
  - Intelligence Fusion Engine
  - Dealer Positioning Intelligence
"""

from typing import Any

from titan.core.evidence import (
    Confidence,
    Evidence,
    EvidenceCategory,
    EvidenceSignal,
    Score,
)
from titan.options.analytics.gamma_walls import GammaWallsAnalyzer
from titan.options.analytics.models import (
    DealerPositioningAnalysis,
    GammaExposureAnalysis,
    GammaExposureExplanation,
    GammaExposureInput,
    GammaRegime,
    GammaWall,
    GreeksAnalysis,
    OptionChainAnalysis,
    OptionChainSnapshot,
    PinningProbability,
    SurfaceIntelligenceAnalysis,
    ZeroGammaLevel,
)
from titan.options.analytics.zero_gamma import ZeroGammaAnalyzer

POSITIVE_GAMMA_SCORE = 70.0
NEGATIVE_GAMMA_SCORE = 30.0
NEUTRAL_SCORE = 50.0

PINNING_LOW_THRESHOLD = 0.3
PINNING_MEDIUM_THRESHOLD = 0.5
PINNING_HIGH_THRESHOLD = 0.7

CONFIDENCE_LOW = 0.3
CONFIDENCE_MODERATE = 0.5
CONFIDENCE_HIGH = 0.7


class GammaExposureAnalyzer:
    """Orchestrate gamma exposure intelligence.

    Consumes DealerPositioningAnalysis, GreeksAnalysis,
    SurfaceIntelligenceAnalysis, OptionChainAnalysis, and
    OptionChainSnapshot to produce a unified institutional
    assessment of gamma exposure.  Pure orchestrator — does not
    recalculate any option metric or greek.
    """

    name = "GammaExposureAnalyzer"

    def __init__(
        self,
        zero_gamma_analyzer: ZeroGammaAnalyzer | None = None,
        gamma_walls_analyzer: GammaWallsAnalyzer | None = None,
    ) -> None:
        self._zero_gamma = zero_gamma_analyzer or ZeroGammaAnalyzer()
        self._walls = gamma_walls_analyzer or GammaWallsAnalyzer()

    def analyze(
        self,
        dealer_positioning: DealerPositioningAnalysis | None = None,
        greeks: GreeksAnalysis | None = None,
        option_chain: OptionChainAnalysis | None = None,
        surface: SurfaceIntelligenceAnalysis | None = None,
        option_chain_snapshot: OptionChainSnapshot | None = None,
    ) -> GammaExposureAnalysis:
        """Execute gamma exposure analysis.

        Args:
            dealer_positioning: Dealer positioning analysis.
            greeks: Combined Greeks intelligence.
            option_chain: Combined option-chain intelligence.
            surface: Volatility surface intelligence.
            option_chain_snapshot: Raw option-chain snapshot with
                per-strike gamma and OI data.

        Returns:
            Combined GammaExposureAnalysis.
        """

        input_data = GammaExposureInput(
            dealer_positioning=dealer_positioning,
            greeks=greeks,
            option_chain=option_chain,
            surface=surface,
            option_chain_snapshot=option_chain_snapshot,
        )

        if all(
            v is None
            for v in (
                dealer_positioning,
                greeks,
                option_chain,
                surface,
                option_chain_snapshot,
            )
        ):
            return self._empty_analysis("No gamma exposure inputs provided.")

        net_gamma_exposure = self._compute_net_gamma_exposure(
            greeks, option_chain_snapshot
        )
        gamma_regime = self._determine_gamma_regime(
            net_gamma_exposure, dealer_positioning
        )
        zero_gamma_level = self._zero_gamma.analyze(input_data)
        call_wall, put_wall = self._walls.analyze(input_data)
        pinning_probability = self._assess_pinning(
            zero_gamma_level, call_wall, put_wall, gamma_regime
        )
        volatility_expansion = self._assess_volatility_expansion(
            gamma_regime, call_wall, put_wall
        )
        confidence = self._calculate_confidence(
            greeks, dealer_positioning, zero_gamma_level, call_wall, put_wall
        )
        warnings = self._combine_warnings(input_data)

        analysis = GammaExposureAnalysis(
            net_gamma_exposure=net_gamma_exposure,
            gamma_regime=gamma_regime,
            zero_gamma_level=zero_gamma_level,
            call_wall=call_wall,
            put_wall=put_wall,
            pinning_probability=pinning_probability,
            volatility_expansion_probability=volatility_expansion,
            confidence=confidence,
            warnings=warnings,
            metadata=self._metadata(input_data),
        )

        evidence = self._to_evidence(analysis)
        explanation = self._explanation(analysis)

        object.__setattr__(analysis, "evidence", evidence)
        object.__setattr__(analysis, "explanation", explanation)

        return analysis

    # ------------------------------------------------------------------
    # Net Gamma Exposure estimation
    # ------------------------------------------------------------------

    def _compute_net_gamma_exposure(
        self,
        greeks: GreeksAnalysis | None,
        snapshot: OptionChainSnapshot | None,
    ) -> float | None:
        """Compute net gamma exposure from available sources.

        Prefers GreeksAnalysis.net_gamma when available, otherwise
        computes from per-strike data.
        """
        if greeks is not None and greeks.net_gamma is not None:
            return greeks.net_gamma

        if snapshot is not None and snapshot.underlying_price is not None:
            return self._compute_from_snapshot(snapshot)

        return None

    def _compute_from_snapshot(self, snapshot: OptionChainSnapshot) -> float | None:
        """Compute net gamma exposure from per-strike gamma and OI."""
        total_call_gex = 0.0
        total_put_gex = 0.0
        has_gamma = False

        for strike in snapshot.strikes:
            if strike.call_gamma is not None:
                total_call_gex += abs(strike.call_gamma) * strike.call_open_interest
                has_gamma = True
            if strike.put_gamma is not None:
                total_put_gex += abs(strike.put_gamma) * strike.put_open_interest
                has_gamma = True

        if not has_gamma:
            return None

        return total_call_gex - total_put_gex

    # ------------------------------------------------------------------
    # Gamma Regime determination
    # ------------------------------------------------------------------

    def _determine_gamma_regime(
        self,
        net_gamma: float | None,
        dealer_positioning: DealerPositioningAnalysis | None,
    ) -> GammaRegime:
        """Determine gamma regime from net gamma and dealer positioning."""
        if net_gamma is not None:
            if abs(net_gamma) < 1e-10:
                return GammaRegime.NEUTRAL
            return GammaRegime.POSITIVE if net_gamma > 0 else GammaRegime.NEGATIVE

        if dealer_positioning is not None:
            from titan.options.analytics.models import DealerSide

            mapping = {
                DealerSide.LONG_GAMMA: GammaRegime.POSITIVE,
                DealerSide.SHORT_GAMMA: GammaRegime.NEGATIVE,
                DealerSide.NEUTRAL: GammaRegime.NEUTRAL,
            }
            return mapping.get(dealer_positioning.dealer_side, GammaRegime.UNKNOWN)

        return GammaRegime.UNKNOWN

    # ------------------------------------------------------------------
    # Pinning probability
    # ------------------------------------------------------------------

    def _assess_pinning(
        self,
        zero_gamma: ZeroGammaLevel | None,
        call_wall: GammaWall | None,
        put_wall: GammaWall | None,
        regime: GammaRegime,
    ) -> PinningProbability:
        """Assess probability of price pinning near gamma levels.

        Pinning is more likely when:
        - Dealers are long gamma (positive regime)
        - Price is near zero-gamma level
        - Strong walls exist close to current price
        """
        factors: list[float] = []

        if regime is GammaRegime.POSITIVE:
            factors.append(0.4)
        elif regime is GammaRegime.NEUTRAL:
            factors.append(0.3)
        elif regime is GammaRegime.NEGATIVE:
            factors.append(0.1)

        if zero_gamma is not None and zero_gamma.distance_percent is not None:
            dist = abs(zero_gamma.distance_percent)
            if dist < 0.01:
                factors.append(0.9)
            elif dist < 0.02:
                factors.append(0.6)
            elif dist < 0.05:
                factors.append(0.3)

        wall_proximity = self._wall_proximity_factor(call_wall, put_wall)
        if wall_proximity is not None:
            factors.append(wall_proximity)

        if not factors:
            return PinningProbability.UNKNOWN

        avg = sum(factors) / len(factors)

        if avg >= PINNING_HIGH_THRESHOLD:
            return PinningProbability.EXTREME
        if avg >= PINNING_MEDIUM_THRESHOLD:
            return PinningProbability.HIGH
        if avg >= PINNING_LOW_THRESHOLD:
            return PinningProbability.MEDIUM
        return PinningProbability.LOW

    def _wall_proximity_factor(
        self,
        call_wall: GammaWall | None,
        put_wall: GammaWall | None,
    ) -> float | None:
        """Estimate pinning contribution from wall proximity.

        When both call and put walls exist and are close to the
        underlying, pinning becomes more probable.
        """
        return (
            0.3
            if (
                call_wall is not None
                and put_wall is not None
                and call_wall.confidence > 0.3
                and put_wall.confidence > 0.3
            )
            else None
        )

    # ------------------------------------------------------------------
    # Volatility expansion probability
    # ------------------------------------------------------------------

    def _assess_volatility_expansion(
        self,
        regime: GammaRegime,
        call_wall: GammaWall | None,
        put_wall: GammaWall | None,
    ) -> float:
        """Assess likelihood of volatility expansion.

        Expansion is more likely when:
        - Dealers are short gamma (negative regime)
        - Walls are weak or far away
        - No zero-gamma pinning level nearby
        """
        score = 0.0
        factors = 0

        if regime is GammaRegime.NEGATIVE:
            score += 0.7
            factors += 1
        elif regime is GammaRegime.NEUTRAL:
            score += 0.3
            factors += 1
        elif regime is GammaRegime.POSITIVE:
            score += 0.1
            factors += 1

        walls_weak = (
            call_wall is None
            or put_wall is None
            or call_wall.confidence < 0.3
            or put_wall.confidence < 0.3
        )
        if walls_weak:
            score += 0.2
            factors += 1

        if factors == 0:
            return 0.0

        return min(1.0, score / factors)

    # ------------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------------

    def _calculate_confidence(
        self,
        greeks: GreeksAnalysis | None,
        dealer_positioning: DealerPositioningAnalysis | None,
        zero_gamma: ZeroGammaLevel | None,
        call_wall: GammaWall | None,
        put_wall: GammaWall | None,
    ) -> float:
        confidences: list[float] = []
        weights: list[float] = []

        if greeks is not None and greeks.net_gamma is not None:
            confidences.append(greeks.confidence)
            weights.append(0.35)

        if dealer_positioning is not None:
            confidences.append(dealer_positioning.confidence)
            weights.append(0.25)

        if zero_gamma is not None and zero_gamma.confidence > 0:
            confidences.append(zero_gamma.confidence)
            weights.append(0.2)

        if call_wall is not None and call_wall.confidence > 0:
            confidences.append(call_wall.confidence)
            weights.append(0.1)

        if put_wall is not None and put_wall.confidence > 0:
            confidences.append(put_wall.confidence)
            weights.append(0.1)

        if not confidences:
            return 0.0

        total = sum(c * w for c, w in zip(confidences, weights))
        total_w = sum(weights)
        return total / total_w if total_w > 0 else 0.0

    # ------------------------------------------------------------------
    # Warnings
    # ------------------------------------------------------------------

    def _combine_warnings(self, input_data: GammaExposureInput) -> tuple[str, ...]:
        combined: list[str] = []
        seen: set[str] = set()

        if input_data.greeks is None:
            msg = "Greeks analysis not available."
            if msg not in seen:
                combined.append(msg)
                seen.add(msg)

        if input_data.dealer_positioning is None:
            msg = "Dealer positioning analysis not available."
            if msg not in seen:
                combined.append(msg)
                seen.add(msg)

        if input_data.option_chain_snapshot is None:
            msg = "Option chain snapshot not available."
            if msg not in seen:
                combined.append(msg)
                seen.add(msg)

        return tuple(combined)

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def _metadata(self, input_data: GammaExposureInput) -> dict[str, Any]:
        return {
            "analyzer": self.name,
            "greeks_available": input_data.greeks is not None,
            "dealer_positioning_available": input_data.dealer_positioning is not None,
            "option_chain_available": input_data.option_chain is not None,
            "surface_available": input_data.surface is not None,
            "snapshot_available": input_data.option_chain_snapshot is not None,
        }

    # ------------------------------------------------------------------
    # Evidence generation
    # ------------------------------------------------------------------

    def _evidence_signal(self, regime: GammaRegime) -> EvidenceSignal:
        mapping = {
            GammaRegime.POSITIVE: EvidenceSignal.BULLISH,
            GammaRegime.NEGATIVE: EvidenceSignal.BEARISH,
            GammaRegime.NEUTRAL: EvidenceSignal.NEUTRAL,
        }
        return mapping.get(regime, EvidenceSignal.UNKNOWN)

    def _evidence_score(self, analysis: GammaExposureAnalysis) -> float:
        base = NEUTRAL_SCORE

        if analysis.gamma_regime is GammaRegime.POSITIVE:
            base = POSITIVE_GAMMA_SCORE
        elif analysis.gamma_regime is GammaRegime.NEGATIVE:
            base = NEGATIVE_GAMMA_SCORE

        adj = 0.0
        if analysis.pinning_probability in (
            PinningProbability.HIGH,
            PinningProbability.EXTREME,
        ):
            adj += 5.0

        return max(0.0, min(100.0, base + adj))

    def _evidence_reasons(
        self,
        analysis: GammaExposureAnalysis,
    ) -> tuple[str, ...]:
        reasons: list[str] = []

        reasons.append(f"Gamma regime is {analysis.gamma_regime.value}.")
        if analysis.net_gamma_exposure is not None:
            reasons.append(f"Net gamma exposure is {analysis.net_gamma_exposure:.4f}.")
        if analysis.zero_gamma_level is not None:
            label = (
                f"at {analysis.zero_gamma_level.strike:.2f}"
                if analysis.zero_gamma_level.strike is not None
                else "undetermined"
            )
            reasons.append(f"Zero gamma level {label}.")
        if analysis.call_wall is not None and analysis.call_wall.strike is not None:
            reasons.append(f"Call wall at {analysis.call_wall.strike:.2f}.")
        if analysis.put_wall is not None and analysis.put_wall.strike is not None:
            reasons.append(f"Put wall at {analysis.put_wall.strike:.2f}.")
        reasons.append(f"Pinning probability is {analysis.pinning_probability.value}.")

        return tuple(reasons)

    def _to_evidence(self, analysis: GammaExposureAnalysis) -> Evidence:
        signal = self._evidence_signal(analysis.gamma_regime)
        score = self._evidence_score(analysis)
        confidence = analysis.confidence

        return Evidence(
            source="Gamma Exposure",
            category=EvidenceCategory.OPTION_CHAIN,
            signal=signal,
            score=Score(score),
            confidence=Confidence(confidence),
            weight=1.0,
            reasons=self._evidence_reasons(analysis),
            warnings=analysis.warnings,
            metadata={
                "analyzer": self.name,
                "gamma_regime": analysis.gamma_regime.value,
                "net_gamma_exposure": analysis.net_gamma_exposure,
                "pinning_probability": analysis.pinning_probability.value,
                "volatility_expansion_probability": analysis.volatility_expansion_probability,
                "has_zero_gamma": analysis.zero_gamma_level is not None,
                "has_call_wall": analysis.call_wall is not None,
                "has_put_wall": analysis.put_wall is not None,
            },
        )

    # ------------------------------------------------------------------
    # Explanation generation
    # ------------------------------------------------------------------

    def _explanation(
        self,
        analysis: GammaExposureAnalysis,
    ) -> GammaExposureExplanation:
        return GammaExposureExplanation(
            gamma_regime=self._regime_section(analysis),
            zero_gamma=self._zero_gamma_section(analysis),
            gamma_walls=self._walls_section(analysis),
            pinning_risk=self._pinning_section(analysis),
            volatility_implications=self._volatility_section(analysis),
            institutional_interpretation=self._institutional_section(analysis),
        )

    def _regime_section(self, analysis: GammaExposureAnalysis) -> str:
        parts: list[str] = ["Gamma Regime Assessment:"]

        if analysis.gamma_regime is GammaRegime.POSITIVE:
            parts.append(
                "Dealers are net long gamma. Their hedging activity "
                "dampens directional moves, creating a range-bound "
                "environment with mean-reversion tendencies."
            )
        elif analysis.gamma_regime is GammaRegime.NEGATIVE:
            parts.append(
                "Dealers are net short gamma. Their hedging activity "
                "amplifies directional moves, increasing the risk of "
                "momentum-driven price action."
            )
        elif analysis.gamma_regime is GammaRegime.NEUTRAL:
            parts.append(
                "Gamma exposure is balanced. No significant damping "
                "or amplification is expected from dealer hedging "
                "alone."
            )
        else:
            parts.append("Gamma regime cannot be determined from available data.")

        if analysis.net_gamma_exposure is not None:
            parts.append(f"Net gamma exposure: {analysis.net_gamma_exposure:.4f}.")

        return " ".join(parts)

    def _zero_gamma_section(self, analysis: GammaExposureAnalysis) -> str:
        parts: list[str] = ["Zero Gamma (Gamma Flip) Level:"]

        zgl = analysis.zero_gamma_level
        if zgl is not None and zgl.strike is not None:
            parts.append(
                f"Net gamma exposure crosses zero at approximately {zgl.strike:.2f}."
            )
            if zgl.distance_percent is not None:
                direction = "above" if zgl.distance_percent > 0 else "below"
                parts.append(
                    f"This level is {abs(zgl.distance_percent):.1%} "
                    f"{direction} the current underlying price."
                )

            if zgl.confidence >= CONFIDENCE_HIGH:
                parts.append("Confidence in this estimate is high.")
            elif zgl.confidence >= CONFIDENCE_MODERATE:
                parts.append("Confidence in this estimate is moderate.")
            elif zgl.confidence >= CONFIDENCE_LOW:
                parts.append("Confidence in this estimate is low.")
            else:
                parts.append("Confidence in this estimate is very low.")
        else:
            parts.append("Zero gamma level cannot be identified from available data.")

        return " ".join(parts)

    def _walls_section(self, analysis: GammaExposureAnalysis) -> str:
        parts: list[str] = ["Gamma Walls:"]

        call = analysis.call_wall
        put = analysis.put_wall

        if call is not None and call.strike is not None:
            parts.append(
                f"Call wall at {call.strike:.2f} with gamma "
                f"concentration {call.gamma_concentration:.2f}."
            )
        else:
            parts.append("No significant call wall identified.")

        if put is not None and put.strike is not None:
            parts.append(
                f"Put wall at {put.strike:.2f} with gamma "
                f"concentration {put.gamma_concentration:.2f}."
            )
        else:
            parts.append("No significant put wall identified.")

        if call is not None and put is not None:
            spread = (
                abs(call.strike - put.strike)
                if (call.strike is not None and put.strike is not None)
                else None
            )
            if spread is not None:
                parts.append(f"Wall corridor width is {spread:.2f}.")

        return " ".join(parts)

    def _pinning_section(self, analysis: GammaExposureAnalysis) -> str:
        parts: list[str] = ["Pinning Risk:"]

        prob = analysis.pinning_probability

        if prob is PinningProbability.EXTREME:
            parts.append(
                "Extreme pinning probability. Price is highly likely "
                "to be drawn toward the zero-gamma level or gamma "
                "walls. Expect tight range with low realised "
                "volatility."
            )
        elif prob is PinningProbability.HIGH:
            parts.append(
                "High pinning probability. Dealer hedging is expected "
                "to create significant mean-reverting pressure near "
                "key gamma levels."
            )
        elif prob is PinningProbability.MEDIUM:
            parts.append(
                "Moderate pinning probability. Some mean-reverting "
                "pressure exists but may not dominate price action."
            )
        elif prob is PinningProbability.LOW:
            parts.append(
                "Low pinning probability. Gamma levels are unlikely "
                "to materially influence near-term price action."
            )
        else:
            parts.append("Pinning probability cannot be assessed from available data.")

        return " ".join(parts)

    def _volatility_section(
        self,
        analysis: GammaExposureAnalysis,
    ) -> str:
        parts: list[str] = ["Volatility Implications:"]

        expansion = analysis.volatility_expansion_probability

        if expansion >= CONFIDENCE_HIGH:
            parts.append(
                "High probability of volatility expansion. Short "
                "gamma conditions suggest acceleration risk."
            )
        elif expansion >= CONFIDENCE_MODERATE:
            parts.append(
                "Moderate probability of volatility expansion. "
                "Gamma conditions do not strongly suppress or "
                "amplify volatility."
            )
        elif expansion >= CONFIDENCE_LOW:
            parts.append(
                "Low probability of volatility expansion. Long "
                "gamma conditions suppress realised volatility."
            )
        else:
            parts.append(
                "Volatility expansion probability cannot be "
                "assessed from available data."
            )

        return " ".join(parts)

    def _institutional_section(
        self,
        analysis: GammaExposureAnalysis,
    ) -> str:
        parts: list[str] = ["Institutional Interpretation:"]

        regime = analysis.gamma_regime
        pinning = analysis.pinning_probability
        expansion = analysis.volatility_expansion_probability

        if regime is GammaRegime.POSITIVE and pinning in (
            PinningProbability.HIGH,
            PinningProbability.EXTREME,
        ):
            parts.append(
                "Long gamma with elevated pinning probability "
                "suggests a range-bound, mean-reverting regime. "
                "Consider mean-reversion strategies and avoid "
                "trend-following approaches."
            )
        elif regime is GammaRegime.NEGATIVE and expansion >= CONFIDENCE_MODERATE:
            parts.append(
                "Short gamma with elevated expansion probability "
                "suggests a trending, momentum-driven regime. "
                "Consider trend-following approaches and maintain "
                "appropriate position sizing for gap risk."
            )
        elif regime is GammaRegime.POSITIVE:
            parts.append(
                "Long gamma conditions suggest dealers provide "
                "liquidity during moves. Expect resistance at "
                "extremes and support on pullbacks."
            )
        elif regime is GammaRegime.NEGATIVE:
            parts.append(
                "Short gamma conditions suggest dealers consume "
                "liquidity during moves. Expect acceleration "
                "through key levels."
            )
        else:
            parts.append(
                "Gamma exposure is insufficiently characterised "
                "to draw institutional conclusions. Cross-reference "
                "with other market intelligence."
            )

        if analysis.confidence < 0.3:
            parts.append(
                "Low confidence suggests limited data availability. "
                "Interpret with caution."
            )

        return " ".join(parts)

    # ------------------------------------------------------------------
    # Empty / fallback analysis
    # ------------------------------------------------------------------

    def _empty_analysis(self, reason: str) -> GammaExposureAnalysis:
        analysis = GammaExposureAnalysis.neutral_placeholder()
        object.__setattr__(analysis, "warnings", (reason,))
        explanation = GammaExposureExplanation(
            gamma_regime="Gamma regime assessment unavailable: no inputs provided.",
            zero_gamma="Zero gamma level assessment unavailable: no inputs provided.",
            gamma_walls="Gamma walls assessment unavailable: no inputs provided.",
            pinning_risk="Pinning risk assessment unavailable: no inputs provided.",
            volatility_implications="Volatility implications unavailable: no inputs provided.",
            institutional_interpretation="Institutional Interpretation: Gamma exposure data is unavailable.",
        )
        object.__setattr__(analysis, "explanation", explanation)
        return analysis
