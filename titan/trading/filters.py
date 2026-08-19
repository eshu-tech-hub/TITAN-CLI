from titan.events.models import EventRisk
from titan.options.analytics.models import ExecutionGrade
from titan.trading.models import (
    FilterCategory,
    FilterResult,
    TradeQualificationInput,
)

MIN_CONFIDENCE_THRESHOLD = 0.2
MIN_MODULES_REQUIRED = 3


class TradeFilterEngine:
    """Evaluates hard filters against all intelligence inputs.

    Any single hard filter failure immediately disqualifies the trade.
    """

    name = "TradeFilterEngine"

    def evaluate(self, inputs: TradeQualificationInput) -> tuple[FilterResult, ...]:
        """Evaluate all hard filters.

        Args:
            inputs: Aggregated intelligence inputs.

        Returns:
            Tuple of filter results, one per evaluated filter.
        """

        return (
            self._check_event_risk(inputs),
            self._check_liquidity_risk(inputs),
            self._check_confidence(inputs),
            self._check_conflicting_intelligence(inputs),
            self._check_sufficient_evidence(inputs),
            self._check_market_regime(inputs),
        )

    def has_failures(self, results: tuple[FilterResult, ...]) -> bool:
        """Check whether any filter failed.

        Args:
            results: Filter results to evaluate.

        Returns:
            True if any filter failed.
        """

        return any(not r.passed for r in results)

    def failed_filters(self, results: tuple[FilterResult, ...]) -> tuple[str, ...]:
        """Extract reasons from all failed filters.

        Args:
            results: Filter results to evaluate.

        Returns:
            Tuple of failure reasons.
        """

        return tuple(r.reason for r in results if not r.passed)

    def passed_filters(self, results: tuple[FilterResult, ...]) -> tuple[str, ...]:
        """Extract reasons from all passed filters.

        Args:
            results: Filter results to evaluate.

        Returns:
            Tuple of pass reasons.
        """

        return tuple(r.reason for r in results if r.passed)

    def _check_event_risk(self, inputs: TradeQualificationInput) -> FilterResult:
        """Reject if event risk is extreme.

        Checks EventAnalysis for extreme overall risk or explicit
        avoidance recommendation.
        """

        event = inputs.event_analysis
        if event is None:
            return FilterResult(
                filter_category=FilterCategory.HIGH_EVENT_RISK,
                passed=True,
                reason="Event intelligence unavailable — skipping event risk check.",
            )

        if event.overall_risk == EventRisk.EXTREME:
            return FilterResult(
                filter_category=FilterCategory.HIGH_EVENT_RISK,
                passed=False,
                reason=f"Extreme event risk detected: {event.overall_risk.value}.",
            )

        if (
            event.decision_context is not None
            and event.decision_context.avoid_new_positions
        ):
            return FilterResult(
                filter_category=FilterCategory.HIGH_EVENT_RISK,
                passed=False,
                reason="Event intelligence recommends avoiding new positions.",
            )

        return FilterResult(
            filter_category=FilterCategory.HIGH_EVENT_RISK,
            passed=True,
            reason=f"Event risk acceptable: {event.overall_risk.value}.",
        )

    def _check_liquidity_risk(self, inputs: TradeQualificationInput) -> FilterResult:
        """Reject if liquidity risk is extreme.

        Checks LiquidityAnalysis for failing execution grade or
        extreme liquidity risk classification.
        """

        liquidity = inputs.liquidity
        if liquidity is None:
            return FilterResult(
                filter_category=FilterCategory.EXTREME_LIQUIDITY_RISK,
                passed=True,
                reason="Liquidity intelligence unavailable — skipping liquidity risk check.",
            )

        if liquidity.execution_grade in (ExecutionGrade.F, ExecutionGrade.UNKNOWN):
            return FilterResult(
                filter_category=FilterCategory.EXTREME_LIQUIDITY_RISK,
                passed=False,
                reason=f"Extreme liquidity risk: execution grade {liquidity.execution_grade.value}.",
            )

        return FilterResult(
            filter_category=FilterCategory.EXTREME_LIQUIDITY_RISK,
            passed=True,
            reason=f"Liquidity acceptable: grade {liquidity.execution_grade.value}.",
        )

    def _check_confidence(self, inputs: TradeQualificationInput) -> FilterResult:
        """Reject if overall confidence across all modules is too low."""
        confidences: list[float] = []

        modules = [
            inputs.market_regime,
            inputs.option_chain,
            inputs.greeks,
            inputs.liquidity,
            inputs.volatility,
            inputs.dealer_positioning,
            inputs.gamma_exposure,
            inputs.vanna_exposure,
            inputs.charm_exposure,
            inputs.event_analysis,
            inputs.news_analysis,
        ]

        for module in modules:
            if module is not None and hasattr(module, "confidence"):
                c = module.confidence
                if isinstance(c, (int, float)) and c > 0:
                    confidences.append(float(c))

        if not confidences:
            return FilterResult(
                filter_category=FilterCategory.LOW_CONFIDENCE,
                passed=False,
                reason="No confidence data available from any intelligence module.",
            )

        avg_confidence = sum(confidences) / len(confidences)

        if avg_confidence < MIN_CONFIDENCE_THRESHOLD:
            return FilterResult(
                filter_category=FilterCategory.LOW_CONFIDENCE,
                passed=False,
                reason=f"Average confidence too low: {avg_confidence:.2f} (threshold: {MIN_CONFIDENCE_THRESHOLD}).",
            )

        return FilterResult(
            filter_category=FilterCategory.LOW_CONFIDENCE,
            passed=True,
            reason=f"Average confidence acceptable: {avg_confidence:.2f}.",
        )

    def _check_conflicting_intelligence(
        self, inputs: TradeQualificationInput
    ) -> FilterResult:
        """Reject if the fusion engine detected conflicting evidence."""

        fusion = inputs.intelligence_fusion
        if fusion is None:
            return FilterResult(
                filter_category=FilterCategory.CONFLICTING_INTELLIGENCE,
                passed=True,
                reason="Intelligence fusion unavailable — skipping conflict check.",
            )

        if fusion.conflicting_evidence:
            conflict_reasons = [c.reason for c in fusion.conflicting_evidence]
            return FilterResult(
                filter_category=FilterCategory.CONFLICTING_INTELLIGENCE,
                passed=False,
                reason=f"Conflicting intelligence detected: {'; '.join(conflict_reasons)}.",
            )

        return FilterResult(
            filter_category=FilterCategory.CONFLICTING_INTELLIGENCE,
            passed=True,
            reason="No conflicting intelligence detected.",
        )

    def _check_sufficient_evidence(
        self, inputs: TradeQualificationInput
    ) -> FilterResult:
        """Reject if insufficient intelligence modules are available."""

        modules = [
            inputs.market_regime,
            inputs.option_chain,
            inputs.greeks,
            inputs.liquidity,
            inputs.volatility,
            inputs.dealer_positioning,
            inputs.gamma_exposure,
            inputs.vanna_exposure,
            inputs.charm_exposure,
            inputs.event_analysis,
            inputs.news_analysis,
            inputs.intelligence_fusion,
        ]

        available = sum(1 for m in modules if m is not None)

        if available < MIN_MODULES_REQUIRED:
            return FilterResult(
                filter_category=FilterCategory.INSUFFICIENT_EVIDENCE,
                passed=False,
                reason=f"Insufficient evidence: {available} modules available (minimum {MIN_MODULES_REQUIRED}).",
            )

        return FilterResult(
            filter_category=FilterCategory.INSUFFICIENT_EVIDENCE,
            passed=True,
            reason=f"Sufficient evidence: {available} modules available.",
        )

    def _check_market_regime(self, inputs: TradeQualificationInput) -> FilterResult:
        """Reject if market regime is unknown."""

        from titan.market.intelligence.models import MarketRegime

        regime = inputs.market_regime
        if regime is None:
            return FilterResult(
                filter_category=FilterCategory.UNKNOWN_MARKET_REGIME,
                passed=True,
                reason="Market regime intelligence unavailable — skipping regime check.",
            )

        if regime.market_regime == MarketRegime.UNKNOWN:
            return FilterResult(
                filter_category=FilterCategory.UNKNOWN_MARKET_REGIME,
                passed=False,
                reason="Market regime is unknown — cannot qualify trade.",
            )

        return FilterResult(
            filter_category=FilterCategory.UNKNOWN_MARKET_REGIME,
            passed=True,
            reason=f"Market regime is {regime.market_regime.value}.",
        )
