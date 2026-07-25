from dataclasses import dataclass

from titan.core.evidence import (
    Confidence,
    Evidence,
    EvidenceCategory,
    EvidenceSignal,
    Score,
)
from titan.decision.models import (
    DecisionAction,
    DecisionExplanation,
    DecisionInput,
    DecisionRank,
    HoldingStyle,
    InstrumentType,
    TradeDecision,
)
from titan.risk.models import RiskScoreBand
from titan.trading.models import TradeDirection, TradeStatus


@dataclass(slots=True)
class DecisionSelectionEngine:
    """Produces the final TradeDecision from validated and ranked inputs.

    Determines:
        - Final action (BUY, SELL, NO_TRADE, WATCHLIST, WAIT).
        - Instrument type selection.
        - Trade direction mapping.
        - Holding style from volatility context.
        - Entry strategy description.
        - Stop loss and target references.
        - Confidence and probability estimates.
        - Institutional grade flag.
    """

    name: str = "DecisionSelectionEngine"

    def select(
        self,
        decision_input: DecisionInput,
        rank: DecisionRank,
        validation_reasons: list[str],
    ) -> TradeDecision:
        """Produce the final trade decision.

        Args:
            decision_input: Aggregated decision input.
            rank: Opportunity rank from the ranking engine.
            validation_reasons: Rejection reasons from validation (empty if passed).

        Returns:
            Complete trade decision.
        """
        action = self._determine_action(decision_input, rank, validation_reasons)
        direction = self._determine_direction(decision_input, action)
        instrument = self._determine_instrument(decision_input, action)
        holding = self._determine_holding_style(decision_input)
        entry_strategy = self._build_entry_strategy(decision_input, action)
        stop_ref = self._get_stop_reference(decision_input)
        target_ref = self._get_target_reference(decision_input)
        confidence = self._compute_confidence(decision_input, validation_reasons)
        probability = self._compute_probability(decision_input, confidence)
        trade_score = self._compute_trade_score(decision_input)
        institutional = self._check_institutional_grade(decision_input)
        warnings = self._collect_warnings(decision_input, validation_reasons)
        evidence = self._generate_evidence(decision_input, action, rank, confidence)
        explanation = self._generate_explanation(
            decision_input,
            action,
            rank,
            validation_reasons,
        )

        return TradeDecision(
            decision=action,
            trade_direction=direction,
            instrument_type=instrument,
            symbol=decision_input.symbol,
            entry_strategy=entry_strategy,
            stop_loss_reference=stop_ref,
            target_reference=target_ref,
            holding_style=holding,
            rank=rank,
            confidence=round(confidence, 4),
            probability=round(probability, 4),
            trade_score=round(trade_score, 2),
            institutional_grade=institutional,
            evidence=evidence,
            explanation=explanation,
            warnings=tuple(warnings),
            metadata={
                "validation_rejections": len(validation_reasons),
                "rank": rank.value,
                "action": action.value,
            },
        )

    def _determine_action(
        self,
        decision_input: DecisionInput,
        rank: DecisionRank,
        validation_reasons: list[str],
    ) -> DecisionAction:
        """Determine the final trading action."""
        if len(validation_reasons) > 0:
            rc = decision_input.risk_analysis
            if rc.decision_context.avoid_trade:
                return DecisionAction.NO_TRADE
            tq = decision_input.trade_qualification
            if tq.status == TradeStatus.WATCHLIST:
                return DecisionAction.WATCHLIST
            if tq.status == TradeStatus.WAIT:
                return DecisionAction.WAIT
            return DecisionAction.NO_TRADE

        if rank == DecisionRank.REJECT:
            return DecisionAction.NO_TRADE

        if rank == DecisionRank.ACCEPTABLE:
            rc = decision_input.risk_analysis
            if rc.risk_score.band in (RiskScoreBand.HIGH,):
                return DecisionAction.WATCHLIST
            if rc.risk_score.band == RiskScoreBand.EXTREME:
                return DecisionAction.NO_TRADE

        rc = decision_input.risk_analysis
        tq = decision_input.trade_qualification

        if tq.status == TradeStatus.WATCHLIST:
            return DecisionAction.WATCHLIST
        if tq.status == TradeStatus.WAIT:
            return DecisionAction.WAIT

        if tq.long_qualification and not tq.short_qualification:
            return DecisionAction.BUY
        if tq.short_qualification and not tq.long_qualification:
            return DecisionAction.SELL

        if tq.long_qualification and tq.short_qualification:
            vol = decision_input.volatility
            if vol is not None:
                bias_name = vol.overall_bias.value if vol.overall_bias else ""
                if bias_name == "bullish":
                    return DecisionAction.BUY
                if bias_name == "bearish":
                    return DecisionAction.SELL
            return DecisionAction.BUY

        if tq.status == TradeStatus.QUALIFIED:
            return DecisionAction.BUY

        return DecisionAction.NO_TRADE

    def _determine_direction(
        self,
        decision_input: DecisionInput,
        action: DecisionAction,
    ) -> TradeDirection:
        if action == DecisionAction.SELL:
            return TradeDirection.SHORT
        if action == DecisionAction.BUY:
            return TradeDirection.LONG
        tq = decision_input.trade_qualification
        if tq.option_buying_qualification:
            return TradeDirection.OPTION_BUYING
        if tq.option_selling_qualification:
            return TradeDirection.OPTION_SELLING
        if tq.long_qualification:
            return TradeDirection.LONG
        return TradeDirection.LONG

    def _determine_instrument(
        self,
        decision_input: DecisionInput,
        action: DecisionAction,
    ) -> InstrumentType:
        tq = decision_input.trade_qualification
        has_options = (
            decision_input.option_chain is not None
            or decision_input.greeks is not None
            or decision_input.gamma_exposure is not None
        )
        if has_options and tq.option_buying_qualification:
            vol = decision_input.volatility
            if vol is not None:
                regime = vol.volatility_regime.value if vol.volatility_regime else ""
                bias_name = vol.overall_bias.value if vol.overall_bias else ""
                if regime == "compression" and bias_name == "bullish":
                    return InstrumentType.CALL_OPTION
                if regime == "compression" and bias_name == "bearish":
                    return InstrumentType.PUT_OPTION
            gamma = decision_input.gamma_exposure
            if gamma is not None:
                regime_name = gamma.gamma_regime.value if gamma.gamma_regime else ""
                if regime_name in ("positive",) and bias_name == "bullish":
                    return InstrumentType.CALL_OPTION
                if regime_name in ("negative",) and bias_name == "bearish":
                    return InstrumentType.PUT_OPTION
            if action == DecisionAction.BUY:
                return InstrumentType.CALL_OPTION
            if action == DecisionAction.SELL:
                return InstrumentType.PUT_OPTION
        return InstrumentType.UNDERLYING

    def _determine_holding_style(
        self,
        decision_input: DecisionInput,
    ) -> HoldingStyle:
        vol = decision_input.volatility
        if vol is not None:
            regime = vol.volatility_regime.value if vol.volatility_regime else ""
            if regime in ("expansion", "transition"):
                return HoldingStyle.DAY_TRADE
            if regime == "compression":
                return HoldingStyle.SWING
        event = decision_input.event_analysis
        if event is not None:
            risk_val = event.overall_risk.value if event.overall_risk else ""
            if risk_val in ("high", "extreme"):
                return HoldingStyle.DAY_TRADE
        tq = decision_input.trade_qualification
        if tq.confidence >= 0.8:
            return HoldingStyle.SWING
        return HoldingStyle.SWING

    def _build_entry_strategy(
        self,
        decision_input: DecisionInput,
        action: DecisionAction,
    ) -> str:
        parts: list[str] = []
        if action == DecisionAction.BUY:
            parts.append("Buy on confirmation")
        elif action == DecisionAction.SELL:
            parts.append("Sell on confirmation")
        else:
            parts.append("No entry")

        rc = decision_input.risk_analysis
        ctx = rc.decision_context
        if ctx.reduce_size:
            parts.append("reduced size")
        elif ctx.increase_size:
            parts.append("increased size")
        else:
            parts.append("standard size")

        vol = decision_input.volatility
        if vol is not None:
            regime = vol.volatility_regime.value if vol.volatility_regime else ""
            parts.append(f"volatility regime: {regime}")

        stop = rc.stop_loss
        if stop.recommended_stop > 0.0:
            parts.append(f"stop at {stop.recommended_stop:.2f}")

        return " | ".join(parts)

    def _get_stop_reference(self, decision_input: DecisionInput) -> float:
        rc = decision_input.risk_analysis
        return rc.stop_loss.recommended_stop

    def _get_target_reference(self, decision_input: DecisionInput) -> float:
        rc = decision_input.risk_analysis
        return rc.targets.target_1

    def _compute_confidence(
        self,
        decision_input: DecisionInput,
        validation_reasons: list[str],
    ) -> float:
        if len(validation_reasons) > 0:
            return 0.05
        tq = decision_input.trade_qualification
        rc = decision_input.risk_analysis
        base = (tq.confidence + rc.decision_context.confidence) / 2.0
        return max(0.0, min(1.0, base))

    def _compute_probability(
        self,
        decision_input: DecisionInput,
        confidence: float,
    ) -> float:
        tq = decision_input.trade_qualification
        score_val = tq.trade_score.value
        prob_from_score = score_val / 100.0
        return confidence * 0.6 + prob_from_score * 0.4

    def _compute_trade_score(self, decision_input: DecisionInput) -> float:
        tq = decision_input.trade_qualification
        rc = decision_input.risk_analysis
        quality_score = tq.trade_score.value
        risk_adj = 100.0 - rc.risk_score.value
        return quality_score * 0.5 + risk_adj * 0.5

    def _check_institutional_grade(self, decision_input: DecisionInput) -> bool:
        tq = decision_input.trade_qualification
        checks = [
            tq.institutional_alignment,
            tq.confidence >= 0.6,
            tq.trade_score.value >= 70.0,
        ]
        return all(checks)

    def _collect_warnings(
        self,
        decision_input: DecisionInput,
        validation_reasons: list[str],
    ) -> list[str]:
        warnings: list[str] = []
        warnings.extend(validation_reasons)
        rc = decision_input.risk_analysis
        warnings.extend(list(rc.warnings))
        tq = decision_input.trade_qualification
        warnings.extend(list(tq.warnings))
        return warnings

    def _generate_evidence(
        self,
        decision_input: DecisionInput,
        action: DecisionAction,
        rank: DecisionRank,
        confidence: float,
    ) -> Evidence:
        action_signal_map = {
            DecisionAction.BUY: EvidenceSignal.BULLISH,
            DecisionAction.SELL: EvidenceSignal.BEARISH,
            DecisionAction.NO_TRADE: EvidenceSignal.NEUTRAL,
            DecisionAction.WATCHLIST: EvidenceSignal.NEUTRAL,
            DecisionAction.WAIT: EvidenceSignal.NEUTRAL,
        }
        signal = action_signal_map.get(action, EvidenceSignal.NEUTRAL)

        score_val = decision_input.trade_qualification.trade_score.value

        reasons = [
            f"Decision: {action.value}",
            f"Rank: {rank.value}",
        ]
        if action in (DecisionAction.BUY, DecisionAction.SELL):
            reason = f"Trade score: {decision_input.trade_qualification.trade_score.value:.1f}"
            reasons.append(reason)
            rc = decision_input.risk_analysis
            reasons.append(
                f"Risk score: {rc.risk_score.value:.1f}/100 ({rc.risk_score.band.value})"
            )

        return Evidence(
            source="DecisionEngine",
            category=EvidenceCategory.TRADE_QUALIFICATION,
            signal=signal,
            score=Score(score_val),
            confidence=Confidence(confidence),
            weight=1.0,
            reasons=tuple(reasons),
        )

    def _generate_explanation(
        self,
        decision_input: DecisionInput,
        action: DecisionAction,
        rank: DecisionRank,
        validation_reasons: list[str],
    ) -> DecisionExplanation:
        tq = decision_input.trade_qualification
        rc = decision_input.risk_analysis

        summary = (
            f"Decision: {action.value.upper()} | "
            f"Rank: {rank.value} | "
            f"Trade Score: {tq.trade_score.value:.1f}/100 | "
            f"Risk Score: {rc.risk_score.value:.1f}/100 ({rc.risk_score.band.value}) | "
            f"Confidence: {tq.confidence:.1%}"
        )

        intel_parts: list[str] = []
        if decision_input.market_regime is not None:
            regime_name = (
                decision_input.market_regime.market_regime.value
                if decision_input.market_regime.market_regime
                else "unknown"
            )
            intel_parts.append(f"Market regime: {regime_name}")
        if decision_input.volatility is not None:
            vol_regime = (
                decision_input.volatility.volatility_regime.value
                if decision_input.volatility.volatility_regime
                else "unknown"
            )
            intel_parts.append(f"Volatility: {vol_regime}")
        if decision_input.intelligence_fusion is not None:
            sig_name = (
                decision_input.intelligence_fusion.overall_signal.value
                if decision_input.intelligence_fusion.overall_signal
                else "unknown"
            )
            intel_parts.append(f"Fusion signal: {sig_name}")

        supporting = (
            "; ".join(intel_parts)
            if intel_parts
            else "No additional intelligence available."
        )

        risk_summary = (
            f"Risk Score: {rc.risk_score.value:.1f}/100 ({rc.risk_score.band.value}). "
        )
        if rc.decision_context.avoid_trade:
            risk_summary += "Trade avoidance recommended. "
        if rc.decision_context.hedging_required:
            risk_summary += "Hedging required. "

        if action in (DecisionAction.BUY, DecisionAction.SELL):
            why = (
                f"Qualification passed with score {tq.trade_score.value:.1f}/100 "
                f"({tq.trade_score.band.value}) and confidence {tq.confidence:.1%}. "
            )
            if rc.risk_score.band in (RiskScoreBand.VERY_LOW, RiskScoreBand.LOW):
                why += "Risk level is favourable for execution. "
            else:
                why += "Risk level is within acceptable parameters. "
        else:
            why = "Not executing based on validation and ranking assessment."

        alternative_text = "No alternatives evaluated (single-symbol pipeline)."

        execution_parts: list[str] = []
        if action in (DecisionAction.BUY, DecisionAction.SELL):
            execution_parts.append(
                f"Entry: {self._build_entry_strategy(decision_input, action)}"
            )
            rc = decision_input.risk_analysis
            if rc.stop_loss.recommended_stop > 0.0:
                execution_parts.append(
                    f"Stop Loss: {rc.stop_loss.recommended_stop:.2f}"
                )
            execution_parts.append(
                f"Target 1: {rc.targets.target_1:.2f}, "
                f"Target 2: {rc.targets.target_2:.2f}, "
                f"Target 3: {rc.targets.target_3:.2f}"
            )
        execution_guidance = (
            " | ".join(execution_parts) if execution_parts else "No execution guidance."
        )

        return DecisionExplanation(
            decision_summary=summary,
            supporting_intelligence=supporting,
            risk_summary=risk_summary,
            why_this_trade=why,
            why_alternatives_rejected=alternative_text,
            execution_guidance=execution_guidance,
        )
