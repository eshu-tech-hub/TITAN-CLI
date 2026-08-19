from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from titan.brokers.models import (
    Exchange,
    OrderSide,
    OrderType,
    ProductType,
    Validity,
)
from titan.execution.models import (
    ExecutionAction,
    OrderEvent,
    OrderRoute,
    OrderState,
)


@dataclass(frozen=True, slots=True)
class Order:
    """TITAN internal order representation.

    This is the single source of truth for order state within the OMS.
    It is distinct from the broker's Order model — it tracks the full
    internal lifecycle, audit trail, and routing information.

    Attributes:
        order_id: TITAN-internal unique order identifier.
        symbol: Trading symbol.
        exchange: Exchange to route the order to.
        side: Buy or sell.
        order_type: Market, limit, or stop-loss.
        quantity: Original order quantity.
        product: Product type.
        validity: Time validity.
        price: Limit price (None for MARKET orders).
        trigger_price: Trigger price for stop-loss orders.
        disclose_quantity: Quantity to disclose.
        tag: Client-provided identifier.
        state: Current OMS lifecycle state.
        broker_order_id: Broker-assigned order ID (None until routed).
        filled_quantity: Quantity filled so far.
        pending_quantity: Quantity still pending.
        average_price: Average fill price.
        action: The execution action taken.
        route: Routing information (None until routed).
        events: Ordered sequence of lifecycle events.
        trade_decision_id: Reference to the originating TradeDecision.
        request_id: Reference to the originating ExecutionRequest.
        created_at: When the order was created.
        updated_at: When the order was last updated.
    """

    order_id: str
    symbol: str
    exchange: Exchange
    side: OrderSide
    order_type: OrderType
    quantity: int
    product: ProductType = ProductType.DELIVERY
    validity: Validity = Validity.DAY
    price: Decimal | None = None
    trigger_price: Decimal | None = None
    disclose_quantity: int = 0
    tag: str = ""
    state: OrderState = OrderState.NEW
    broker_order_id: str | None = None
    filled_quantity: int = 0
    pending_quantity: int = 0
    average_price: Decimal | None = None
    action: ExecutionAction = ExecutionAction.ROUTE
    route: OrderRoute | None = None
    events: tuple[OrderEvent, ...] = field(default_factory=tuple)
    trade_decision_id: str = ""
    request_id: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        return self.state in {
            OrderState.FILLED,
            OrderState.REJECTED,
            OrderState.CANCELLED,
            OrderState.EXPIRED,
            OrderState.FAILED,
        }

    @property
    def is_active(self) -> bool:
        return self.state in {
            OrderState.NEW,
            OrderState.VALIDATED,
            OrderState.SUBMITTED,
            OrderState.ACKNOWLEDGED,
            OrderState.MODIFIED,
            OrderState.PARTIALLY_FILLED,
        }

    def with_state(
        self,
        state: OrderState,
        reason: str = "",
        broker_order_id: str | None = None,
        error: str | None = None,
        filled_quantity: int | None = None,
        pending_quantity: int | None = None,
        average_price: Decimal | None = None,
        route: OrderRoute | None = None,
    ) -> Order:
        """Create a new Order instance with an updated state.

        This is the immutable equivalent of a state mutation. The
        original Order is unchanged; a new instance is returned.
        """
        event = OrderEvent(
            from_state=self.state,
            to_state=state,
            reason=reason,
            broker_order_id=broker_order_id or self.broker_order_id,
            error=error,
        )
        return Order(
            order_id=self.order_id,
            symbol=self.symbol,
            exchange=self.exchange,
            side=self.side,
            order_type=self.order_type,
            quantity=self.quantity,
            product=self.product,
            validity=self.validity,
            price=self.price,
            trigger_price=self.trigger_price,
            disclose_quantity=self.disclose_quantity,
            tag=self.tag,
            state=state,
            broker_order_id=broker_order_id or self.broker_order_id,
            filled_quantity=(
                filled_quantity if filled_quantity is not None else self.filled_quantity
            ),
            pending_quantity=(
                pending_quantity
                if pending_quantity is not None
                else self.pending_quantity
            ),
            average_price=(
                average_price if average_price is not None else self.average_price
            ),
            action=self.action,
            route=route or self.route,
            events=self.events + (event,),
            trade_decision_id=self.trade_decision_id,
            request_id=self.request_id,
            created_at=self.created_at,
            metadata=self.metadata,
        )
