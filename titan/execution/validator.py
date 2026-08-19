from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal

from titan.brokers.broker import Broker
from titan.brokers.models import FundsInfo
from titan.execution.execution import ExecutionEngine
from titan.execution.planner import ExecutionPlan


@dataclass(frozen=True, slots=True)
class ValidationResult:
    valid: bool
    issues: tuple[str, ...] = field(default_factory=tuple)


class ExecutionValidator:
    def __init__(
        self,
        market_hours_check: Callable[[str], bool] | None = None,
        trading_enabled_check: Callable[[str], bool] | None = None,
        instrument_check: Callable[[str], bool] | None = None,
    ) -> None:
        self._market_hours_check = market_hours_check or (lambda _symbol: True)
        self._trading_enabled_check = trading_enabled_check or (lambda _symbol: True)
        self._instrument_check = instrument_check or (lambda _symbol: True)

    def validate(
        self,
        plan: ExecutionPlan,
        broker: Broker,
        oms: ExecutionEngine,
        required_capital: Decimal | None = None,
    ) -> ValidationResult:
        issues: list[str] = []

        issues.extend(self._check_broker_connected(broker))
        issues.extend(self._check_oms_available(oms))
        issues.extend(self._check_plan_has_orders(plan))

        if not issues:
            for order in plan.orders:
                issues.extend(self._check_market_hours(order.symbol))
                issues.extend(self._check_trading_enabled(order.symbol))
                issues.extend(self._check_instrument_tradable(order.symbol))
                break

        if not issues and required_capital is not None:
            issues.extend(self._check_funds_available(broker, required_capital))
            issues.extend(self._check_margin_available(broker, required_capital))

        return ValidationResult(
            valid=len(issues) == 0,
            issues=tuple(issues),
        )

    def _check_broker_connected(self, broker: Broker) -> list[str]:
        if not broker.is_connected():
            return ["Broker is not connected."]
        return []

    def _check_oms_available(self, oms: ExecutionEngine) -> list[str]:
        registered = oms.router.registered_brokers()
        if not registered:
            return ["Order Management System has no registered brokers."]
        return []

    def _check_plan_has_orders(self, plan: ExecutionPlan) -> list[str]:
        if not plan.orders:
            return ["Execution plan contains no orders."]
        return []

    def _check_market_hours(self, symbol: str) -> list[str]:
        if not self._market_hours_check(symbol):
            return [f"Market is closed for {symbol}."]
        return []

    def _check_trading_enabled(self, symbol: str) -> list[str]:
        if not self._trading_enabled_check(symbol):
            return [f"Trading is not enabled for {symbol}."]
        return []

    def _check_instrument_tradable(self, symbol: str) -> list[str]:
        if not self._instrument_check(symbol):
            return [f"Instrument {symbol} is not tradable."]
        return []

    def _check_funds_available(self, broker: Broker, required: Decimal) -> list[str]:
        try:
            funds: FundsInfo = broker.funds()
            available = Decimal(str(funds.available_cash))
            if available < required:
                return [
                    f"Insufficient funds: {available} available, {required} required."
                ]
        except Exception as exc:
            return [f"Failed to check funds availability: {exc}"]
        return []

    def _check_margin_available(self, broker: Broker, required: Decimal) -> list[str]:
        try:
            margin = broker.margin()
            available = Decimal(str(margin.available_margin))
            if available < required:
                return [
                    f"Insufficient margin: {available} available, {required} required."
                ]
        except Exception as exc:
            return [f"Failed to check margin availability: {exc}"]
        return []
