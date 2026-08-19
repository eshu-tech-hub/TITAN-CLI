from titan.events.models import EventImportance, EventRisk
from titan.options.analytics.models import (
    DealerSide,
    ExecutionGrade,
    GammaRegime,
    IVHVRelation,
    IVRankLevel,
    VolatilityRegime,
)
from titan.risk.exceptions import RiskEngineError
from titan.risk.models import (
    ExposureAssessment,
    ExposureLevel,
    RiskInput,
    RiskProfile,
)


class ExposureEngine:
    """Assesses exposure across multiple risk dimensions.

    Evaluates directional, volatility, event, sector, and liquidity
    exposure to produce an overall portfolio risk assessment.
    """

    name = "ExposureEngine"

    def assess(
        self,
        risk_input: RiskInput,
        risk_profile: RiskProfile = RiskProfile.MODERATE,
    ) -> ExposureAssessment:
        """Compute exposure assessment.

        Args:
            risk_input: Aggregated risk intelligence inputs.
            risk_profile: Risk tolerance profile.

        Returns:
            Complete exposure assessment.

        Raises:
            RiskEngineError: If exposure assessment fails.
        """

        try:
            return self._compute(risk_input, risk_profile)
        except Exception as exc:
            raise RiskEngineError(f"Exposure assessment failed: {exc}") from exc

    def _compute(
        self,
        risk_input: RiskInput,
        risk_profile: RiskProfile,
    ) -> ExposureAssessment:
        directional = self._directional_exposure(risk_input)
        volatility = self._volatility_exposure(risk_input)
        event = self._event_exposure(risk_input)
        sector = self._sector_exposure(risk_input)
        liquidity = self._liquidity_exposure(risk_input)
        overall = self._overall_risk(
            directional, volatility, event, sector, liquidity, risk_profile
        )

        return ExposureAssessment(
            directional_exposure=directional,
            volatility_exposure=volatility,
            event_exposure=event,
            sector_exposure=sector,
            liquidity_exposure=liquidity,
            overall_portfolio_risk=overall,
        )

    def _directional_exposure(self, risk_input: RiskInput) -> ExposureLevel:
        dealer = risk_input.dealer_positioning
        if dealer is not None:
            side = dealer.dealer_side
            if side == DealerSide.SHORT_GAMMA:
                return ExposureLevel.HIGH

        gamma = risk_input.gamma_exposure
        if gamma is not None:
            regime = gamma.gamma_regime
            if regime == GammaRegime.NEGATIVE:
                return ExposureLevel.HIGH
            if regime == GammaRegime.POSITIVE:
                return ExposureLevel.LOW

        confidence = risk_input.trade_qualification.confidence
        if confidence < 0.3:
            return ExposureLevel.MODERATE

        return ExposureLevel.LOW

    def _volatility_exposure(self, risk_input: RiskInput) -> ExposureLevel:
        volatility = risk_input.volatility
        if volatility is not None:
            regime = volatility.volatility_regime
            if regime == VolatilityRegime.EXPANSION:
                return ExposureLevel.HIGH

            rank = volatility.iv_rank_level
            if rank in (IVRankLevel.VERY_HIGH, IVRankLevel.HIGH):
                return ExposureLevel.MODERATE

            relation = volatility.iv_vs_hv
            if relation == IVHVRelation.MISPRICING:
                return ExposureLevel.HIGH

        return ExposureLevel.LOW

    def _event_exposure(self, risk_input: RiskInput) -> ExposureLevel:
        event = risk_input.event_analysis
        if event is not None:
            risk_val = event.overall_risk
            if risk_val == EventRisk.EXTREME:
                return ExposureLevel.EXTREME
            if risk_val == EventRisk.HIGH:
                return ExposureLevel.HIGH
            if risk_val == EventRisk.MODERATE:
                return ExposureLevel.MODERATE

            importance = event.highest_importance
            if importance == EventImportance.CRITICAL:
                return ExposureLevel.HIGH

        return ExposureLevel.LOW

    def _sector_exposure(self, risk_input: RiskInput) -> ExposureLevel:
        regime = risk_input.market_regime
        if regime is not None:
            strength = regime.trend_strength
            if strength < 0.3:
                return ExposureLevel.MODERATE

        return ExposureLevel.LOW

    def _liquidity_exposure(self, risk_input: RiskInput) -> ExposureLevel:
        liquidity = risk_input.liquidity
        if liquidity is not None:
            grade = liquidity.execution_grade
            if grade in (ExecutionGrade.F, ExecutionGrade.UNKNOWN):
                return ExposureLevel.EXTREME
            if grade == ExecutionGrade.D:
                return ExposureLevel.HIGH
            if grade == ExecutionGrade.C:
                return ExposureLevel.MODERATE
            if grade == ExecutionGrade.B:
                return ExposureLevel.LOW
            if grade == ExecutionGrade.A:
                return ExposureLevel.VERY_LOW

        return ExposureLevel.LOW

    def _overall_risk(
        self,
        directional: ExposureLevel,
        volatility: ExposureLevel,
        event: ExposureLevel,
        sector: ExposureLevel,
        liquidity: ExposureLevel,
        risk_profile: RiskProfile,
    ) -> ExposureLevel:
        levels = [directional, volatility, event, sector, liquidity]
        score_map = {
            ExposureLevel.VERY_LOW: 0,
            ExposureLevel.LOW: 1,
            ExposureLevel.MODERATE: 2,
            ExposureLevel.HIGH: 3,
            ExposureLevel.EXTREME: 4,
        }

        total = sum(score_map[level] for level in levels)
        avg = total / len(levels)
        high_count = sum(
            1
            for level in levels
            if level in (ExposureLevel.HIGH, ExposureLevel.EXTREME)
        )

        if any(level == ExposureLevel.EXTREME for level in levels):
            return ExposureLevel.EXTREME

        if high_count >= 3:
            return ExposureLevel.HIGH
        if avg >= 2.0:
            return ExposureLevel.MODERATE
        if avg >= 1.0:
            return ExposureLevel.LOW

        return ExposureLevel.VERY_LOW
