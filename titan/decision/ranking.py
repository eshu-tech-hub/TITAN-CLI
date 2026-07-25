from dataclasses import dataclass

from titan.core.evidence.models import EvidenceSignal
from titan.decision.models import DecisionInput, DecisionRank
from titan.options.analytics.models import DealerBiasLevel, MarketBias
from titan.risk.models import RiskScoreBand
from titan.trading.models import ScoreBand


@dataclass(slots=True)
class DecisionRankingEngine:
    """Ranks the trade opportunity based on combined intelligence.

    Produces one of:
        - BEST: Strong alignment across all intelligence sources.
        - GOOD: Moderate alignment, acceptable risk.
        - ACCEPTABLE: Marginal opportunity, proceed with caution.
        - REJECT: Should not be traded.
    """

    name: str = "DecisionRankingEngine"

    def rank(self, decision_input: DecisionInput) -> DecisionRank:
        """Rank the trade opportunity.

        Args:
            decision_input: Aggregated decision input.

        Returns:
            Decision rank for the opportunity.
        """
        score = self._compute_rank_score(decision_input)
        if score >= 80.0:
            return DecisionRank.BEST
        if score >= 60.0:
            return DecisionRank.GOOD
        if score >= 40.0:
            return DecisionRank.ACCEPTABLE
        return DecisionRank.REJECT

    def _compute_rank_score(self, decision_input: DecisionInput) -> float:
        """Compute a normalised rank score (0-100) from all intelligence.

        Components:
            - Trade quality (40% weight): from the qualification score.
            - Risk alignment (25% weight): inverse of risk score.
            - Intelligence bias (20% weight): alignment across signals.
            - Confidence (15% weight): average of available confidences.
        """
        quality = self._score_quality(decision_input)
        risk_alignment = self._score_risk_alignment(decision_input)
        bias = self._score_bias_alignment(decision_input)
        confidence = self._score_confidence(decision_input)

        total = quality * 0.40 + risk_alignment * 0.25 + bias * 0.20 + confidence * 0.15
        return max(0.0, min(100.0, total))

    def _score_quality(self, decision_input: DecisionInput) -> float:
        """Score based on trade quality."""
        tq = decision_input.trade_qualification
        score_val = tq.trade_score.value
        band = tq.trade_score.band

        if band == ScoreBand.EXCELLENT:
            return 100.0
        if band == ScoreBand.GOOD:
            return 75.0
        if band == ScoreBand.AVERAGE:
            return 50.0
        if band == ScoreBand.WEAK:
            return 25.0
        if band == ScoreBand.REJECT:
            return 0.0
        return score_val

    def _score_risk_alignment(self, decision_input: DecisionInput) -> float:
        """Score based on risk alignment (lower risk = higher score)."""
        rc = decision_input.risk_analysis
        band = rc.risk_score.band

        if band == RiskScoreBand.VERY_LOW:
            return 100.0
        if band == RiskScoreBand.LOW:
            return 80.0
        if band == RiskScoreBand.MODERATE:
            return 60.0
        if band == RiskScoreBand.HIGH:
            return 30.0
        if band == RiskScoreBand.EXTREME:
            return 0.0
        return 50.0

    def _score_bias_alignment(self, decision_input: DecisionInput) -> float:
        """Score based on alignment across intelligence biases."""
        signals: list[float] = []

        fusion = decision_input.intelligence_fusion
        if fusion is not None:
            sig = fusion.overall_signal
            signals.append(self._signal_to_score(sig))

        option_chain = decision_input.option_chain
        if option_chain is not None:
            signals.append(self._bias_to_score(option_chain.overall_bias))

        greeks = decision_input.greeks
        if greeks is not None:
            signals.append(self._bias_to_score(greeks.overall_bias))

        dealer = decision_input.dealer_positioning
        if dealer is not None:
            dealer_score = self._dealer_bias_to_score(dealer.dealer_bias)
            signals.append(dealer_score)

        if not signals:
            return 60.0

        avg_signal = sum(signals) / len(signals)
        return avg_signal

    def _signal_to_score(self, signal: EvidenceSignal) -> float:
        mapping = {
            EvidenceSignal.VERY_BULLISH: 100.0,
            EvidenceSignal.BULLISH: 75.0,
            EvidenceSignal.NEUTRAL: 60.0,
            EvidenceSignal.BEARISH: 25.0,
            EvidenceSignal.VERY_BEARISH: 0.0,
            EvidenceSignal.UNKNOWN: 50.0,
        }
        return mapping.get(signal, 50.0)

    def _bias_to_score(self, bias: MarketBias) -> float:
        mapping = {
            MarketBias.BULLISH: 75.0,
            MarketBias.NEUTRAL: 60.0,
            MarketBias.BEARISH: 25.0,
            MarketBias.UNKNOWN: 50.0,
        }
        return mapping.get(bias, 50.0)

    def _dealer_bias_to_score(self, bias: DealerBiasLevel) -> float:
        mapping = {
            DealerBiasLevel.BULLISH: 75.0,
            DealerBiasLevel.NEUTRAL: 60.0,
            DealerBiasLevel.BEARISH: 25.0,
            DealerBiasLevel.UNKNOWN: 50.0,
        }
        return mapping.get(bias, 50.0)

    def _score_confidence(self, decision_input: DecisionInput) -> float:
        """Score based on available confidence metrics."""
        confidences: list[float] = []

        tq = decision_input.trade_qualification
        confidences.append(tq.confidence * 100.0)

        rc = decision_input.risk_analysis
        confidences.append(rc.decision_context.confidence * 100.0)

        fusion = decision_input.intelligence_fusion
        if fusion is not None:
            confidences.append(fusion.overall_confidence.value * 100.0)

        if not confidences:
            return 0.0

        return sum(confidences) / len(confidences)
