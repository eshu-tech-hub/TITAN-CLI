from typing import Any

from titan.core.evidence import (
    Confidence,
    Evidence,
    EvidenceCategory,
    EvidenceSignal,
    Score,
)
from titan.options.analytics.butterfly import ButterflyAnalyzer
from titan.options.analytics.models import (
    ButterflyResult,
    MarketBias,
    OptionChainSnapshot,
    RiskReversalResult,
    SkewAnalysis,
    SkewDirection,
    SkewExplanation,
    SkewStrength,
)
from titan.options.analytics.risk_reversal import RiskReversalAnalyzer

NEUTRAL_SCORE = 50.0
SKEW_DIRECTION_THRESHOLD = 0.01
SKEW_STRENGTH_LOW = 0.01
SKEW_STRENGTH_MEDIUM = 0.03
SKEW_STRENGTH_HIGH = 0.06
SKEW_STRENGTH_EXTREME = 0.10


class SkewAnalyzer:
    """Analyze implied volatility skew across option strikes.

    Orchestrates RiskReversalAnalyzer and ButterflyAnalyzer to produce
    combined institutional-grade skew intelligence.

    Consumes supplied implied volatility values only.
    Never estimates delta or implied volatility.
    """

    name = "SkewAnalyzer"

    def __init__(
        self,
        rr_analyzer: RiskReversalAnalyzer | None = None,
        butterfly_analyzer: ButterflyAnalyzer | None = None,
    ) -> None:
        self._rr = rr_analyzer or RiskReversalAnalyzer()
        self._bf = butterfly_analyzer or ButterflyAnalyzer()

    def analyze(self, chain: OptionChainSnapshot) -> SkewAnalysis:
        if not isinstance(chain, OptionChainSnapshot):
            raise TypeError("chain must be an OptionChainSnapshot.")

        if not chain.strikes:
            return self._empty_analysis("Chain has no strikes.")

        rr_result = self._rr.analyze(chain)
        bf_result = self._bf.analyze(chain)

        direction = self._determine_direction(rr_result, bf_result)
        strength = self._determine_strength(rr_result, bf_result)
        overall_bias = self._determine_overall_bias(rr_result.bias, direction)
        confidence = self._calculate_confidence(rr_result, bf_result)
        warnings = self._combine_warnings(rr_result, bf_result)

        analysis = SkewAnalysis(
            direction=direction,
            strength=strength,
            risk_reversal=rr_result,
            butterfly=bf_result,
            overall_bias=overall_bias,
            confidence=confidence,
            warnings=warnings,
            metadata=self._metadata(chain, direction, strength, overall_bias),
        )

        evidence = self._to_evidence(analysis, rr_result, bf_result)
        explanation = self._explanation(analysis)

        object.__setattr__(analysis, "evidence", evidence)
        object.__setattr__(analysis, "explanation", explanation)

        return analysis

    def _determine_direction(
        self,
        rr_result: RiskReversalResult,
        bf_result: ButterflyResult,
    ) -> SkewDirection:
        rr_bias = rr_result.bias
        rr_conf = rr_result.confidence

        if rr_conf >= 0.3 and rr_bias is MarketBias.BEARISH:
            return SkewDirection.LEFT
        if rr_conf >= 0.3 and rr_bias is MarketBias.BULLISH:
            return SkewDirection.RIGHT

        if rr_bias is MarketBias.NEUTRAL and rr_conf >= 0.3:
            return SkewDirection.SYMMETRIC

        if bf_result.atm_richness is not None and bf_result.confidence >= 0.3:
            return SkewDirection.SYMMETRIC

        return SkewDirection.UNKNOWN

    def _determine_strength(
        self,
        rr_result: RiskReversalResult,
        bf_result: ButterflyResult,
    ) -> SkewStrength:
        rr_magnitudes: list[float] = []
        if rr_result.twenty_five_delta_rr is not None:
            rr_magnitudes.append(abs(rr_result.twenty_five_delta_rr))
        if rr_result.general_rr is not None:
            rr_magnitudes.append(abs(rr_result.general_rr))

        if not rr_magnitudes:
            if bf_result.relative_curvature is not None:
                curv = abs(bf_result.relative_curvature)
                return self._strength_from_curvature(curv)
            return SkewStrength.UNKNOWN

        avg_mag = sum(rr_magnitudes) / len(rr_magnitudes)
        return self._strength_from_rr(avg_mag)

    def _strength_from_rr(self, magnitude: float) -> SkewStrength:
        if magnitude >= SKEW_STRENGTH_EXTREME:
            return SkewStrength.EXTREME
        if magnitude >= SKEW_STRENGTH_HIGH:
            return SkewStrength.HIGH
        if magnitude >= SKEW_STRENGTH_MEDIUM:
            return SkewStrength.MEDIUM
        if magnitude >= 0.0:
            return SkewStrength.LOW
        return SkewStrength.UNKNOWN

    def _strength_from_curvature(self, curvature: float) -> SkewStrength:
        if curvature >= 0.35:
            return SkewStrength.EXTREME
        if curvature >= 0.20:
            return SkewStrength.HIGH
        if curvature >= 0.10:
            return SkewStrength.MEDIUM
        if curvature >= 0.05:
            return SkewStrength.LOW
        return SkewStrength.UNKNOWN

    def _determine_overall_bias(
        self,
        rr_bias: MarketBias,
        direction: SkewDirection,
    ) -> MarketBias:
        if rr_bias is not MarketBias.UNKNOWN:
            return rr_bias
        if direction is SkewDirection.LEFT:
            return MarketBias.BEARISH
        if direction is SkewDirection.RIGHT:
            return MarketBias.BULLISH
        if direction is SkewDirection.SYMMETRIC:
            return MarketBias.NEUTRAL
        return MarketBias.UNKNOWN

    def _calculate_confidence(
        self,
        rr_result: RiskReversalResult,
        bf_result: ButterflyResult,
    ) -> float:
        confidences = [v for v in (rr_result.confidence, bf_result.confidence) if v > 0]
        if not confidences:
            return 0.0
        return sum(confidences) / len(confidences)

    def _combine_warnings(
        self,
        rr_result: RiskReversalResult,
        bf_result: ButterflyResult,
    ) -> tuple[str, ...]:
        combined: list[str] = []
        for w in rr_result.warnings:
            if w not in combined:
                combined.append(w)
        for w in bf_result.warnings:
            if w not in combined:
                combined.append(w)
        return tuple(combined)

    def _metadata(
        self,
        chain: OptionChainSnapshot,
        direction: SkewDirection,
        strength: SkewStrength,
        overall_bias: MarketBias,
    ) -> dict[str, Any]:
        return {
            "analyzer": self.name,
            "underlying": chain.underlying,
            "expiry": chain.expiry.isoformat() if chain.expiry else None,
            "skew_direction": direction.value,
            "skew_strength": strength.value,
            "overall_bias": overall_bias.value,
        }

    # ------------------------------------------------------------------
    # Evidence generation
    # ------------------------------------------------------------------

    def _evidence_signal(self, analysis: SkewAnalysis) -> EvidenceSignal:
        if analysis.overall_bias is MarketBias.BEARISH:
            return EvidenceSignal.BEARISH
        if analysis.overall_bias is MarketBias.BULLISH:
            return EvidenceSignal.BULLISH
        if analysis.overall_bias is MarketBias.NEUTRAL:
            return EvidenceSignal.NEUTRAL
        return EvidenceSignal.UNKNOWN

    def _evidence_score(self, analysis: SkewAnalysis) -> float:
        base = NEUTRAL_SCORE
        if analysis.direction in (SkewDirection.LEFT, SkewDirection.RIGHT):
            if analysis.strength in (SkewStrength.HIGH, SkewStrength.EXTREME):
                return base + (analysis.confidence * 40.0)
            return base + (analysis.confidence * 25.0)
        return base

    def _evidence_reasons(self, analysis: SkewAnalysis) -> tuple[str, ...]:
        reasons: list[str] = []
        if analysis.direction is not SkewDirection.UNKNOWN:
            reasons.append(f"Skew direction is {analysis.direction.value}.")
        if analysis.strength is not SkewStrength.UNKNOWN:
            reasons.append(f"Skew strength is {analysis.strength.value}.")

        rr = analysis.risk_reversal
        if rr is not None:
            if rr.twenty_five_delta_rr is not None:
                reasons.append(
                    f"25-delta risk reversal is {rr.twenty_five_delta_rr:+.4f} "
                    f"(put IV {rr.twenty_five_delta_put_iv:.2%}, "
                    f"call IV {rr.twenty_five_delta_call_iv:.2%})."
                )
            if rr.general_rr is not None:
                reasons.append(
                    f"General risk reversal (OTM put IV - OTM call IV) "
                    f"is {rr.general_rr:+.4f}."
                )
            if rr.bias is not MarketBias.UNKNOWN:
                reasons.append(f"Risk reversal bias is {rr.bias.value}.")

        bf = analysis.butterfly
        if bf is not None:
            if bf.atm_richness is not None:
                reasons.append(f"ATM richness is {bf.atm_richness:+.4f}.")
            if bf.wing_richness is not None:
                reasons.append(f"Wing richness is {bf.wing_richness:+.4f}.")
            if bf.relative_curvature is not None:
                reasons.append(f"Relative curvature is {bf.relative_curvature:.4f}.")

        return tuple(reasons)

    def _to_evidence(
        self,
        analysis: SkewAnalysis,
        rr_result: RiskReversalResult,
        bf_result: ButterflyResult,
    ) -> Evidence:
        return Evidence(
            source="Volatility Skew",
            category=EvidenceCategory.OPTION_CHAIN,
            signal=self._evidence_signal(analysis),
            score=Score(self._evidence_score(analysis)),
            confidence=Confidence(analysis.confidence),
            weight=1.0,
            reasons=self._evidence_reasons(analysis),
            warnings=analysis.warnings,
            metadata={
                "analyzer": self.name,
                "skew_direction": analysis.direction.value,
                "skew_strength": analysis.strength.value,
                "overall_bias": analysis.overall_bias.value,
                "rr_25d": rr_result.twenty_five_delta_rr,
                "rr_general": rr_result.general_rr,
                "atm_richness": bf_result.atm_richness,
                "wing_richness": bf_result.wing_richness,
                "relative_curvature": bf_result.relative_curvature,
            },
        )

    # ------------------------------------------------------------------
    # Explanation generation
    # ------------------------------------------------------------------

    def _explanation(self, analysis: SkewAnalysis) -> SkewExplanation:
        return SkewExplanation(
            skew_direction=self._skew_direction_section(analysis),
            risk_reversal=self._risk_reversal_section(analysis),
            butterfly=self._butterfly_section(analysis),
            institutional_interpretation=self._institutional_section(analysis),
            risk_assessment=self._risk_assessment_section(analysis),
            warnings=analysis.warnings,
        )

    def _skew_direction_section(self, analysis: SkewAnalysis) -> str:
        direction_desc = {
            SkewDirection.LEFT: (
                "The volatility skew is left-sided: out-of-the-money put options "
                "carry higher implied volatility than out-of-the-money call options."
            ),
            SkewDirection.RIGHT: (
                "The volatility skew is right-sided: out-of-the-money call options "
                "carry higher implied volatility than out-of-the-money put options."
            ),
            SkewDirection.SYMMETRIC: (
                "The volatility skew is symmetric with balanced implied volatility "
                "across put and call sides."
            ),
            SkewDirection.UNKNOWN: (
                "Volatility skew direction cannot be determined from available data."
            ),
        }

        strength_desc = {
            SkewStrength.LOW: " The skew magnitude is low.",
            SkewStrength.MEDIUM: " The skew magnitude is moderate.",
            SkewStrength.HIGH: " The skew magnitude is high.",
            SkewStrength.EXTREME: " The skew magnitude is extreme.",
            SkewStrength.UNKNOWN: "",
        }

        base = direction_desc.get(
            analysis.direction,
            "Skew direction is unavailable.",
        )
        extra = strength_desc.get(analysis.strength, "")
        return base + extra

    def _risk_reversal_section(self, analysis: SkewAnalysis) -> str:
        rr = analysis.risk_reversal
        if rr is None:
            return "Risk reversal analysis is unavailable."

        parts: list[str] = ["Risk Reversal Analysis:"]

        if rr.twenty_five_delta_rr is not None:
            parts.append(
                f"25-delta risk reversal is {rr.twenty_five_delta_rr:+.4f} "
                f"(put strike {rr.twenty_five_delta_put_strike:.2f} at "
                f"{rr.twenty_five_delta_put_iv:.2%}, call strike "
                f"{rr.twenty_five_delta_call_strike:.2f} at "
                f"{rr.twenty_five_delta_call_iv:.2%})."
            )
        elif rr.general_rr is not None:
            parts.append(
                "25-delta risk reversal unavailable. Using general risk reversal."
            )

        if rr.general_rr is not None:
            parts.append(
                f"General risk reversal (OTM put IV - OTM call IV) is "
                f"{rr.general_rr:+.4f} "
                f"(avg OTM put IV {rr.avg_otm_put_iv:.2%}, "
                f"avg OTM call IV {rr.avg_otm_call_iv:.2%})."
            )

        if rr.bias is MarketBias.BEARISH:
            parts.append(
                "Risk reversal indicates bearish bias: put options are "
                "priced at higher implied volatility than call options."
            )
        elif rr.bias is MarketBias.BULLISH:
            parts.append(
                "Risk reversal indicates bullish bias: call options are "
                "priced at higher implied volatility than put options."
            )
        elif rr.bias is MarketBias.NEUTRAL:
            parts.append(
                "Risk reversal is neutral: put and call implied volatilities "
                "are balanced."
            )

        return " ".join(parts)

    def _butterfly_section(self, analysis: SkewAnalysis) -> str:
        bf = analysis.butterfly
        if bf is None:
            return "Butterfly analysis is unavailable."

        parts: list[str] = ["Butterfly Analysis:"]

        if bf.atm_richness is not None:
            if bf.atm_richness > 0:
                parts.append(
                    f"ATM implied volatility is rich relative to near wings "
                    f"by {bf.atm_richness:.2%}."
                )
            elif bf.atm_richness < 0:
                parts.append(
                    f"ATM implied volatility is cheap relative to near wings "
                    f"by {abs(bf.atm_richness):.2%}."
                )
            else:
                parts.append("ATM implied volatility is at parity with near wings.")
        else:
            parts.append("ATM richness could not be determined.")

        if bf.wing_richness is not None:
            if bf.wing_richness > 0:
                parts.append(
                    f"Far wings are expensive relative to near wings "
                    f"by {bf.wing_richness:.2%}."
                )
            elif bf.wing_richness < 0:
                parts.append(
                    f"Far wings are cheap relative to near wings "
                    f"by {abs(bf.wing_richness):.2%}."
                )
            else:
                parts.append("Wing pricing is uniform.")

        if bf.relative_curvature is not None:
            parts.append(f"Relative curvature is {bf.relative_curvature:.4f}.")

        if bf.confidence > 0.0:
            parts.append(f"Butterfly analysis confidence is {bf.confidence:.0%}.")

        return " ".join(parts)

    def _institutional_section(self, analysis: SkewAnalysis) -> str:
        parts: list[str] = ["Institutional Interpretation:"]

        if analysis.direction is SkewDirection.LEFT:
            parts.append(
                "Elevated OTM put implied volatility indicates market "
                "participants are pricing in heightened downside risk. "
                "This is typical of protective hedging demand or "
                "distribution of tail risk concerns."
            )
        elif analysis.direction is SkewDirection.RIGHT:
            parts.append(
                "Elevated OTM call implied volatility suggests speculative "
                "demand for upside exposure. This may indicate market "
                "participants are positioning for a potential upward move."
            )
        elif analysis.direction is SkewDirection.SYMMETRIC:
            parts.append(
                "Balanced put and call implied volatility suggests no "
                "directional premium is being priced by the market. "
                "Tail-risk pricing is symmetric."
            )

        if analysis.strength is SkewStrength.HIGH:
            parts.append("The skew strength is high, warranting close monitoring.")
        elif analysis.strength is SkewStrength.EXTREME:
            parts.append(
                "The skew strength is extreme. This may indicate market "
                "stress or dislocated option pricing."
            )

        return " ".join(parts)

    def _risk_assessment_section(self, analysis: SkewAnalysis) -> str:
        parts: list[str] = ["Risk Assessment:"]

        if analysis.direction is SkewDirection.LEFT:
            parts.append(
                "Downside tail risk is elevated. Consider reviewing "
                "portfolio tail-risk hedging and put protection costs."
            )
        elif analysis.direction is SkewDirection.RIGHT:
            parts.append(
                "Upside tail risk is elevated. Monitor for potential "
                "short-squeeze or momentum-driven upside scenarios."
            )
        elif analysis.direction is SkewDirection.SYMMETRIC:
            parts.append(
                "Tail risk is symmetrically priced. Standard risk "
                "management protocols apply."
            )
        else:
            parts.append(
                "Skew direction unknown. Risk assessment is limited by available data."
            )

        if analysis.strength is SkewStrength.HIGH:
            parts.append("Consider adjusting position sizing for tail risk.")
        elif analysis.strength is SkewStrength.EXTREME:
            parts.append(
                "Extreme skew warrants heightened vigilance. Consider "
                "reducing directional exposure until skew normalizes."
            )

        if analysis.confidence < 0.3:
            parts.append(
                "Low confidence in skew analysis. Cross-reference with "
                "other market indicators before acting."
            )

        return " ".join(parts)

    def _empty_analysis(self, reason: str) -> SkewAnalysis:
        analysis = SkewAnalysis.neutral_placeholder()
        object.__setattr__(analysis, "warnings", (reason,))
        explanation = SkewExplanation(
            skew_direction="Skew direction is unavailable.",
            risk_reversal="Risk reversal analysis is unavailable.",
            butterfly="Butterfly analysis is unavailable.",
            institutional_interpretation="Institutional Interpretation: Skew data is unavailable.",
            risk_assessment="Risk Assessment: Skew data is unavailable.",
            warnings=(reason,),
        )
        object.__setattr__(analysis, "explanation", explanation)
        return analysis
