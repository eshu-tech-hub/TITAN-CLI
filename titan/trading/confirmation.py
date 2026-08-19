from titan.core.evidence import EvidenceSignal
from titan.options.analytics.models import (
    DealerBiasLevel,
    MarketBias,
)
from titan.trading.models import (
    ConfirmationResult,
    ConfirmationSource,
    TradeDirection,
    TradeQualificationInput,
)

MIN_CONFIRMATION_SCORE = 50.0

DEFAULT_LONG_CONFIRMATION_SOURCES = 8
DEFAULT_SHORT_CONFIRMATION_SOURCES = 8
DEFAULT_OPTION_BUYING_CONFIRMATION_SOURCES = 5
DEFAULT_OPTION_SELLING_CONFIRMATION_SOURCES = 5


class _SignalMapping:
    """Maps domain-specific enums to bullish/bearish/neutral."""

    @staticmethod
    def from_market_bias(bias: MarketBias) -> str | None:
        mapping = {
            MarketBias.BULLISH: "bullish",
            MarketBias.BEARISH: "bearish",
            MarketBias.NEUTRAL: "neutral",
        }
        return mapping.get(bias)

    @staticmethod
    def from_dealer_bias(bias: DealerBiasLevel) -> str | None:
        mapping = {
            DealerBiasLevel.BULLISH: "bullish",
            DealerBiasLevel.BEARISH: "bearish",
            DealerBiasLevel.NEUTRAL: "neutral",
        }
        return mapping.get(bias)

    @staticmethod
    def from_evidence_signal(signal: EvidenceSignal) -> str | None:
        mapping = {
            EvidenceSignal.VERY_BULLISH: "bullish",
            EvidenceSignal.BULLISH: "bullish",
            EvidenceSignal.NEUTRAL: "neutral",
            EvidenceSignal.BEARISH: "bearish",
            EvidenceSignal.VERY_BEARISH: "bearish",
        }
        return mapping.get(signal)


