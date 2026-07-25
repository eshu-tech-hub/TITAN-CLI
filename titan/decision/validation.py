from dataclasses import dataclass

from titan.decision.models import DecisionInput
from titan.risk.models import RiskScoreBand
from titan.trading.models import TradeStatus


@dataclass(slots=True)
class DecisionValidationEngine:
    """Validates decision inputs and enforces hard rejection rules.

    The validation engine is the first gate in the decision pipeline.
    If any rejection condition is met, the opportunity is immediately
    flagged with a human-readable reason.

    Rejection conditions:
        - Risk engine says avoid_trade.
        - Trade qualification status is REJECTED.
        - Conflicting intelligence detected across sources.
        - Insufficient confidence below institutional threshold.
        - Extreme event risk present.
    """

    name: str = "DecisionValidationEngine"

    def validate(self, decision_input: DecisionInput) -> list[str]:
        """Run all validation checks against the decision input.

        Args:
            decision_input: Aggregated decision input.

        Returns:
            List of rejection reasons. Empty list means all checks passed.
        """
        reasons: list[str] = []
        reasons.extend(self._check_risk_rejection(decision_input))
        reasons.extend(self._check_qualification(decision_input))
        reasons.extend(self._check_conflicting_intelligence(decision_input))
        reasons.extend(self._check_confidence(decision_input))
        reasons.extend(self._check_extreme_event(decision_input))
        return reasons

    def _check_risk_rejection(self, decision_input: DecisionInput) -> list[str]:
        """Check if the risk engine recommends avoiding the trade."""
        reasons: list[str] = []
        rc = decision_input.risk_analysis
        if rc.decision_context.avoid_trade:
            band = rc.risk_score.band.value
            reasons.append(
                f"Risk engine rejects trade: risk score {rc.risk_score.value:.1f}/100 "
                f"({band}), avoid_trade=True."
            )
        return reasons

    def _check_qualification(self, decision_input: DecisionInput) -> list[str]:
        """Check if the trade qualification is rejected."""
        reasons: list[str] = []
        tq = decision_input.trade_qualification
        if tq.status == TradeStatus.REJECTED:
            reasons.append(
                f"Trade qualification rejected: status={tq.status.value}, "
                f"score={tq.trade_score.value:.1f}, "
                f"failed_filters={len(tq.failed_filters)}."
            )
        return reasons

    def _check_conflicting_intelligence(
        self, decision_input: DecisionInput
    ) -> list[str]:
        """Detect conflicting intelligence signals."""
        reasons: list[str] = []
        fusion = decision_input.intelligence_fusion
        if fusion is not None and len(fusion.conflicting_evidence) > 0:
            reasons.append(
                f"Conflicting intelligence: {len(fusion.conflicting_evidence)} "
                f"conflict(s) detected."
            )
        return reasons

    def _check_confidence(self, decision_input: DecisionInput) -> list[str]:
        """Check if confidence meets the minimum threshold."""
        reasons: list[str] = []
        tq = decision_input.trade_qualification
        min_conf = 0.3
        if tq.confidence < min_conf:
            reasons.append(
                f"Insufficient confidence: {tq.confidence:.2f} "
                f"(minimum {min_conf})."
            )
        return reasons

    def _check_extreme_event(self, decision_input: DecisionInput) -> list[str]:
        """Check if extreme event risk is present."""
        reasons: list[str] = []
        rc = decision_input.risk_analysis
        if rc.risk_score.band == RiskScoreBand.EXTREME:
            event = decision_input.event_analysis
            if event is not None:
                risk_val = event.overall_risk.value
                if risk_val == "extreme":
                    reasons.append(
                        "Extreme event risk: trade rejected by event intelligence."
                    )
        return reasons
