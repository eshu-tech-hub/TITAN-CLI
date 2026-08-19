"""Strategy Suitability Analyzer.

Determines which trading strategies are suitable for the current
market environment based on synthesised regime intelligence.

Pure synthesis — consumes existing intelligence, no market calculations.
Must NOT be interpreted as trade recommendations.
"""

from titan.market.intelligence.models import (
    MarketRegime,
    MarketStructureAnalysis,
    ParticipationRegime,
    StrategySuitability,
    StrategyType,
    TrendRegime,
)

CONFIDENCE_LOW = 0.3


class StrategySuitabilityAnalyzer:
    """Determine strategy suitability from regime context.

    Consumes TrendRegime, ParticipationRegime, and market structure
    to identify the most suitable strategy approach.
    """

    name = "StrategySuitabilityAnalyzer"

    def analyze(
        self,
        trend: TrendRegime | None,
        participation: ParticipationRegime | None,
        market_regime: MarketRegime,
        market_structure: MarketStructureAnalysis | None,
    ) -> StrategySuitability:
        """Determine strategy suitability.

        Args:
            trend: Trend regime assessment.
            participation: Participation regime assessment.
            market_regime: Determined primary market regime.
            market_structure: Market structure intelligence.

        Returns:
            Strategy suitability assessment.
        """

        reasons: list[str] = []

        if trend is None or market_structure is None:
            return StrategySuitability(
                confidence=0.0,
                reasons=("Insufficient intelligence inputs.",),
            )

        preferred = self._preferred_strategy(market_regime, trend, participation)
        avoid_breakouts = self._avoid_breakouts(market_regime, trend)
        avoid_mean_rev = self._avoid_mean_reversion(market_regime, trend)
        confidence = self._confidence(trend, participation, market_structure)

        reasons.extend(
            self._reasons(
                preferred=preferred,
                avoid_breakouts=avoid_breakouts,
                avoid_mean_rev=avoid_mean_rev,
            )
        )

        return StrategySuitability(
            preferred=preferred,
            avoid_breakouts=avoid_breakouts,
            avoid_mean_reversion=avoid_mean_rev,
            confidence=confidence,
            reasons=tuple(reasons),
        )

    def _preferred_strategy(
        self,
        regime: MarketRegime,
        trend: TrendRegime | None,
        participation: ParticipationRegime | None,
    ) -> StrategyType:
        regime_map: dict[MarketRegime, StrategyType] = {
            MarketRegime.TRENDING_BULLISH: StrategyType.TREND_FOLLOWING,
            MarketRegime.TRENDING_BEARISH: StrategyType.TREND_FOLLOWING,
            MarketRegime.BREAKOUT: StrategyType.BREAKOUT,
            MarketRegime.BREAKDOWN: StrategyType.BREAKOUT,
            MarketRegime.RANGING: StrategyType.RANGE_TRADING,
            MarketRegime.COMPRESSION: StrategyType.VOLATILITY_CONTRACTION,
            MarketRegime.EXPANSION: StrategyType.VOLATILITY_EXPANSION,
            MarketRegime.TRANSITION: StrategyType.MEAN_REVERSION,
            MarketRegime.MIXED: StrategyType.NO_TRADE,
        }

        preferred = regime_map.get(regime, StrategyType.NO_TRADE)

        if (
            preferred is StrategyType.TREND_FOLLOWING
            and trend is not None
            and trend.mean_reversion_environment
        ):
            return StrategyType.MEAN_REVERSION

        return preferred

    def _avoid_breakouts(
        self,
        regime: MarketRegime,
        trend: TrendRegime | None,
    ) -> bool:
        if regime in (
            MarketRegime.RANGING,
            MarketRegime.COMPRESSION,
            MarketRegime.MIXED,
        ):
            return True
        return bool(trend is not None and trend.mean_reversion_environment)

    def _avoid_mean_reversion(
        self,
        regime: MarketRegime,
        trend: TrendRegime | None,
    ) -> bool:
        if regime in (
            MarketRegime.TRENDING_BULLISH,
            MarketRegime.TRENDING_BEARISH,
            MarketRegime.BREAKOUT,
            MarketRegime.BREAKDOWN,
        ):
            return True
        return bool(trend is not None and trend.momentum_environment)

    def _confidence(
        self,
        trend: TrendRegime | None,
        participation: ParticipationRegime | None,
        ms: MarketStructureAnalysis | None,
    ) -> float:
        confidences: list[float] = []
        weights: list[float] = []

        if trend is not None and trend.confidence > 0:
            confidences.append(trend.confidence)
            weights.append(0.4)
        if participation is not None and participation.confidence > 0:
            confidences.append(participation.confidence)
            weights.append(0.3)
        if ms is not None and ms.confidence > 0:
            confidences.append(ms.confidence)
            weights.append(0.3)

        if not confidences:
            return 0.0

        total = sum(c * w for c, w in zip(confidences, weights))
        total_w = sum(weights)
        return total / total_w if total_w > 0 else 0.0

    def _reasons(
        self,
        preferred: StrategyType,
        avoid_breakouts: bool,
        avoid_mean_rev: bool,
    ) -> list[str]:
        reasons: list[str] = []

        reasons.append(f"Preferred strategy: {preferred.value}.")

        if avoid_breakouts:
            reasons.append(
                "Avoid breakout strategies — environment does not support them."
            )

        if avoid_mean_rev:
            reasons.append("Avoid mean reversion strategies — trend is strong.")

        return reasons
