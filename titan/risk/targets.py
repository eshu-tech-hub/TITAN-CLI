from titan.risk.exceptions import RiskEngineError
from titan.risk.models import (
    RISK_PROFILE_MAP,
    RiskInput,
    RiskProfile,
    StopLossPlan,
    TargetPlan,
)


class TargetEngine:
    """Determines target levels for a qualified trade.

    Produces three profit targets, trailing stop trigger level, and
    expected risk-reward ratio based on risk profile and stop loss.
    """

    name = "TargetEngine"

    def calculate(
        self,
        risk_input: RiskInput,
        risk_profile: RiskProfile = RiskProfile.MODERATE,
        entry_price: float | None = None,
        stop_loss: StopLossPlan | None = None,
    ) -> TargetPlan:
        """Compute target plan.

        Args:
            risk_input: Aggregated risk intelligence inputs.
            risk_profile: Risk tolerance profile.
            entry_price: Proposed entry price.
            stop_loss: Stop loss plan for risk distance calculation.

        Returns:
            Complete target plan.

        Raises:
            RiskEngineError: If target calculation fails.
        """

        try:
            return self._compute(risk_input, risk_profile, entry_price, stop_loss)
        except Exception as exc:
            raise RiskEngineError(f"Target calculation failed: {exc}") from exc

    def _compute(
        self,
        risk_input: RiskInput,
        risk_profile: RiskProfile,
        entry_price: float | None,
        stop_loss: StopLossPlan | None,
    ) -> TargetPlan:
        config = RISK_PROFILE_MAP[risk_profile]

        if entry_price is None or entry_price <= 0.0:
            return TargetPlan()

        stop_price = self._effective_stop(stop_loss, entry_price)
        risk_distance = abs(entry_price - stop_price)

        if risk_distance <= 0.0:
            risk_distance = entry_price * 0.02

        is_long = risk_input.trade_qualification.long_qualification

        multipliers = config.target_atr_multipliers
        t1_mult, t2_mult, t3_mult = multipliers

        t1 = self._target_level(entry_price, risk_distance, t1_mult, is_long)
        t2 = self._target_level(entry_price, risk_distance, t2_mult, is_long)
        t3 = self._target_level(entry_price, risk_distance, t3_mult, is_long)
        trailing = t1
        rr = (abs(t3 - entry_price) / risk_distance) if risk_distance > 0.0 else 0.0

        return TargetPlan(
            target_1=round(t1, 2),
            target_2=round(t2, 2),
            target_3=round(t3, 2),
            trailing_stop_trigger=round(trailing, 2),
            expected_risk_reward=round(rr, 2),
        )

    def _effective_stop(
        self,
        stop_loss: StopLossPlan | None,
        entry_price: float,
    ) -> float:
        if stop_loss is None:
            return entry_price * 0.98

        if stop_loss.recommended_stop > 0.0:
            return stop_loss.recommended_stop

        for stop in (
            stop_loss.technical_stop,
            stop_loss.volatility_stop,
            stop_loss.emergency_stop,
        ):
            if stop is not None and stop > 0.0:
                return stop

        return entry_price * 0.98

    def _target_level(
        self,
        entry_price: float,
        risk_distance: float,
        multiplier: float,
        is_long: bool,
    ) -> float:
        if is_long:
            return entry_price + (risk_distance * multiplier)
        return entry_price - (risk_distance * multiplier)
