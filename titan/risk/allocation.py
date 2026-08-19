from titan.risk.exceptions import RiskEngineError
from titan.risk.models import (
    RISK_PROFILE_MAP,
    CapitalAllocation,
    PositionInfo,
    RiskInput,
    RiskProfile,
    RiskProfileConfig,
)


class CapitalAllocationEngine:
    """Determines capital allocation parameters for a qualified trade.

    Calculates capital used, available capital, daily and weekly exposure,
    maximum allocation, and portfolio concentration.
    """

    name = "CapitalAllocationEngine"

    def allocate(
        self,
        risk_input: RiskInput,
        risk_profile: RiskProfile = RiskProfile.MODERATE,
        total_capital: float = 1_000_000.0,
        current_positions: tuple[PositionInfo, ...] = (),
    ) -> CapitalAllocation:
        """Compute capital allocation plan.

        Args:
            risk_input: Aggregated risk intelligence inputs.
            risk_profile: Risk tolerance profile.
            total_capital: Total trading capital.
            current_positions: Currently held positions.

        Returns:
            Complete capital allocation plan.

        Raises:
            RiskEngineError: If capital allocation calculation fails.
        """

        try:
            return self._compute(
                risk_input, risk_profile, total_capital, current_positions
            )
        except Exception as exc:
            raise RiskEngineError(f"Capital allocation failed: {exc}") from exc

    def _compute(
        self,
        risk_input: RiskInput,
        risk_profile: RiskProfile,
        total_capital: float,
        current_positions: tuple[PositionInfo, ...],
    ) -> CapitalAllocation:
        config = RISK_PROFILE_MAP[risk_profile]

        capital_used = (
            sum(p.market_value for p in current_positions) if current_positions else 0.0
        )
        available = max(0.0, total_capital - capital_used)

        daily_exposure = self._daily_exposure(current_positions, total_capital, config)
        weekly_exposure = min(1.0, daily_exposure * 2.5)

        max_alloc = total_capital * config.max_position_size_pct
        event = risk_input.event_analysis
        if event is not None:
            risk_val = event.overall_risk.value
            if risk_val == "extreme":
                max_alloc *= 0.25
            elif risk_val == "high":
                max_alloc *= 0.50

        concentration = self._portfolio_concentration(current_positions, total_capital)

        return CapitalAllocation(
            capital_used=round(capital_used, 2),
            available_capital=round(available, 2),
            daily_exposure=round(daily_exposure, 4),
            weekly_exposure=round(weekly_exposure, 4),
            maximum_allocation=round(max_alloc, 2),
            portfolio_concentration=round(concentration, 4),
        )

    def _daily_exposure(
        self,
        current_positions: tuple[PositionInfo, ...],
        total_capital: float,
        config: RiskProfileConfig,
    ) -> float:
        if not current_positions:
            return 0.0

        total_exposure = 0.0
        for pos in current_positions:
            position_exposure = (
                abs(pos.pnl) / total_capital
                if total_capital > 0 and pos.pnl < 0
                else 0.0
            )
            total_exposure += position_exposure

        return min(1.0, total_exposure)

    def _portfolio_concentration(
        self,
        current_positions: tuple[PositionInfo, ...],
        total_capital: float,
    ) -> float:
        if not current_positions or total_capital <= 0.0:
            return 0.0

        max_value = max(p.market_value for p in current_positions)
        return min(1.0, max_value / total_capital)
