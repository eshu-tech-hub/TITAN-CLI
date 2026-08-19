"""Trend Regime Analyzer.

Synthesises Market Structure and VWAP intelligence to assess trend
strength, alignment, and whether the environment favours momentum or
mean reversion.

Pure synthesis — consumes existing intelligence, no market calculations.
"""

from titan.market.intelligence.models import (
    MarketStructureAnalysis,
    StructureState,
    TrendDirection,
    TrendRegime,
    VWAPAnalysis,
)

CONFIDENCE_HIGH = 0.7
CONFIDENCE_MODERATE = 0.5
CONFIDENCE_LOW = 0.3

TREND_STRENGTH_HIGH = 0.6
TREND_STRENGTH_MODERATE = 0.35


class TrendRegimeAnalyzer:
    """Synthesise trend regime from market structure and VWAP.

    Consumes MarketStructureAnalysis and VWAPAnalysis to determine
    trend direction, strength, momentum vs mean reversion favour,
    and trend alignment.
    """

    name = "TrendRegimeAnalyzer"

    def analyze(
        self,
        market_structure: MarketStructureAnalysis | None,
        vwap: VWAPAnalysis | None,
    ) -> TrendRegime:
        """Determine trend regime characteristics.

        Args:
            market_structure: Market structure intelligence output.
            vwap: VWAP intelligence output.

        Returns:
            Trend regime assessment.
        """

        reasons: list[str] = []

        if market_structure is None or vwap is None:
            return TrendRegime(
                confidence=0.0,
                reasons=("Insufficient intelligence inputs.",),
            )

        if (
            market_structure.confidence < CONFIDENCE_LOW
            and vwap.confidence < CONFIDENCE_LOW
        ):
            return TrendRegime(
                confidence=0.0,
                reasons=("All inputs have low confidence.",),
            )

        direction = self._direction(market_structure)
        strength = self._strength(market_structure)
        aligned = self._aligned(market_structure, vwap)
        momentum_env = self._momentum_environment(
            market_structure, vwap, direction, aligned
        )
        mean_rev_env = self._mean_reversion_environment(
            market_structure, direction, aligned
        )
        confidence = self._confidence(market_structure, vwap)

        reasons.extend(
            self._reasons(
                direction=direction,
                strength=strength,
                aligned=aligned,
                momentum=momentum_env,
                mean_rev=mean_rev_env,
            )
        )

        return TrendRegime(
            direction=direction,
            strength=strength,
            momentum_environment=momentum_env,
            mean_reversion_environment=mean_rev_env,
            aligned=aligned,
            confidence=confidence,
            reasons=tuple(reasons),
        )

    def _direction(
        self,
        ms: MarketStructureAnalysis,
    ) -> TrendDirection:
        if ms.structure_state is StructureState.RANGING:
            return TrendDirection.SIDEWAYS
        if ms.primary_trend is not TrendDirection.UNKNOWN:
            return ms.primary_trend
        return TrendDirection.UNKNOWN

    def _strength(
        self,
        ms: MarketStructureAnalysis,
    ) -> float:
        return ms.trend_strength

    def _aligned(
        self,
        ms: MarketStructureAnalysis,
        vwap: VWAPAnalysis,
    ) -> bool:
        if ms.primary_trend is TrendDirection.BULLISH and vwap.bias.value == "bullish":
            return True
        return bool(ms.primary_trend is TrendDirection.BEARISH and vwap.bias.value == "bearish")

    def _momentum_environment(
        self,
        ms: MarketStructureAnalysis,
        vwap: VWAPAnalysis,
        direction: TrendDirection,
        aligned: bool,
    ) -> bool:
        if direction is TrendDirection.UNKNOWN:
            return False
        trending = ms.structure_state is StructureState.TRENDING
        strong = ms.trend_strength >= TREND_STRENGTH_HIGH
        return trending and strong and aligned

    def _mean_reversion_environment(
        self,
        ms: MarketStructureAnalysis,
        direction: TrendDirection,
        aligned: bool,
    ) -> bool:
        if direction is TrendDirection.UNKNOWN:
            return False
        ranging = ms.structure_state is StructureState.RANGING
        transition = ms.structure_state is StructureState.TRANSITION
        return (ranging or transition) or not aligned

    def _confidence(
        self,
        ms: MarketStructureAnalysis,
        vwap: VWAPAnalysis,
    ) -> float:
        confidences: list[float] = []
        weights: list[float] = []

        if ms.confidence > 0:
            confidences.append(ms.confidence)
            weights.append(0.6)
        if vwap.confidence > 0:
            confidences.append(vwap.confidence)
            weights.append(0.4)

        if not confidences:
            return 0.0

        total = sum(c * w for c, w in zip(confidences, weights))
        total_w = sum(weights)
        return total / total_w if total_w > 0 else 0.0

    def _reasons(
        self,
        direction: TrendDirection,
        strength: float,
        aligned: bool,
        momentum: bool,
        mean_rev: bool,
    ) -> list[str]:
        reasons: list[str] = []

        reasons.append(f"Trend is {direction.value} (strength: {strength:.2f}).")

        if aligned:
            reasons.append("Price trend and VWAP bias are aligned.")
        else:
            reasons.append("Price trend and VWAP bias diverge.")

        if momentum:
            reasons.append("Environment favours momentum strategies.")
        if mean_rev:
            reasons.append("Environment favours mean reversion strategies.")

        return reasons
