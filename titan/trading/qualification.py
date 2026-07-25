from datetime import datetime, timezone
from typing import Any, Mapping

from titan.core.evidence import (
    Confidence,
    Evidence,
    EvidenceCategory,
    EvidenceSignal,
    Score,
)

from titan.trading.confirmation import ConfirmationEngine
from titan.trading.exceptions import (
    TradeQualificationEngineError,
    TradeQualificationInputError,
)
from titan.trading.filters import TradeFilterEngine
from titan.trading.models import (
    ConfirmationResult,
    DirectionQualification,
    FilterResult,
    ScoreBand,
    TradeDirection,
    TradeQualification,
    TradeQualificationExplanation,
    TradeQualificationInput,
    TradeScore,
    TradeStatus,
)
from titan.trading.scoring import TradeScoringEngine

MIN_CONFIRMATIONS_FOR_QUALIFIED = 4
MIN_CONFIRMATIONS_FOR_WATCHLIST = 2

QUALIFIED_MIN_SCORE = 60.0
WATCHLIST_MIN_SCORE = 20.0


class TradeQualificationEngine:
    """Orchestrates trade qualification by consuming completed intelligence.

    Internally delegates to:
      - TradeFilterEngine: Evaluates hard reject filters.
      - ConfirmationEngine: Checks agreement across intelligence sources.
      - TradeScoringEngine: Produces normalised 0-100 score.

    This engine does NOT calculate indicators, Greeks, or raw candles.
    It operates exclusively on completed intelligence module outputs.
    """

    name = "TradeQualificationEngine"

    def __init__(
        self,
        filter_engine: TradeFilterEngine | None = None,
        confirmation_engine: ConfirmationEngine | None = None,
        scoring_engine: TradeScoringEngine | None = None,
    ) -> None:
        self._filter_engine = filter_engine or TradeFilterEngine()
        self._confirmation_engine = confirmation_engine or ConfirmationEngine()
        self._scoring_engine = scoring_engine or TradeScoringEngine()

    def qualify(
        self,
        inputs: TradeQualificationInput,
        min_confirmations: int | None = None,
    ) -> TradeQualification:
        """Execute the full trade qualification pipeline.

        Args:
            inputs: Aggregated intelligence inputs from all modules.
            min_confirmations: Optional override for minimum confirmations
                required for qualification.

        Returns:
            Complete trade qualification result.

        Raises:
            TradeQualificationInputError: If inputs are invalid.
            TradeQualificationEngineError: If processing fails unexpectedly.
        """

        if not isinstance(inputs, TradeQualificationInput):
            raise TradeQualificationInputError(
                "Input must be a TradeQualificationInput instance."
            )

        try:
            return self._process(inputs, min_confirmations)
        except TradeQualificationError:
            raise
        except Exception as exc:
            raise TradeQualificationEngineError(
                f"Unexpected error during trade qualification: {exc}"
            ) from exc

    def _process(
        self,
        inputs: TradeQualificationInput,
        min_confirmations: int | None,
    ) -> TradeQualification:
        filter_results = self._filter_engine.evaluate(inputs)
        has_filter_failures = self._filter_engine.has_failures(filter_results)

        if has_filter_failures:
            return self._build_rejected(inputs, filter_results)

        confirmations = self._confirmation_engine.confirm(inputs)
        trade_score = self._scoring_engine.score(inputs, confirmations, filter_results)

        direction_qualifications = self._evaluate_directions(inputs, confirmations)

        status = self._determine_status(
            confirmations,
            trade_score,
            filter_results,
            min_confirmations,
        )

        passed = self._filter_engine.passed_filters(filter_results)
        failed = self._filter_engine.failed_filters(filter_results)

        inst_alignment = self._check_institutional_alignment(inputs, confirmations)

        evidence = self._to_evidence(status, trade_score, confirmations, inst_alignment)
        explanation = self._to_explanation(
            status, confirmations, filter_results, inst_alignment
        )

        return TradeQualification(
            status=status,
            trade_score=trade_score,
            confidence=self._overall_confidence(inputs),
            decision_context=self._build_decision_context(
                status, confirmations, trade_score
            ),
            passed_filters=passed,
            failed_filters=failed,
            confirmations=confirmations,
            long_qualification=direction_qualifications[TradeDirection.LONG].qualified,
            short_qualification=direction_qualifications[
                TradeDirection.SHORT
            ].qualified,
            option_buying_qualification=direction_qualifications[
                TradeDirection.OPTION_BUYING
            ].qualified,
            option_selling_qualification=direction_qualifications[
                TradeDirection.OPTION_SELLING
            ].qualified,
            institutional_alignment=inst_alignment,
            evidence=evidence,
            explanation=explanation,
            warnings=self._collect_warnings(inputs),
            metadata=self._build_metadata(inputs),
            timestamp=datetime.now(timezone.utc),
        )

    def _evaluate_directions(
        self,
        inputs: TradeQualificationInput,
        confirmations: tuple[ConfirmationResult, ...],
    ) -> dict[TradeDirection, DirectionQualification]:
        directions: dict[TradeDirection, DirectionQualification] = {}

        for direction in TradeDirection:
            dir_confirmations = self._confirmation_engine.confirm(
                inputs, direction=direction
            )
            confirmed_count = self._confirmation_engine.confirmation_count(
                dir_confirmations
            )
            score = self._confirmation_engine.weighted_confirmation_score(
                dir_confirmations
            )
            qualified = confirmed_count >= MIN_CONFIRMATIONS_FOR_QUALIFIED

            reasons = tuple(r.reason for r in dir_confirmations if r.confirmed)

            directions[direction] = DirectionQualification(
                direction=direction,
                qualified=qualified,
                confirmations=confirmed_count,
                total_possible=len(dir_confirmations),
                score=score,
                reasons=reasons,
            )

        return directions

    def _determine_status(
        self,
        confirmations: tuple[ConfirmationResult, ...],
        trade_score: TradeScore,
        filter_results: tuple[FilterResult, ...],
        min_confirmations: int | None,
    ) -> TradeStatus:
        confirmed_count = self._confirmation_engine.confirmation_count(confirmations)
        required = min_confirmations or MIN_CONFIRMATIONS_FOR_QUALIFIED

        if trade_score.value >= QUALIFIED_MIN_SCORE and confirmed_count >= required:
            return TradeStatus.QUALIFIED

        if trade_score.value >= WATCHLIST_MIN_SCORE:
            return TradeStatus.WATCHLIST

        return TradeStatus.WAIT

    def _check_institutional_alignment(
        self,
        inputs: TradeQualificationInput,
        confirmations: tuple[ConfirmationResult, ...],
    ) -> bool:
        regime = inputs.market_regime
        if regime is not None and regime.institutional_confirmation:
            return True

        dealer = inputs.dealer_positioning
        if dealer is not None and dealer.confidence > 0.5:
            if dealer.dealer_bias.value in ("bullish", "bearish"):
                return True

        confirmed = self._confirmation_engine.confirmation_count(confirmations)
        return confirmed >= MIN_CONFIRMATIONS_FOR_QUALIFIED

    def _overall_confidence(self, inputs: TradeQualificationInput) -> float:
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
            return 0.0

        return sum(confidences) / len(confidences)

    def _build_decision_context(
        self,
        status: TradeStatus,
        confirmations: tuple[ConfirmationResult, ...],
        trade_score: TradeScore,
    ) -> str:
        confirmed = self._confirmation_engine.confirmation_count(confirmations)
        total = len(confirmations)

        return (
            f"Status: {status.value}. "
            f"Score: {trade_score.value:.0f}/{trade_score.band.value}. "
            f"Confirmations: {confirmed}/{total}."
        )

    def _build_rejected(
        self,
        inputs: TradeQualificationInput,
        filter_results: tuple[FilterResult, ...],
    ) -> TradeQualification:
        failed = self._filter_engine.failed_filters(filter_results)
        passed = self._filter_engine.passed_filters(filter_results)

        return TradeQualification(
            status=TradeStatus.REJECTED,
            trade_score=TradeScore(value=0.0, band=ScoreBand.REJECT),
            confidence=self._overall_confidence(inputs),
            decision_context=f"Rejected by hard filters: {'; '.join(failed)}",
            passed_filters=passed,
            failed_filters=failed,
            long_qualification=False,
            short_qualification=False,
            option_buying_qualification=False,
            option_selling_qualification=False,
            institutional_alignment=False,
            evidence=None,
            warnings=self._collect_warnings(inputs),
            metadata=self._build_metadata(inputs),
            timestamp=datetime.now(timezone.utc),
        )

    def _to_evidence(
        self,
        status: TradeStatus,
        trade_score: TradeScore,
        confirmations: tuple[ConfirmationResult, ...],
        institutional_alignment: bool,
    ) -> Evidence:
        confirmed = self._confirmation_engine.confirmation_count(confirmations)
        total = len(confirmations)
        weighted = self._confirmation_engine.weighted_confirmation_score(confirmations)

        signal = self._derive_signal(status, trade_score)
        reasons = [
            f"Trade qualification: {status.value}.",
            f"Score: {trade_score.value:.0f} ({trade_score.band.value}).",
            f"Confirmations: {confirmed}/{total}.",
            f"Confirmation score: {weighted:.1f}.",
        ]
        if institutional_alignment:
            reasons.append("Institutional alignment detected.")

        return Evidence(
            source=self.name,
            category=EvidenceCategory.TRADE_QUALIFICATION,
            signal=signal,
            score=Score(trade_score.value),
            confidence=Confidence(min(1.0, confirmed / total) if total > 0 else 0.0),
            weight=1.0,
            reasons=tuple(reasons),
            metadata={
                "status": status.value,
                "score": trade_score.value,
                "band": trade_score.band.value,
                "confirmations": confirmed,
                "total_sources": total,
                "institutional_alignment": institutional_alignment,
            },
        )

    def _derive_signal(
        self, status: TradeStatus, trade_score: TradeScore
    ) -> EvidenceSignal:
        if status == TradeStatus.REJECTED:
            return EvidenceSignal.UNKNOWN

        if trade_score.value >= 80.0:
            return EvidenceSignal.VERY_BULLISH
        if trade_score.value >= 60.0:
            return EvidenceSignal.BULLISH
        if trade_score.value >= 40.0:
            return EvidenceSignal.NEUTRAL
        if trade_score.value >= 20.0:
            return EvidenceSignal.BEARISH

        return EvidenceSignal.VERY_BEARISH

    def _to_explanation(
        self,
        status: TradeStatus,
        confirmations: tuple[ConfirmationResult, ...],
        filter_results: tuple[FilterResult, ...],
        institutional_alignment: bool,
    ) -> TradeQualificationExplanation:
        confirmed = self._confirmation_engine.confirmation_count(confirmations)
        total = len(confirmations)
        failed = self._filter_engine.failed_filters(filter_results)

        return TradeQualificationExplanation(
            overall_qualification=self._overall_section(status, confirmed, total),
            confirmations=self._confirmations_section(confirmations),
            rejections=self._rejections_section(failed),
            risk_factors=self._risk_section(confirmations),
            institutional_alignment=self._alignment_section(institutional_alignment),
            final_assessment=self._final_section(status),
        )

    @staticmethod
    def _overall_section(status: TradeStatus, confirmed: int, total: int) -> str:
        return (
            f"Trade Qualification: {status.value}. "
            f"Confirmations: {confirmed}/{total}."
        )

    @staticmethod
    def _confirmations_section(
        confirmations: tuple[ConfirmationResult, ...],
    ) -> str:
        parts = ["Confirmations:"]
        for c in confirmations:
            status_str = "confirmed" if c.confirmed else "not confirmed"
            parts.append(
                f"  {c.source.value}: {status_str} (score: {c.score:.0f}, "
                f"confidence: {c.confidence:.2f})"
            )
        return "\n".join(parts)

    @staticmethod
    def _rejections_section(failed: tuple[str, ...]) -> str:
        if not failed:
            return "Rejections: None."
        parts = ["Rejections:"]
        for f in failed:
            parts.append(f"  - {f}")
        return "\n".join(parts)

    @staticmethod
    def _risk_section(
        confirmations: tuple[ConfirmationResult, ...],
    ) -> str:
        low_conf = [c for c in confirmations if c.confidence < 0.3 and c.confidence > 0]
        if not low_conf:
            return "Risk Factors: No significant risk factors detected."

        parts = ["Risk Factors:"]
        for c in low_conf:
            parts.append(
                f"  - Low confidence from {c.source.value}: {c.confidence:.2f}"
            )
        return "\n".join(parts)

    @staticmethod
    def _alignment_section(aligned: bool) -> str:
        if aligned:
            return (
                "Institutional Alignment: Signals from market, dealer, "
                "and fusion engines are aligned."
            )
        return "Institutional Alignment: Limited institutional alignment " "detected."

    @staticmethod
    def _final_section(status: TradeStatus) -> str:
        messages = {
            TradeStatus.QUALIFIED: (
                "Final Assessment: Trade is qualified for consideration. "
                "Proceed with standard due diligence."
            ),
            TradeStatus.REJECTED: (
                "Final Assessment: Trade is rejected. Address hard filter "
                "failures before re-evaluation."
            ),
            TradeStatus.WATCHLIST: (
                "Final Assessment: Trade placed on watchlist. "
                "Monitor for improved conditions."
            ),
            TradeStatus.WAIT: (
                "Final Assessment: Insufficient confirmation. "
                "Wait for more evidence before considering."
            ),
        }
        return messages.get(
            status,
            "Final Assessment: Unable to determine trade qualification.",
        )

    @staticmethod
    def _collect_warnings(inputs: TradeQualificationInput) -> tuple[str, ...]:
        warnings: list[str] = []
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
            if module is not None and hasattr(module, "warnings"):
                w = module.warnings
                if isinstance(w, (tuple, list)):
                    for warning in w:
                        if warning not in warnings:
                            warnings.append(str(warning))

        return tuple(warnings)

    @staticmethod
    def _build_metadata(
        inputs: TradeQualificationInput,
    ) -> Mapping[str, Any]:
        return {
            "engine": "TradeQualificationEngine",
            "inputs": {
                "market_regime": inputs.market_regime is not None,
                "option_chain": inputs.option_chain is not None,
                "greeks": inputs.greeks is not None,
                "liquidity": inputs.liquidity is not None,
                "volatility": inputs.volatility is not None,
                "dealer_positioning": inputs.dealer_positioning is not None,
                "gamma_exposure": inputs.gamma_exposure is not None,
                "vanna_exposure": inputs.vanna_exposure is not None,
                "charm_exposure": inputs.charm_exposure is not None,
                "event_analysis": inputs.event_analysis is not None,
                "news_analysis": inputs.news_analysis is not None,
                "intelligence_fusion": inputs.intelligence_fusion is not None,
            },
        }


# Re-export for convenience
from titan.trading.exceptions import (  # noqa: E402, F401
    TradeQualificationError,
)
