from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    from titan.decision.models import TradeDecision

from titan.brokers.models import Exchange, OrderSide, OrderType, ProductType, Validity


@dataclass(frozen=True, slots=True)
class PlannedOrder:
    symbol: str
    exchange: Exchange
    side: OrderSide
    order_type: OrderType
    quantity: int
    price: Decimal | None = None
    trigger_price: Decimal | None = None
    product: ProductType = ProductType.DELIVERY
    validity: Validity = Validity.DAY
    tag: str = ""


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    plan_id: str
    trade_decision_id: str
    orders: tuple[PlannedOrder, ...] = field(default_factory=tuple)
    strategy: str = "simple"
    total_quantity: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)


class ExecutionPlanner:
    def __init__(self) -> None:
        self._plan_id_counter: int = 0

    def plan(
        self,
        decision: TradeDecision,
        strategy: str = "simple",
        **kwargs: Any,
    ) -> ExecutionPlan:
        if strategy == "simple":
            return self._plan_simple(decision, **kwargs)
        if strategy == "twap":
            return self._plan_twap(decision, **kwargs)
        if strategy == "vwap":
            return self._plan_vwap(decision, **kwargs)
        if strategy == "iceberg":
            return self._plan_iceberg(decision, **kwargs)
        if strategy == "basket":
            return self._plan_basket(decision, **kwargs)
        msg = f"Unknown execution strategy: {strategy}"
        raise ValueError(msg)

    def _plan_simple(self, decision: TradeDecision, **kwargs: Any) -> ExecutionPlan:
        if decision.decision.value not in ("buy", "sell"):
            return ExecutionPlan(
                plan_id=self._next_id(),
                trade_decision_id="",
                orders=(),
                strategy="simple",
            )

        side = OrderSide.BUY if decision.decision.value == "buy" else OrderSide.SELL
        quantity = kwargs.get("quantity", 0)
        if quantity <= 0:
            quantity = 1

        planned = PlannedOrder(
            symbol=decision.symbol,
            exchange=Exchange.NSE,
            side=side,
            order_type=OrderType.MARKET,
            quantity=quantity,
        )

        return ExecutionPlan(
            plan_id=self._next_id(),
            trade_decision_id="",
            orders=(planned,),
            strategy="simple",
            total_quantity=quantity,
        )

    def _plan_twap(self, decision: TradeDecision, **kwargs: Any) -> ExecutionPlan:
        slices = kwargs.get("slices", 4)
        interval_minutes = kwargs.get("interval_minutes", 15)
        total_qty = kwargs.get("quantity", 0)
        if total_qty <= 0:
            total_qty = 1

        side = OrderSide.BUY if decision.decision.value == "buy" else OrderSide.SELL
        actual_slices = min(slices, total_qty)
        qty_per_slice = total_qty // actual_slices
        remainder = total_qty - (qty_per_slice * actual_slices)

        orders: list[PlannedOrder] = []
        for i in range(actual_slices):
            qty = qty_per_slice + (1 if i < remainder else 0)
            if qty <= 0:
                continue
            orders.append(
                PlannedOrder(
                    symbol=decision.symbol,
                    exchange=Exchange.NSE,
                    side=side,
                    order_type=OrderType.MARKET,
                    quantity=qty,
                    tag=f"twap_{i + 1}of{actual_slices}_{interval_minutes}min",
                )
            )

        return ExecutionPlan(
            plan_id=self._next_id(),
            trade_decision_id="",
            orders=tuple(orders),
            strategy="twap",
            total_quantity=total_qty,
            metadata={
                "slices": slices,
                "interval_minutes": interval_minutes,
            },
        )

    def _plan_vwap(self, decision: TradeDecision, **kwargs: Any) -> ExecutionPlan:
        raise NotImplementedError("VWAP execution strategy is not yet implemented.")

    def _plan_iceberg(self, decision: TradeDecision, **kwargs: Any) -> ExecutionPlan:
        raise NotImplementedError("Iceberg execution strategy is not yet implemented.")

    def _plan_basket(self, decision: TradeDecision, **kwargs: Any) -> ExecutionPlan:
        raise NotImplementedError("Basket execution strategy is not yet implemented.")

    def _next_id(self) -> str:
        self._plan_id_counter += 1
        return f"PLAN-{self._plan_id_counter}-{uuid4().hex[:8]}"