class ConfirmationEngine:
    """Evaluates configurable agreement across intelligence modules.

    Checks each intelligence source for alignment with the specified
    trade direction and produces confirmation results.
    """

    name = "ConfirmationEngine"

    def confirm(
        self,
        inputs: TradeQualificationInput,
        direction: TradeDirection = TradeDirection.LONG,
        min_confirmations: int | None = None,
    ) -> tuple[ConfirmationResult, ...]:
        """Evaluate confirmation across all available sources.

        Args:
            inputs: Aggregated intelligence inputs.
            direction: Trade direction to confirm.
            min_confirmations: Minimum confirmations required (optional,
                defaults to direction-specific minimum).

        Returns:
            Tuple of confirmation results, one per source.
        """

        results: list[ConfirmationResult] = []

        results.append(self._confirm_market(inputs, direction))
        results.append(self._confirm_options(inputs, direction))
        results.append(self._confirm_dealer(inputs, direction))
        results.append(self._confirm_volatility(inputs, direction))
        results.append(self._confirm_news(inputs, direction))
        results.append(self._confirm_events(inputs, direction))
        results.append(self._confirm_evidence(inputs, direction))
        results.append(self._confirm_fusion(inputs, direction))

        return tuple(results)

    def confirmation_count(self, results: tuple[ConfirmationResult, ...]) -> int:
        """Count how many sources confirmed.

        Args:
            results: Confirmation results to evaluate.

        Returns:
            Number of sources that confirmed.
        """

        return sum(1 for r in results if r.confirmed)

    def weighted_confirmation_score(
        self, results: tuple[ConfirmationResult, ...]
    ) -> float:
        """Compute weighted average confirmation score.

        Args:
            results: Confirmation results to evaluate.

        Returns:
            Weighted average score (0-100).
        """

        total_weight = 0.0
        weighted_sum = 0.0
        weights = {
            ConfirmationSource.MARKET: 0.20,
            ConfirmationSource.OPTIONS: 0.15,
            ConfirmationSource.DEALER: 0.15,
            ConfirmationSource.VOLATILITY: 0.10,
            ConfirmationSource.NEWS: 0.10,
            ConfirmationSource.EVENTS: 0.10,
            ConfirmationSource.EVIDENCE: 0.10,
            ConfirmationSource.FUSION: 0.10,
        }

        for result in results:
            w = weights.get(result.source, 0.05)
            total_weight += w
            weighted_sum += result.score * w

        if total_weight == 0:
            return 0.0

        return weighted_sum / total_weight

    def _confirm_market(
        self,
        inputs: TradeQualificationInput,
        direction: TradeDirection,
    ) -> ConfirmationResult:
        regime = inputs.market_regime
        if regime is None:
            return ConfirmationResult(
                source=ConfirmationSource.MARKET,
                confirmed=False,
                score=0.0,
                confidence=0.0,
                reason="Market regime intelligence unavailable.",
            )

        decision = regime.decision_context
        if decision is None:
            return ConfirmationResult(
                source=ConfirmationSource.MARKET,
                confirmed=False,
                score=float(regime.confidence) * 50.0,
                confidence=float(regime.confidence),
                reason="Market regime decision context unavailable.",
            )

        favorable = self._direction_favorable(direction, decision)
        score = 75.0 if favorable else 25.0

        adj = 0.0
        if regime.institutional_confirmation:
            adj += 10.0
        if float(regime.confidence) >= 0.7:
            adj += 5.0

        final_score = max(0.0, min(100.0, score + adj))

        return ConfirmationResult(
            source=ConfirmationSource.MARKET,
            confirmed=final_score >= MIN_CONFIRMATION_SCORE,
            score=final_score,
            confidence=float(regime.confidence),
            reason=(
                f"Market regime {regime.market_regime.value}: "
                f"{'favourable' if favorable else 'unfavourable'} for {direction.value}."
            ),
        )

    def _confirm_options(
        self,
        inputs: TradeQualificationInput,
        direction: TradeDirection,
    ) -> ConfirmationResult:
        chain = inputs.option_chain
        if chain is None:
            return ConfirmationResult(
                source=ConfirmationSource.OPTIONS,
                confirmed=False,
                score=0.0,
                confidence=0.0,
                reason="Option chain intelligence unavailable.",
            )

        signal = _SignalMapping.from_market_bias(chain.overall_bias)
        if signal is None:
            return ConfirmationResult(
                source=ConfirmationSource.OPTIONS,
                confirmed=False,
                score=50.0,
                confidence=float(chain.confidence),
                reason=f"Option chain bias is {chain.overall_bias.value}.",
            )

        aligned = self._signal_aligns(signal, direction)
        score = 75.0 if aligned else 25.0

        # Adjust for extreme OI positioning
        if (
            chain.bullish_score > 70.0
            and direction == TradeDirection.LONG
            or chain.bearish_score > 70.0
            and direction == TradeDirection.SHORT
        ):
            score += 10.0

        final_score = max(0.0, min(100.0, score))

        return ConfirmationResult(
            source=ConfirmationSource.OPTIONS,
            confirmed=final_score >= MIN_CONFIRMATION_SCORE,
            score=final_score,
            confidence=float(chain.confidence),
            reason=(
                f"Option chain bias {chain.overall_bias.value}: "
                f"{'aligns' if aligned else 'does not align'} with {direction.value}."
            ),
        )

    def _confirm_dealer(
        self,
        inputs: TradeQualificationInput,
        direction: TradeDirection,
    ) -> ConfirmationResult:
        dealer = inputs.dealer_positioning
        if dealer is None:
            return ConfirmationResult(
                source=ConfirmationSource.DEALER,
                confirmed=False,
                score=0.0,
                confidence=0.0,
                reason="Dealer positioning intelligence unavailable.",
            )

        signal = _SignalMapping.from_dealer_bias(dealer.dealer_bias)
        if signal is None:
            return ConfirmationResult(
                source=ConfirmationSource.DEALER,
                confirmed=False,
                score=50.0,
                confidence=float(dealer.confidence),
                reason=f"Dealer bias is {dealer.dealer_bias.value}.",
            )

        aligned = self._signal_aligns(signal, direction)
        score = 80.0 if aligned else 20.0

        # Adjust for hedging pressure
        if dealer.hedging_pressure > 0.7:
            score = score - 15.0 if aligned else score + 5.0

        final_score = max(0.0, min(100.0, score))

        return ConfirmationResult(
            source=ConfirmationSource.DEALER,
            confirmed=final_score >= MIN_CONFIRMATION_SCORE,
            score=final_score,
            confidence=float(dealer.confidence),
            reason=(
                f"Dealer bias {dealer.dealer_bias.value}: "
                f"{'aligns' if aligned else 'does not align'} with {direction.value}."
            ),
        )

    def _confirm_volatility(
        self,
        inputs: TradeQualificationInput,
        direction: TradeDirection,
    ) -> ConfirmationResult:
        vol = inputs.volatility
        if vol is None:
            return ConfirmationResult(
                source=ConfirmationSource.VOLATILITY,
                confirmed=False,
                score=0.0,
                confidence=0.0,
                reason="Volatility intelligence unavailable.",
            )

        signal = _SignalMapping.from_market_bias(vol.overall_bias)
        if signal is None:
            return ConfirmationResult(
                source=ConfirmationSource.VOLATILITY,
                confirmed=False,
                score=50.0,
                confidence=float(vol.confidence),
                reason=f"Volatility bias is {vol.overall_bias.value}.",
            )

        aligned = self._signal_aligns(signal, direction)

        # For option buying/selling, check buying_bias/selling_bias
        if direction == TradeDirection.OPTION_BUYING:
            aligned = vol.buying_bias
        elif direction == TradeDirection.OPTION_SELLING:
            aligned = vol.selling_bias

        score = 70.0 if aligned else 30.0
        final_score = max(0.0, min(100.0, score))

        return ConfirmationResult(
            source=ConfirmationSource.VOLATILITY,
            confirmed=final_score >= MIN_CONFIRMATION_SCORE,
            score=final_score,
            confidence=float(vol.confidence),
            reason=(
                f"Volatility bias {vol.overall_bias.value}: "
                f"{'aligns' if aligned else 'does not align'} with {direction.value}."
            ),
        )

    def _confirm_news(
        self,
        inputs: TradeQualificationInput,
        direction: TradeDirection,
    ) -> ConfirmationResult:
        news = inputs.news_analysis
        if news is None:
            return ConfirmationResult(
                source=ConfirmationSource.NEWS,
                confirmed=False,
                score=0.0,
                confidence=0.0,
                reason="News intelligence unavailable.",
            )

        reaction = news.overall_reaction
        signal_map = {
            "likely_bullish": "bullish",
            "likely_bearish": "bearish",
            "likely_neutral": "neutral",
            "mixed": "neutral",
        }
        signal = signal_map.get(reaction.reaction.value) if reaction else None

        if signal is None:
            return ConfirmationResult(
                source=ConfirmationSource.NEWS,
                confirmed=False,
                score=50.0,
                confidence=float(reaction.confidence) if reaction else 0.0,
                reason=f"News reaction is {reaction.reaction.value if reaction else 'unknown'}.",
            )

        aligned = self._signal_aligns(signal, direction)
        score = 65.0 if aligned else 35.0

        confidence = float(reaction.confidence) if reaction else 0.0
        final_score = max(0.0, min(100.0, score))

        return ConfirmationResult(
            source=ConfirmationSource.NEWS,
            confirmed=final_score >= MIN_CONFIRMATION_SCORE,
            score=final_score,
            confidence=confidence,
            reason=(
                f"News reaction {reaction.reaction.value if reaction else 'unknown'}: "
                f"{'aligns' if aligned else 'does not align'} with {direction.value}."
            ),
        )

    def _confirm_events(
        self,
        inputs: TradeQualificationInput,
        direction: TradeDirection,
    ) -> ConfirmationResult:
        event = inputs.event_analysis
        if event is None:
            return ConfirmationResult(
                source=ConfirmationSource.EVENTS,
                confirmed=False,
                score=0.0,
                confidence=0.0,
                reason="Event intelligence unavailable.",
            )

        decision = event.decision_context
        if decision is None:
            return ConfirmationResult(
                source=ConfirmationSource.EVENTS,
                confirmed=True,
                score=60.0,
                confidence=float(event.confidence),
                reason="No event decision context — defaulting to neutral.",
            )

        if decision.avoid_new_positions:
            return ConfirmationResult(
                source=ConfirmationSource.EVENTS,
                confirmed=False,
                score=10.0,
                confidence=float(decision.confidence),
                reason="Event intelligence recommends avoiding new positions.",
            )

        score = 50.0
        if decision.allow_intraday_only:
            score = 40.0
        if decision.expect_high_volatility:
            if direction in (TradeDirection.OPTION_BUYING,):
                score += 20.0
            elif direction in (TradeDirection.OPTION_SELLING,):
                score -= 20.0

        final_score = max(0.0, min(100.0, score))

        return ConfirmationResult(
            source=ConfirmationSource.EVENTS,
            confirmed=final_score >= MIN_CONFIRMATION_SCORE,
            score=final_score,
            confidence=float(decision.confidence),
            reason=f"Event risk level {event.overall_risk.value}: {'favourable' if final_score >= MIN_CONFIRMATION_SCORE else 'cautious'} for {direction.value}.",
        )

    def _confirm_evidence(
        self,
        inputs: TradeQualificationInput,
        direction: TradeDirection,
    ) -> ConfirmationResult:
        fusion = inputs.intelligence_fusion
        if fusion is None:
            return ConfirmationResult(
                source=ConfirmationSource.EVIDENCE,
                confirmed=False,
                score=0.0,
                confidence=0.0,
                reason="Intelligence fusion unavailable — cannot evaluate aggregate evidence.",
            )

        signal = _SignalMapping.from_evidence_signal(fusion.overall_signal)
        if signal is None:
            return ConfirmationResult(
                source=ConfirmationSource.EVIDENCE,
                confirmed=False,
                score=50.0,
                confidence=float(fusion.overall_confidence),
                reason=f"Aggregate evidence signal is {fusion.overall_signal.value}.",
            )

        aligned = self._signal_aligns(signal, direction)
        score = 70.0 if aligned else 30.0

        # Adjust based on evidence count
        if fusion.evidence_count > 5 and aligned:
            score += 10.0
        elif fusion.evidence_count < 3:
            score -= 10.0

        final_score = max(0.0, min(100.0, score))

        return ConfirmationResult(
            source=ConfirmationSource.EVIDENCE,
            confirmed=final_score >= MIN_CONFIRMATION_SCORE,
            score=final_score,
            confidence=float(fusion.overall_confidence),
            reason=(
                f"Aggregate evidence {fusion.overall_signal.value}: "
                f"{'aligns' if aligned else 'does not align'} with {direction.value}."
            ),
        )

    def _confirm_fusion(
        self,
        inputs: TradeQualificationInput,
        direction: TradeDirection,
    ) -> ConfirmationResult:
        fusion = inputs.intelligence_fusion
        if fusion is None:
            return ConfirmationResult(
                source=ConfirmationSource.FUSION,
                confirmed=False,
                score=0.0,
                confidence=0.0,
                reason="Intelligence fusion unavailable.",
            )

        signal = _SignalMapping.from_evidence_signal(fusion.overall_signal)
        if signal is None:
            return ConfirmationResult(
                source=ConfirmationSource.FUSION,
                confirmed=False,
                score=50.0,
                confidence=float(fusion.overall_confidence),
                reason=f"Fusion signal is {fusion.overall_signal.value}.",
            )

        aligned = self._signal_aligns(signal, direction)
        score = float(fusion.overall_score)
        confirmed = aligned and score >= MIN_CONFIRMATION_SCORE

        return ConfirmationResult(
            source=ConfirmationSource.FUSION,
            confirmed=confirmed,
            score=score,
            confidence=float(fusion.overall_confidence),
            reason=(
                f"Fusion signal {fusion.overall_signal.value} "
                f"(score: {fusion.overall_score.value:.0f}): "
                f"{'aligns' if aligned else 'does not align'} with {direction.value}."
            ),
        )

    @staticmethod
    def _direction_favorable(
        direction: TradeDirection,
        decision: object,
    ) -> bool:
        from titan.market.intelligence.models import (
            DecisionContext as MarketDecisionContext,
        )

        if not isinstance(decision, MarketDecisionContext):
            return False

        mapping = {
            TradeDirection.LONG: decision.favorable_for_long,
            TradeDirection.SHORT: decision.favorable_for_short,
            TradeDirection.OPTION_BUYING: decision.favorable_for_option_buying,
            TradeDirection.OPTION_SELLING: decision.favorable_for_option_selling,
        }
        return mapping.get(direction, False)

    @staticmethod
    def _signal_aligns(signal: str, direction: TradeDirection) -> bool:
        long_directions = (TradeDirection.LONG, TradeDirection.OPTION_BUYING)
        short_directions = (TradeDirection.SHORT, TradeDirection.OPTION_SELLING)

        if direction in long_directions:
            return signal == "bullish"
        if direction in short_directions:
            return signal == "bearish"
        return signal == "neutral"
