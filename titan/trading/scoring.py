from titan.trading.models import (
    ConfirmationResult,
    FilterResult,
    ScoreBand,
    TradeQualificationInput,
    TradeScore,
)

EXCELLENT_THRESHOLD = 80.0
GOOD_THRESHOLD = 60.0
AVERAGE_THRESHOLD = 40.0
WEAK_THRESHOLD = 20.0


class TradeScoringEngine:
    """Produces a normalised trade opportunity score from 0 to 100.

    The score reflects overall opportunity quality based on:
      - Confirmation agreement across intelligence sources
      - Overall confidence from available modules
      - Institutional alignment
      - Deductions for warnings and risk factors
    """

    name = "TradeScoringEngine"

    def score(
        self,
        inputs: TradeQualificationInput,
        confirmations: tuple[ConfirmationResult, ...],
        filter_results: tuple[FilterResult, ...],
    ) -> TradeScore:
        """Compute the trade score.

        Args:
            inputs: Aggregated intelligence inputs.
            confirmations: Confirmation results from each source.
            filter_results: Hard filter evaluation results.

        Returns:
            Normalised trade score with quality band.
        """

        base = self._base_score(confirmations)
        confidence_adj = self._confidence_adjustment(inputs)
        alignment_adj = self._institutional_alignment_adjustment(inputs)
        warning_penalty = self._warning_penalty(inputs)

        raw = base + confidence_adj + alignment_adj - warning_penalty
        final = max(0.0, min(100.0, raw))

        return TradeScore(value=final, band=self._determine_band(final))

    @staticmethod
    def _base_score(
        confirmations: tuple[ConfirmationResult, ...],
    ) -> float:
        if not confirmations:
            return 0.0

        total = len(confirmations)
        confirmed = sum(1 for c in confirmations if c.confirmed)
        weighted = sum(c.score for c in confirmations)

        agreement_ratio = confirmed / total if total > 0 else 0.0
        avg_score = weighted / total if total > 0 else 0.0

        return (agreement_ratio * 40.0) + (avg_score * 0.6)

    @staticmethod
    def _confidence_adjustment(
        inputs: TradeQualificationInput,
    ) -> float:
        confidences: list[float] = []
        weights: list[float] = []

        module_weights = {
            "market_regime": 0.20,
            "option_chain": 0.15,
            "greeks": 0.05,
            "liquidity": 0.05,
            "volatility": 0.10,
            "dealer_positioning": 0.15,
            "gamma_exposure": 0.05,
            "vanna_exposure": 0.05,
            "charm_exposure": 0.05,
            "event_analysis": 0.05,
            "news_analysis": 0.10,
        }

        modules = {
            "market_regime": inputs.market_regime,
            "option_chain": inputs.option_chain,
            "greeks": inputs.greeks,
            "liquidity": inputs.liquidity,
            "volatility": inputs.volatility,
            "dealer_positioning": inputs.dealer_positioning,
            "gamma_exposure": inputs.gamma_exposure,
            "vanna_exposure": inputs.vanna_exposure,
            "charm_exposure": inputs.charm_exposure,
            "event_analysis": inputs.event_analysis,
            "news_analysis": inputs.news_analysis,
        }

        for name, module in modules.items():
            if module is not None and hasattr(module, "confidence"):
                c = module.confidence
                if isinstance(c, (int, float)) and c > 0:
                    confidences.append(float(c))
                    weights.append(module_weights.get(name, 0.05))

        if not confidences:
            return 0.0

        total_weight = sum(weights)
        if total_weight == 0:
            return 0.0

        avg = sum(c * w for c, w in zip(confidences, weights)) / total_weight

        return (avg - 0.5) * 20.0

    @staticmethod
    def _institutional_alignment_adjustment(
        inputs: TradeQualificationInput,
    ) -> float:
        adjustment = 0.0

        regime = inputs.market_regime
        if regime is not None and regime.institutional_confirmation:
            adjustment += 5.0

        dealer = inputs.dealer_positioning
        if dealer is not None and dealer.confidence > 0.5:
            if dealer.dealer_bias.value in ("bullish", "bearish"):
                adjustment += 5.0

        fusion = inputs.intelligence_fusion
        if fusion is not None:
            score_val = float(fusion.overall_score)
            if score_val >= 70.0:
                adjustment += 5.0
            elif score_val >= 55.0:
                adjustment += 2.0

        return adjustment

    @staticmethod
    def _warning_penalty(inputs: TradeQualificationInput) -> float:
        penalty = 0.0
        warning_count = 0

        modules_with_warnings = [
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

        for module in modules_with_warnings:
            if module is not None and hasattr(module, "warnings"):
                w = module.warnings
                if isinstance(w, (tuple, list)):
                    warning_count += len(w)

        penalty = float(warning_count) * 2.0

        return min(penalty, 30.0)

    @staticmethod
    def _determine_band(score: float) -> ScoreBand:
        if score >= EXCELLENT_THRESHOLD:
            return ScoreBand.EXCELLENT
        if score >= GOOD_THRESHOLD:
            return ScoreBand.GOOD
        if score >= AVERAGE_THRESHOLD:
            return ScoreBand.AVERAGE
        if score >= WEAK_THRESHOLD:
            return ScoreBand.WEAK
        return ScoreBand.REJECT
