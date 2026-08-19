from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from titan.brokers.models import (
    Order,
    OrderStatus,
    Trade,
)
from titan.paper.models import PaperFill, PaperOrder


@dataclass(slots=True)
class TradeJournal:
    """Records every paper trading event with timestamps.

    Stores orders, fills, modifications, cancellations,
    position changes, and exits for later analysis.

    Attributes:
        _orders: Internal order ID -> PaperOrder.
        _trades: List of Trade records.
        _events: Chronological event log.
    """

    _orders: dict[str, PaperOrder] = field(default_factory=dict)
    _trades: list[Trade] = field(default_factory=list)
    _events: list[dict[str, Any]] = field(default_factory=list)

    def record_order(self, order: PaperOrder) -> None:
        """Record a new order.

        Args:
            order: The order to record.
        """
        self._orders[order.order_id] = order
        self._log("order_placed", order_id=order.order_id, symbol=order.symbol)

    def update_order(self, order: PaperOrder) -> None:
        """Update an existing order record.

        Args:
            order: Updated order state.
        """
        self._orders[order.order_id] = order

    def record_fill(
        self,
        fill: PaperFill,
        order: PaperOrder,
    ) -> None:
        """Record a fill event and update the parent order.

        Args:
            fill: The fill to record.
            order: The order being filled.
        """
        updated_order = PaperOrder(
            order_id=order.order_id,
            broker_order_id=order.broker_order_id,
            symbol=order.symbol,
            exchange=order.exchange,
            side=order.side,
            order_type=order.order_type,
            quantity=order.quantity,
            filled_quantity=order.filled_quantity + fill.quantity,
            pending_quantity=order.quantity - (order.filled_quantity + fill.quantity),
            price=order.price,
            trigger_price=order.trigger_price,
            product=order.product,
            status=(
                OrderStatus.PARTIALLY_FILLED
                if order.filled_quantity + fill.quantity < order.quantity
                else OrderStatus.FILLED
            ),
            fills=order.fills + (fill,),
            tag=order.tag,
            placed_at=order.placed_at,
            filled_at=fill.timestamp,
            metadata=order.metadata,
        )
        self._orders[order.order_id] = updated_order

        trade = Trade(
            trade_id=fill.fill_id,
            broker_order_id=fill.broker_order_id,
            symbol=fill.symbol,
            exchange=fill.exchange,
            side=fill.side,
            quantity=fill.quantity,
            price=fill.price,
            product=fill.product,
            trade_time=fill.timestamp,
        )
        self._trades.append(trade)
        self._log(
            "fill",
            fill_id=fill.fill_id,
            order_id=order.order_id,
            symbol=fill.symbol,
            quantity=fill.quantity,
            price=str(fill.price),
        )

    def record_modification(
        self,
        order_id: str,
        field_name: str,
        old_value: Any,
        new_value: Any,
    ) -> None:
        """Record an order modification.

        Args:
            order_id: ID of the modified order.
            field_name: Name of the modified field.
            old_value: Previous value.
            new_value: New value.
        """
        self._log(
            "modification",
            order_id=order_id,
            field=field_name,
            old=str(old_value),
            new=str(new_value),
        )

    def record_cancellation(self, order_id: str, reason: str = "") -> None:
        """Record an order cancellation.

        Args:
            order_id: ID of the cancelled order.
            reason: Optional cancellation reason.
        """
        order = self._orders.get(order_id)
        if order is not None and order.status not in (
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
        ):
            cancelled = PaperOrder(
                order_id=order.order_id,
                broker_order_id=order.broker_order_id,
                symbol=order.symbol,
                exchange=order.exchange,
                side=order.side,
                order_type=order.order_type,
                quantity=order.quantity,
                filled_quantity=order.filled_quantity,
                pending_quantity=order.pending_quantity,
                price=order.price,
                trigger_price=order.trigger_price,
                product=order.product,
                status=OrderStatus.CANCELLED,
                fills=order.fills,
                tag=order.tag,
                rejected_reason=reason,
                placed_at=order.placed_at,
                metadata=order.metadata,
            )
            self._orders[order_id] = cancelled

        self._log("cancellation", order_id=order_id, reason=reason)

    def record_position_change(
        self,
        symbol: str,
        old_quantity: int,
        new_quantity: int,
    ) -> None:
        """Record a position quantity change.

        Args:
            symbol: Trading symbol.
            old_quantity: Previous quantity.
            new_quantity: New quantity.
        """
        self._log(
            "position_change",
            symbol=symbol,
            old_qty=old_quantity,
            new_qty=new_quantity,
        )

    def record_exit(self, symbol: str, pnl: Any = None) -> None:
        """Record a full position exit.

        Args:
            symbol: Trading symbol.
            pnl: Realized P&L from the exit (optional).
        """
        self._log("exit", symbol=symbol, pnl=str(pnl) if pnl is not None else None)

    def get_order(self, order_id: str) -> PaperOrder | None:
        """Get an order by internal ID.

        Args:
            order_id: Internal order ID.

        Returns:
            PaperOrder if found, None otherwise.
        """
        return self._orders.get(order_id)

    def get_order_by_broker_id(self, broker_order_id: str) -> PaperOrder | None:
        """Get an order by broker-assigned ID.

        Args:
            broker_order_id: Broker-assigned order ID.

        Returns:
            PaperOrder if found, None otherwise.
        """
        for order in self._orders.values():
            if order.broker_order_id == broker_order_id:
                return order
        return None

    def all_orders(self) -> list[PaperOrder]:
        """Get all recorded orders.

        Returns:
            List of all PaperOrder objects.
        """
        return list(self._orders.values())

    def orders(
        self,
        symbol: str | None = None,
        since: datetime | None = None,
    ) -> list[PaperOrder]:
        """Get filtered orders.

        Args:
            symbol: Filter by symbol (optional).
            since: Filter by placement time (optional).

        Returns:
            Filtered list of PaperOrder objects.
        """
        result = self.all_orders()
        if symbol is not None:
            result = [o for o in result if o.symbol == symbol]
        if since is not None:
            result = [
                o for o in result if o.placed_at is not None and o.placed_at >= since
            ]
        return result

    def to_broker_order(self, order: PaperOrder) -> Order:
        """Convert a PaperOrder to a broker Order model.

        Args:
            order: Internal paper order.

        Returns:
            Broker Order model.
        """
        return Order(
            broker_order_id=order.broker_order_id,
            symbol=order.symbol,
            exchange=order.exchange,
            side=order.side,
            order_type=order.order_type,
            product=order.product,
            status=order.status,
            quantity=order.quantity,
            filled_quantity=order.filled_quantity,
            pending_quantity=order.pending_quantity,
            average_price=self._compute_average_price(order),
            price=order.price,
            trigger_price=order.trigger_price,
            tag=order.tag,
            rejected_reason=order.rejected_reason,
            placed_at=order.placed_at,
            filled_at=order.filled_at,
        )

    def to_broker_orders(
        self,
        symbol: str | None = None,
        since: datetime | None = None,
    ) -> list[Order]:
        """Convert filtered orders to broker Order models.

        Args:
            symbol: Filter by symbol (optional).
            since: Filter by placement time (optional).

        Returns:
            List of broker Order models.
        """
        return [self.to_broker_order(o) for o in self.orders(symbol, since)]

    def to_broker_trades(
        self,
        symbol: str | None = None,
        since: datetime | None = None,
    ) -> list[Trade]:
        """Get trades optionally filtered.

        Args:
            symbol: Filter by symbol (optional).
            since: Filter by trade time (optional).

        Returns:
            List of broker Trade models.
        """
        result = list(self._trades)
        if symbol is not None:
            result = [t for t in result if t.symbol == symbol]
        if since is not None:
            result = [
                t for t in result if t.trade_time is not None and t.trade_time >= since
            ]
        return result

    def events(self) -> list[dict[str, Any]]:
        """Get the full chronological event log.

        Returns:
            List of event dictionaries.
        """
        return list(self._events)

    def _compute_average_price(self, order: PaperOrder) -> Decimal | None:
        """Compute the average fill price for an order."""
        if not order.fills:
            return None
        total_value = sum(f.price * Decimal(str(f.quantity)) for f in order.fills)
        total_qty = sum(f.quantity for f in order.fills)
        if total_qty == 0:
            return None
        return (total_value / Decimal(str(total_qty))).quantize(Decimal("0.01"))

    def _log(self, event_type: str, **kwargs: Any) -> None:
        """Append an event to the chronological log."""
        entry: dict[str, Any] = {
            "type": event_type,
            "timestamp": datetime.now(UTC),
        }
        entry.update(kwargs)
        self._events.append(entry)

    def reset(self) -> None:
        """Clear all journal data."""
        self._orders.clear()
        self._trades.clear()
        self._events.clear()
