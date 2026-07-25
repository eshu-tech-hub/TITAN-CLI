from dataclasses import dataclass

from titan.portfolio.models import (
    CorrelationAnalysis,
    CorrelationLevel,
    ExistingPortfolio,
    HedgingAction,
    HedgingRecommendation,
    PortfolioExposure,
    PortfolioSnapshot,
)


@dataclass(slots=True)
class HedgingAnalyzer:
    """Analyses portfolio hedging needs.

    Recommends:
        - No hedge required (well-diversified).
        - Reduce exposure (over-concentrated).
        - Increase hedge (unbalanced Greeks).
        - Diversify (sector or symbol concentration).
    """

    name: str = "HedgingAnalyzer"

    def analyze(
        self,
        portfolio: ExistingPortfolio,
        snapshot: PortfolioSnapshot,
        exposure: PortfolioExposure,
        correlation: CorrelationAnalysis,
    ) -> HedgingRecommendation:
        """Analyse hedging needs for the portfolio.

        Args:
            portfolio: Existing portfolio with open positions.
            snapshot: Current portfolio snapshot.
            exposure: Portfolio Greeks and directional exposure.
            correlation: Correlation risk assessment.

        Returns:
            Hedging recommendation.
        """
        reasons: list[str] = []
        instruments: list[str] = []

        if not portfolio.positions:
            return HedgingRecommendation(
                action=HedgingAction.NO_HEDGE_REQUIRED,
                reason="No open positions. No hedging required.",
            )

        if snapshot.utilization >= 0.9:
            reasons.append(
                f"Portfolio utilisation at {snapshot.utilization:.0%} — consider reducing exposure."
            )
            return HedgingRecommendation(
                action=HedgingAction.REDUCE_EXPOSURE,
                reason="; ".join(reasons),
                max_cost=snapshot.capital_used * 0.05,
            )

        if exposure.symbol_concentration >= 0.25:
            reasons.append(
                f"Symbol concentration at {exposure.symbol_concentration:.0%} "
                f"— diversify across more symbols."
            )
            return HedgingRecommendation(
                action=HedgingAction.DIVERSIFY,
                reason="; ".join(reasons),
                max_cost=snapshot.total_capital * 0.02,
            )

        if exposure.sector_concentration >= 0.40:
            reasons.append(
                f"Sector concentration at {exposure.sector_concentration:.0%} "
                f"— consider sector diversification."
            )
            return HedgingRecommendation(
                action=HedgingAction.DIVERSIFY,
                reason="; ".join(reasons),
                suggested_instruments=("Sector ETF", "Index Futures"),
                max_cost=snapshot.total_capital * 0.02,
            )

        if correlation.overall_correlation_level in (
            CorrelationLevel.HIGH,
            CorrelationLevel.EXTREME,
        ):
            reasons.append(
                f"High correlation risk ({correlation.overall_correlation_level.value}) "
                f"— consider uncorrelated positions."
            )
            return HedgingRecommendation(
                action=HedgingAction.DIVERSIFY,
                reason="; ".join(reasons),
                max_cost=snapshot.total_capital * 0.03,
            )

        if (
            exposure.directional_bias is not None
            and abs(exposure.directional_bias) > 0.7
        ):
            bias_dir = "long" if exposure.directional_bias > 0 else "short"
            reasons.append(
                f"Strong {bias_dir} bias (net delta {exposure.directional_bias:.2f}) "
                f"— consider hedging directional risk."
            )
            instruments.append(
                "Index Futures" if exposure.directional_bias > 0 else "Index Puts"
            )
            return HedgingRecommendation(
                action=HedgingAction.INCREASE_HEDGE,
                reason="; ".join(reasons),
                suggested_instruments=tuple(instruments),
                max_cost=snapshot.total_capital * 0.03,
            )

        return HedgingRecommendation(
            action=HedgingAction.NO_HEDGE_REQUIRED,
            reason="Portfolio is well-diversified. No hedging required.",
        )
