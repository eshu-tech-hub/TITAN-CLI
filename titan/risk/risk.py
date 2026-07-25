from dataclasses import dataclass, field
from datetime import datetime, timezone

from titan.core.evidence import (
    Confidence,
    Evidence,
    EvidenceCategory,
    EvidenceSignal,
    Score,
)

from titan.risk.allocation import CapitalAllocationEngine
from titan.risk.exceptions import RiskEngineError, RiskInputError, RiskValidationError
from titan.risk.exposure import ExposureEngine
from titan.risk.models import (
    CapitalAllocation,
    DecisionContext,
    ExposureAssessment,
    ExposureLevel,
    PositionInfo,
    PositionSizing,
    RiskAnalysis,
    RiskExplanation,
    RiskInput,
    RiskProfile,
    RiskProfileConfig,
    RiskScore,
    RiskScoreBand,
    RISK_PROFILE_MAP,
    StopLossPlan,
    TargetPlan,
)
from titan.risk.position import PositionSizingEngine
from titan.risk.stoploss import StopLossEngine
from titan.risk.targets import TargetEngine


@dataclass(slots=True)
class RiskEngine:
    """Central Risk Intelligence Engine.

    Orchestrates all risk sub-engines to produce a complete risk plan
    for a qualified trade opportunity.

    This engine does NOT determine BUY/SELL, CE/PE, strike selection,
    or order execution. Its responsibility is to answer:
    "If this trade is taken, how should capital be protected and allocated?"

    Internally orchestrates:
        - PositionSizingEngine
        - StopLossEngine
        - TargetEngine
        - CapitalAllocationEngine
        - ExposureEngine
    """

    _position_sizer: PositionSizingEngine = field(default_factory=PositionSizingEngine)
    _stop_loss: StopLossEngine = field(default_factory=StopLossEngine)
    _targets: TargetEngine = field(default_factory=TargetEngine)
    _allocation: CapitalAllocationEngine = field(
        default_factory=CapitalAllocationEngine
    )
    _exposure: ExposureEngine = field(default_factory=ExposureEngine)

    def analyze(
        self,
        risk_input: RiskInput,
        risk_profile: RiskProfile = RiskProfile.MODERATE,
        total_capital: float = 1_000_000.0,
        current_positions: tuple[PositionInfo, ...] = (),
    ) -> RiskAnalysis:
        """Execute complete risk intelligence analysis.

        Args:
            risk_input: Aggregated risk intelligence inputs.
            risk_profile: Risk tolerance profile.
            total_capital: Total trading capital.
            current_positions: Currently held positions.

        Returns:
            Complete risk analysis with all risk planning outputs.

        Raises:
            RiskInputError: If risk input is invalid.
            RiskEngineError: If any sub-engine fails.
        """

        self._validate_inputs(risk_input, risk_profile)

        try:
            entry_price = risk_input.entry_price or risk_input.underlying_price
            config = RISK_PROFILE_MAP[risk_profile]

            sizing = self._position_sizer.size(
                risk_input=risk_input,
                risk_profile=risk_profile,
                total_capital=total_capital,
                entry_price=entry_price,
            )

            stop_loss = self._stop_loss.calculate(
                risk_input=risk_input,
                risk_profile=risk_profile,
                entry_price=entry_price,
            )

            targets = self._targets.calculate(
                risk_input=risk_input,
                risk_profile=risk_profile,
                entry_price=entry_price,
                stop_loss=stop_loss,
            )

            allocation = self._allocation.allocate(
                risk_input=risk_input,
                risk_profile=risk_profile,
                total_capital=total_capital,
                current_positions=current_positions,
            )

            exposure = self._exposure.assess(
                risk_input=risk_input,
                risk_profile=risk_profile,
            )

            risk_score = self._calculate_risk_score(
                sizing=sizing,
                stop_loss=stop_loss,
                allocation=allocation,
                exposure=exposure,
                risk_input=risk_input,
                config=config,
            )

            decision_context = self._generate_decision_context(
                risk_score=risk_score,
                exposure=exposure,
                sizing=sizing,
                risk_input=risk_input,
                config=config,
            )

            evidence = self._generate_evidence(
                risk_score=risk_score,
                decision_context=decision_context,
                risk_input=risk_input,
            )

            explanation = self._generate_explanation(
                sizing=sizing,
                stop_loss=stop_loss,
                targets=targets,
                allocation=allocation,
                exposure=exposure,
                risk_score=risk_score,
                decision_context=decision_context,
            )

            warnings = self._collect_warnings(
                risk_input=risk_input,
                risk_score=risk_score,
                exposure=exposure,
            )

            return RiskAnalysis(
                risk_profile=risk_profile,
                risk_score=risk_score,
                position_sizing=sizing,
                stop_loss=stop_loss,
                targets=targets,
                capital_allocation=allocation,
                exposure=exposure,
                decision_context=decision_context,
                evidence=evidence,
                explanation=explanation,
                warnings=tuple(warnings),
                metadata={
                    "total_capital": total_capital,
                    "position_count": len(current_positions),
                    "sub_engines": [
                        self._position_sizer.name,
                        self._stop_loss.name,
                        self._targets.name,
                        self._allocation.name,
                        self._exposure.name,
                    ],
                },
                timestamp=datetime.now(timezone.utc),
            )

        except RiskInputError, RiskValidationError:
            raise
        except Exception as exc:
            raise RiskEngineError(f"Risk analysis failed: {exc}") from exc

    def _validate_inputs(
        self,
        risk_input: RiskInput,
        risk_profile: RiskProfile,
    ) -> None:
        if not isinstance(risk_input, RiskInput):
            raise RiskInputError("Input must be a RiskInput instance.")

        if not isinstance(risk_profile, RiskProfile):
            raise RiskValidationError("Risk profile must be a RiskProfile enum.")

        if risk_profile not in RISK_PROFILE_MAP:
            raise RiskValidationError(f"Unknown risk profile: {risk_profile}")

    def _calculate_risk_score(
        self,
        sizing: PositionSizing,
        stop_loss: StopLossPlan,
        allocation: CapitalAllocation,
        exposure: ExposureAssessment,
        risk_input: RiskInput,
        config: RiskProfileConfig,
    ) -> RiskScore:
        score_val = risk_input.trade_qualification.trade_score.value
        quality_risk = (100.0 - score_val) * 0.25

        vol = risk_input.volatility
        if vol is not None:
            regime = vol.volatility_regime.value
            if regime == "expansion":
                vol_risk = 20.0
            elif (
                vol.iv_rank_level is not None and vol.iv_rank_level.value == "very_high"
            ):
                vol_risk = 18.0
            elif vol.iv_rank_level is not None and vol.iv_rank_level.value == "high":
                vol_risk = 14.0
            elif regime == "compression":
                vol_risk = 5.0
            else:
                vol_risk = 8.0
        else:
            vol_risk = 8.0

        event = risk_input.event_analysis
        if event is not None:
            risk_val = event.overall_risk.value
            if risk_val == "extreme":
                event_risk = 20.0
            elif risk_val == "high":
                event_risk = 16.0
            elif risk_val == "moderate":
                event_risk = 10.0
            elif risk_val == "low":
                event_risk = 4.0
            else:
                event_risk = 10.0
        else:
            event_risk = 5.0

        liquidity = risk_input.liquidity
        if liquidity is not None:
            grade = liquidity.execution_grade.value
            if grade == "F" or grade == "UNKNOWN":
                liq_risk = 15.0
            elif grade == "D":
                liq_risk = 12.0
            elif grade == "C":
                liq_risk = 10.0
            elif grade == "B":
                liq_risk = 5.0
            elif grade == "A":
                liq_risk = 0.0
            else:
                liq_risk = 7.5
        else:
            liq_risk = 5.0

        stop_risk = 10.0
        stop_count = sum(
            1
            for s in (
                stop_loss.technical_stop,
                stop_loss.volatility_stop,
                stop_loss.emergency_stop,
                stop_loss.invalidation_level,
            )
            if s is not None
        )
        stop_risk -= stop_count * 2.5
        stop_risk = max(0.0, stop_risk)

        regime_analysis = risk_input.market_regime
        if regime_analysis is not None and hasattr(regime_analysis, "confidence"):
            regime_risk = (1.0 - min(1.0, max(0.0, regime_analysis.confidence))) * 10.0
        else:
            regime_risk = 5.0

        total = (
            quality_risk + vol_risk + event_risk + liq_risk + stop_risk + regime_risk
        )
        total = max(0.0, min(100.0, total))

        band = self._determine_risk_band(total)

        return RiskScore(value=round(total, 2), band=band)

    def _determine_risk_band(self, score: float) -> RiskScoreBand:
        if score <= 25.0:
            return RiskScoreBand.VERY_LOW
        if score <= 45.0:
            return RiskScoreBand.LOW
        if score <= 65.0:
            return RiskScoreBand.MODERATE
        if score <= 85.0:
            return RiskScoreBand.HIGH
        return RiskScoreBand.EXTREME

    def _generate_decision_context(
        self,
        risk_score: RiskScore,
        exposure: ExposureAssessment,
        sizing: PositionSizing,
        risk_input: RiskInput,
        config: RiskProfileConfig,
    ) -> DecisionContext:
        band = risk_score.band

        avoid = band in (RiskScoreBand.EXTREME,)
        reduce = band in (RiskScoreBand.HIGH, RiskScoreBand.EXTREME)
        increase = band == RiskScoreBand.VERY_LOW
        normal = band in (RiskScoreBand.LOW, RiskScoreBand.MODERATE)

        hedge = exposure.overall_portfolio_risk in (
            ExposureLevel.HIGH,
            ExposureLevel.EXTREME,
        )

        if risk_input.event_analysis is not None:
            risk_val = risk_input.event_analysis.overall_risk.value
            if risk_val == "extreme":
                avoid = True

        max_contracts = sizing.maximum_quantity

        confidence = self._compute_confidence(risk_score)

        return DecisionContext(
            reduce_size=reduce,
            normal_size=normal,
            increase_size=increase,
            avoid_trade=avoid,
            hedging_required=hedge,
            maximum_contracts=max_contracts,
            confidence=round(confidence, 4),
        )

    def _compute_confidence(self, risk_score: RiskScore) -> float:
        score = risk_score.value
        if score <= 20.0:
            return 0.9
        if score <= 40.0:
            return 0.7
        if score <= 60.0:
            return 0.5
        if score <= 80.0:
            return 0.3
        return 0.1

    def _generate_evidence(
        self,
        risk_score: RiskScore,
        decision_context: DecisionContext,
        risk_input: RiskInput,
    ) -> Evidence:
        score_val = 100.0 - risk_score.value

        if decision_context.avoid_trade:
            signal = EvidenceSignal.VERY_BEARISH
        elif decision_context.reduce_size:
            signal = EvidenceSignal.BEARISH
        elif decision_context.increase_size:
            signal = EvidenceSignal.VERY_BULLISH
        elif decision_context.normal_size:
            signal = EvidenceSignal.NEUTRAL
        else:
            signal = EvidenceSignal.NEUTRAL

        reasons = [
            f"Risk Score: {risk_score.value:.1f}/100 ({risk_score.band.value})",
        ]
        if decision_context.avoid_trade:
            reasons.append("Trade avoidance recommended by risk intelligence.")
        if decision_context.hedging_required:
            reasons.append("Hedging recommended based on exposure assessment.")

        warnings: list[str] = []
        if risk_score.band == RiskScoreBand.EXTREME:
            warnings.append("Risk score is at extreme level.")
        if decision_context.hedging_required:
            warnings.append("Hedging is required for this position.")

        return Evidence(
            source="RiskEngine",
            category=EvidenceCategory.RISK,
            signal=signal,
            score=Score(score_val),
            confidence=Confidence(decision_context.confidence),
            weight=1.0,
            reasons=tuple(reasons),
            warnings=tuple(warnings),
            metadata={
                "risk_score": risk_score.value,
                "risk_band": risk_score.band.value,
                "avoid_trade": decision_context.avoid_trade,
                "hedging_required": decision_context.hedging_required,
            },
        )

    def _generate_explanation(
        self,
        sizing: PositionSizing,
        stop_loss: StopLossPlan,
        targets: TargetPlan,
        allocation: CapitalAllocation,
        exposure: ExposureAssessment,
        risk_score: RiskScore,
        decision_context: DecisionContext,
    ) -> RiskExplanation:
        position_text = (
            f"Position Sizing: Maximum capital {sizing.maximum_capital:.2f}, "
            f"risk per trade {sizing.risk_per_trade:.2f}, "
            f"units {sizing.units}, contracts {sizing.contracts}, "
            f"capital utilisation {sizing.capital_utilization:.1%}."
        )

        allocation_text = (
            f"Capital Allocation: Used {allocation.capital_used:.2f}, "
            f"available {allocation.available_capital:.2f}, "
            f"max allocation {allocation.maximum_allocation:.2f}, "
            f"portfolio concentration {allocation.portfolio_concentration:.1%}."
        )

        stop_text = f"Stop Loss: Recommended at {stop_loss.recommended_stop:.2f}"
        if stop_loss.technical_stop is not None:
            stop_text += f", technical stop {stop_loss.technical_stop:.2f}"
        if stop_loss.volatility_stop is not None:
            stop_text += f", volatility stop {stop_loss.volatility_stop:.2f}"
        if stop_loss.time_stop is not None:
            stop_text += f", time stop ({stop_loss.time_stop})"
        stop_text += "."

        target_text = (
            f"Targets: T1 {targets.target_1:.2f}, "
            f"T2 {targets.target_2:.2f}, "
            f"T3 {targets.target_3:.2f}, "
            f"trailing trigger {targets.trailing_stop_trigger:.2f}, "
            f"expected R:R {targets.expected_risk_reward:.2f}."
        )

        exposure_text = (
            f"Exposure: Directional {exposure.directional_exposure.value}, "
            f"volatility {exposure.volatility_exposure.value}, "
            f"event {exposure.event_exposure.value}, "
            f"liquidity {exposure.liquidity_exposure.value}, "
            f"overall {exposure.overall_portfolio_risk.value}."
        )

        overall = (
            f"Overall Risk Assessment: Score {risk_score.value:.1f}/100 "
            f"({risk_score.band.value}). "
        )
        if decision_context.avoid_trade:
            overall += "Trade should be avoided based on risk intelligence."
        elif decision_context.reduce_size:
            overall += "Reduce position size due to elevated risk."
        elif decision_context.increase_size:
            overall += "Conditions favour increased position size."
        elif decision_context.normal_size:
            overall += "Standard position sizing is appropriate."
        overall += f" Confidence in assessment: {decision_context.confidence:.1%}."

        return RiskExplanation(
            position_size=position_text,
            capital_allocation=allocation_text,
            stop_loss=stop_text,
            targets=target_text,
            exposure=exposure_text,
            overall_risk_assessment=overall,
        )

    def _collect_warnings(
        self,
        risk_input: RiskInput,
        risk_score: RiskScore,
        exposure: ExposureAssessment,
    ) -> list[str]:
        warnings: list[str] = []

        if risk_score.band == RiskScoreBand.EXTREME:
            warnings.append("EXTREME risk score — exercise maximum caution.")

        if exposure.overall_portfolio_risk == ExposureLevel.EXTREME:
            warnings.append("Extreme overall portfolio exposure detected.")

        event = risk_input.event_analysis
        if event is not None:
            risk_val = event.overall_risk.value
            if risk_val in ("extreme", "high"):
                warnings.append(f"Event risk is {risk_val} — consider reducing size.")

        if risk_input.liquidity is not None:
            grade = risk_input.liquidity.execution_grade
            if grade.value in ("F", "UNKNOWN"):
                warnings.append("Poor execution liquidity — slippage risk is high.")

        return warnings
