from dataclasses import dataclass, field
from datetime import UTC, datetime

from titan.decision.exceptions import DecisionEngineError, DecisionInputError
from titan.decision.models import DecisionInput, TradeDecision
from titan.decision.ranking import DecisionRankingEngine
from titan.decision.selection import DecisionSelectionEngine
from titan.decision.validation import DecisionValidationEngine


@dataclass(slots=True)
class DecisionEngine:
    """Central Decision Engine for TITAN OS.

    This engine is the final decision-making layer in the TITAN pipeline.
    It consumes completed intelligence, qualification, and risk outputs to
    produce a complete institutional trade plan.

    Responsibilities:
        - Orchestrate validation, ranking, and selection sub-engines.
        - Determine final action (BUY, SELL, NO_TRADE, WATCHLIST, WAIT).
        - Produce a complete TradeDecision with evidence and explanation.

    This engine does NOT:
        - Perform market analysis or indicator calculations.
        - Determine CE/PE, strike selection, or order execution.
        - Call broker APIs or execute trades.

    Internally orchestrates:
        - DecisionValidationEngine
        - DecisionRankingEngine
        - DecisionSelectionEngine
    """

    _validator: DecisionValidationEngine = field(
        default_factory=DecisionValidationEngine
    )
    _ranker: DecisionRankingEngine = field(default_factory=DecisionRankingEngine)
    _selector: DecisionSelectionEngine = field(default_factory=DecisionSelectionEngine)

    def decide(
        self,
        decision_input: DecisionInput,
    ) -> TradeDecision:
        """Execute complete decision pipeline.

        Args:
            decision_input: Aggregated decision input consuming all
                intelligence, qualification, and risk outputs.

        Returns:
            Complete institutional trade decision.

        Raises:
            DecisionInputError: If decision input is invalid.
            DecisionEngineError: If any sub-engine fails.
        """

        self._validate_input(decision_input)

        try:
            validation_reasons = self._validator.validate(decision_input)
            rank = self._ranker.rank(decision_input)
            decision = self._selector.select(
                decision_input=decision_input,
                rank=rank,
                validation_reasons=validation_reasons,
            )

            return TradeDecision(
                decision=decision.decision,
                trade_direction=decision.trade_direction,
                instrument_type=decision.instrument_type,
                symbol=decision.symbol,
                expiry=decision.expiry,
                strike=decision.strike,
                entry_strategy=decision.entry_strategy,
                stop_loss_reference=decision.stop_loss_reference,
                target_reference=decision.target_reference,
                holding_style=decision.holding_style,
                rank=rank,
                confidence=decision.confidence,
                probability=decision.probability,
                trade_score=decision.trade_score,
                institutional_grade=decision.institutional_grade,
                evidence=decision.evidence,
                explanation=decision.explanation,
                warnings=decision.warnings,
                metadata={
                    **decision.metadata,
                    "sub_engines": [
                        self._validator.name,
                        self._ranker.name,
                        self._selector.name,
                    ],
                },
                timestamp=datetime.now(UTC),
            )

        except DecisionInputError:
            raise
        except Exception as exc:
            raise DecisionEngineError(f"Decision pipeline failed: {exc}") from exc

    def _validate_input(self, decision_input: DecisionInput) -> None:
        if not isinstance(decision_input, DecisionInput):
            raise DecisionInputError("Input must be a DecisionInput instance.")
        if decision_input.trade_qualification is None:
            raise DecisionInputError("TradeQualification is required.")
        if decision_input.risk_analysis is None:
            raise DecisionInputError("RiskAnalysis is required.")
