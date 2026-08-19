from titan.options.analytics.models import GammaRegime
from titan.risk.exceptions import RiskEngineError
from titan.risk.models import (
    RISK_PROFILE_MAP,
    RiskInput,
    RiskProfile,
    RiskProfileConfig,
    StopLossPlan,
)


class StopLossEngine:
    """Determines stop loss levels for a qualified trade.

    Produces technical, volatility, time, invalidation, and emergency
    stop levels based on market structure, volatility, and risk profile.
    """

    name = "StopLossEngine"

    def calculate(
        self,
        risk_input: RiskInput,
        risk_profile: RiskProfile = RiskProfile.MODERATE,
        entry_price: float | None = None,
    ) -> StopLossPlan:
        """Compute stop loss plan.

        Args:
            risk_input: Aggregated risk intelligence inputs.
            risk_profile: Risk tolerance profile.
            entry_price: Proposed entry price.

        Returns:
            Complete stop loss plan.

        Raises:
            RiskEngineError: If stop loss calculation fails.
        """

        try:
            return self._compute(risk_input, risk_profile, entry_price)
        except Exception as exc:
            raise RiskEngineError(f"Stop loss calculation failed: {exc}") from exc

    def _compute(
        self,
        risk_input: RiskInput,
        risk_profile: RiskProfile,
        entry_price: float | None,
    ) -> StopLossPlan:
        config = RISK_PROFILE_MAP[risk_profile]

        if entry_price is None or entry_price <= 0.0:
            return StopLossPlan(
                recommended_stop=0.0,
                time_stop="No entry price provided.",
            )

        atr = self._estimate_atr(risk_input, entry_price)
        is_long = risk_input.trade_qualification.long_qualification

        technical = self._technical_stop(risk_input, entry_price, is_long)
        volatility = self._volatility_stop(
            entry_price, atr, config.stop_loss_atr_multiplier, is_long
        )
        time_stop = self._time_stop(risk_input)
        invalidation = self._invalidation_level(risk_input, entry_price, is_long)
        emergency = self._emergency_stop(
            entry_price, atr, config.stop_loss_atr_multiplier, is_long
        )
        recommended = self._recommended_stop(
            technical=technical,
            volatility=volatility,
            emergency=emergency,
            entry_price=entry_price,
            config=config,
            is_long=is_long,
        )

        return StopLossPlan(
            technical_stop=technical,
            volatility_stop=volatility,
            time_stop=time_stop,
            invalidation_level=invalidation,
            emergency_stop=emergency,
            recommended_stop=round(recommended, 2),
        )

    def _estimate_atr(self, risk_input: RiskInput, entry_price: float) -> float:
        volatility = risk_input.volatility
        if volatility is not None and volatility.current_iv is not None:
            return entry_price * (volatility.current_iv / 100.0) * 0.1

        return entry_price * 0.02

    def _technical_stop(
        self,
        risk_input: RiskInput,
        entry_price: float,
        is_long: bool,
    ) -> float | None:
        gamma = risk_input.gamma_exposure
        if gamma is not None and gamma.put_wall is not None:
            if is_long and gamma.put_wall.strike is not None:
                return round(gamma.put_wall.strike, 2)

        if gamma is not None and gamma.call_wall is not None:
            if not is_long and gamma.call_wall.strike is not None:
                return round(gamma.call_wall.strike, 2)

        if gamma is not None and gamma.zero_gamma_level is not None:
            if gamma.zero_gamma_level.strike is not None:
                return round(gamma.zero_gamma_level.strike, 2)

        return None

    def _volatility_stop(
        self,
        entry_price: float,
        atr: float,
        atr_multiplier: float,
        is_long: bool,
    ) -> float:
        if is_long:
            return round(entry_price - (atr * atr_multiplier), 2)
        return round(entry_price + (atr * atr_multiplier), 2)

    def _time_stop(self, risk_input: RiskInput) -> str | None:
        event = risk_input.event_analysis
        if event is not None and event.economic_events:
            upcoming = sorted(
                event.economic_events,
                key=lambda e: e.timestamp,
            )
            if upcoming:
                next_event = upcoming[0]
                return (
                    f"Before {next_event.event_type.value}: "
                    f"{next_event.timestamp.isoformat() if hasattr(next_event.timestamp, 'isoformat') else str(next_event.timestamp)}"
                )

        return None

    def _invalidation_level(
        self,
        risk_input: RiskInput,
        entry_price: float,
        is_long: bool,
    ) -> float | None:
        dealer = risk_input.dealer_positioning
        if dealer is not None:
            side = (
                dealer.dealer_side.value if hasattr(dealer.dealer_side, "value") else ""
            )
            if side == "short_gamma":
                if is_long:
                    return round(entry_price * 0.97, 2)
                return round(entry_price * 1.03, 2)

        gamma = risk_input.gamma_exposure
        if gamma is not None and gamma.gamma_regime == GammaRegime.NEGATIVE:
            if is_long:
                return round(entry_price * 0.98, 2)
            return round(entry_price * 1.02, 2)

        return None

    def _emergency_stop(
        self,
        entry_price: float,
        atr: float,
        atr_multiplier: float,
        is_long: bool,
    ) -> float:
        emergency_multiplier = atr_multiplier * 2.0
        if is_long:
            return round(entry_price - (atr * emergency_multiplier), 2)
        return round(entry_price + (atr * emergency_multiplier), 2)

    def _recommended_stop(
        self,
        technical: float | None,
        volatility: float | None,
        emergency: float | None,
        entry_price: float,
        config: RiskProfileConfig,
        is_long: bool,
    ) -> float:
        candidate = (
            volatility if volatility is not None else (technical or emergency or 0.0)
        )

        if technical is not None:
            if is_long:
                candidate = max(candidate, technical)
            else:
                candidate = min(candidate, technical)

        if is_long:
            candidate = max(
                candidate, entry_price * (1.0 - config.max_risk_per_trade_pct * 5.0)
            )
        else:
            candidate = min(
                candidate, entry_price * (1.0 + config.max_risk_per_trade_pct * 5.0)
            )

        return candidate
