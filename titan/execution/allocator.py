from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Mapping, TYPE_CHECKING

if TYPE_CHECKING:
    from titan.decision.models import TradeDecision

from titan.portfolio.models import PortfolioSnapshot
from titan.risk.models import RiskAnalysis


@dataclass(frozen=True, slots=True)
class AllocationInstruction:
    execution_quantity: int
    execution_price: Decimal | None = None
    capital_allocated: float = 0.0
    price_reference: str = "market"
    metadata: Mapping[str, Any] = field(default_factory=dict)


class ExecutionAllocator:
    def allocate(
        self,
        decision: TradeDecision,
        portfolio: PortfolioSnapshot,
        risk: RiskAnalysis,
    ) -> AllocationInstruction:
        position_sizing = risk.position_sizing
        capital_allocation = risk.capital_allocation

        max_allocation = Decimal(str(capital_allocation.maximum_allocation))
        max_contracts = risk.decision_context.maximum_contracts

        unit_price = Decimal(str(decision.stop_loss_reference or 1))
        if unit_price <= Decimal("0"):
            unit_price = Decimal("1")

        max_qty_from_capital = (
            int(max_allocation / unit_price) if max_allocation > 0 else 0
        )
        available_qty = (
            int(portfolio.available_capital / float(unit_price))
            if portfolio.available_capital > 0
            else 0
        )
        sized_quantity = position_sizing.maximum_quantity

        effective_qty = sized_quantity
        if max_qty_from_capital > 0 and effective_qty > max_qty_from_capital:
            effective_qty = max_qty_from_capital
        if available_qty > 0 and effective_qty > available_qty:
            effective_qty = available_qty
        if max_contracts > 0 and effective_qty > max_contracts:
            effective_qty = max_contracts
        if effective_qty < 1:
            effective_qty = 1

        capital_used = float(effective_qty) * float(unit_price)

        return AllocationInstruction(
            execution_quantity=effective_qty,
            execution_price=unit_price if unit_price > Decimal("0") else None,
            capital_allocated=capital_used,
            price_reference="risk_analysis",
            metadata={
                "sized_quantity": sized_quantity,
                "max_qty_from_capital": max_qty_from_capital,
                "available_qty": available_qty,
                "max_contracts": max_contracts,
                "capital_available": portfolio.available_capital,
                "maximum_allocation": float(max_allocation),
            },
        )
