from math import floor

from titan.options.analytics.models import ExecutionGrade, IVRankLevel, VolatilityRegime

from titan.risk.exceptions import RiskEngineError
from titan.risk.models import (
    PositionSizing,
    RiskInput,
    RiskProfile,
    RiskProfileConfig,
    RISK_PROFILE_MAP,
)


class PositionSizingEngine:
    """Determines position size parameters for a qualified trade.

    This engine calculates maximum capital allocation, risk per trade,
    units, contracts, and capital utilisation based on the risk profile,
    trade score, liquidity, volatility, and event risk.

    It does NOT decide whether to trade — only how much to risk if traded.
    """

    name = "PositionSizingEngine"

    def size(
        self,
        risk_input: RiskInput,
        risk_profile: RiskProfile = RiskProfile.MODERATE,
        total_capital: float = 1_000_000.0,
        entry_price: float | None = None,
    ) -> PositionSizing:
        """Compute position sizing parameters.

        Args:
            risk_input: Aggregated risk intelligence inputs.
            risk_profile: Risk tolerance profile.
            total_capital: Total trading capital.
            entry_price: Proposed entry price per unit.

        Returns:
            Complete position sizing plan.

        Raises:
            RiskEngineError: If position sizing cannot be computed.
        """

        try:
            return self._compute(risk_input, risk_profile, total_capital, entry_price)
        except Exception as exc:
            raise RiskEngineError(f"Position sizing failed: {exc}") from exc

    def _compute(
        self,
        risk_input: RiskInput,
        risk_profile: RiskProfile,
        total_capital: float,
        entry_price: float | None,
    ) -> PositionSizing:
        config = RISK_PROFILE_MAP[risk_profile]

        safe_capital = max(total_capital, 0.0)
        base_max_capital = safe_capital * config.max_position_size_pct
        base_risk_per_trade = safe_capital * config.max_risk_per_trade_pct

        size_modifier = self._size_modifier(risk_input, config)
        max_capital = base_max_capital * size_modifier
        risk_per_trade = base_risk_per_trade * size_modifier

        units = self._calculate_units(
            risk_per_trade=risk_per_trade,
            entry_price=entry_price,
            max_capital=max_capital,
            config=config,
        )

        contracts = self._calculate_contracts(units, entry_price)

        max_quantity = self._maximum_quantity(units, risk_input, config)

        util = (
            (units * (entry_price or 1.0)) / safe_capital
            if entry_price and entry_price > 0.0 and safe_capital > 0.0
            else 0.0
        )

        return PositionSizing(
            maximum_capital=round(max_capital, 2),
            risk_per_trade=round(risk_per_trade, 2),
            units=units,
            contracts=contracts,
            maximum_quantity=max_quantity,
            capital_utilization=min(1.0, round(util, 4)),
        )

    def _size_modifier(
        self,
        risk_input: RiskInput,
        config: RiskProfileConfig,
    ) -> float:
        modifier = 1.0

        score_val = risk_input.trade_qualification.trade_score.value
        if score_val >= 80.0:
            modifier *= 1.25
        elif score_val >= 60.0:
            modifier *= 1.0
        elif score_val >= 40.0:
            modifier *= 0.75
        elif score_val >= 20.0:
            modifier *= 0.50
        else:
            modifier *= 0.25

        liquidity = risk_input.liquidity
        if liquidity is not None and liquidity.execution_grade in (
            ExecutionGrade.D,
            ExecutionGrade.F,
            ExecutionGrade.UNKNOWN,
        ):
            modifier *= 0.50

        volatility = risk_input.volatility
        if volatility is not None:
            if volatility.volatility_regime == VolatilityRegime.EXPANSION:
                modifier *= 0.75
            elif volatility.iv_rank_level in (
                IVRankLevel.VERY_HIGH,
                IVRankLevel.HIGH,
            ):
                modifier *= 0.85

        event = risk_input.event_analysis
        if event is not None:
            risk_val = event.overall_risk.value
            if risk_val in ("extreme", "high"):
                modifier *= 0.50

        confidence = risk_input.trade_qualification.confidence
        if confidence < config.min_confidence_threshold:
            modifier *= 0.50

        return max(0.05, min(2.0, modifier))

    def _calculate_units(
        self,
        risk_per_trade: float,
        entry_price: float | None,
        max_capital: float,
        config: RiskProfileConfig,
    ) -> int:
        if entry_price is None or entry_price <= 0.0:
            return 0

        risk_per_unit = entry_price * config.max_risk_per_trade_pct
        if risk_per_unit <= 0.0:
            return 0

        units_from_risk = int(floor(risk_per_trade / risk_per_unit))
        units_from_capital = int(floor(max_capital / entry_price))

        return max(1, min(units_from_risk, units_from_capital))

    def _calculate_contracts(self, units: int, entry_price: float | None) -> int:
        if entry_price is None or entry_price <= 0.0 or units == 0:
            return 0

        lot_size = self._estimate_lot_size(entry_price)
        return max(1, int(floor(units / lot_size)))

    def _maximum_quantity(
        self,
        units: int,
        risk_input: RiskInput,
        config: RiskProfileConfig,
    ) -> int:
        quantity = units

        event = risk_input.event_analysis
        if event is not None:
            risk_val = event.overall_risk.value
            if risk_val == "extreme":
                quantity = min(quantity, 1)
            elif risk_val == "high":
                quantity = min(quantity, int(round(quantity * 0.5)))

        return max(1, quantity)

    def _estimate_lot_size(self, price: float) -> int:
        if price >= 100000:
            return 50
        if price >= 50000:
            return 100
        if price >= 10000:
            return 250
        if price >= 1000:
            return 500
        return 1000
