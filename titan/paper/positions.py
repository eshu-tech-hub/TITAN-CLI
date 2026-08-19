from dataclasses import dataclass, field
from decimal import Decimal

from titan.brokers.models import (
    Holding,
    InstrumentType,
    Position,
    ProductType,
)
from titan.paper.exceptions import PaperPositionError
from titan.paper.models import PaperFill, PaperPosition


@dataclass(slots=True)
class PositionEngine:
    """Tracks open positions for paper trading.

    Maintains average price, realized and unrealized P&L,
    and maximum excursion metrics for each position.

    Attributes:
        _positions: Internal map of symbol -> PaperPosition.
    """

    _positions: dict[str, PaperPosition] = field(default_factory=dict)

    def apply_fill(self, fill: PaperFill) -> None:
        """Update position state based on a fill event.

        Args:
            fill: The fill to apply.

        Raises:
            PaperPositionError: If fill data is invalid.
        """
        if fill.quantity <= 0:
            raise PaperPositionError("Fill quantity must be positive.")

        current = self._positions.get(fill.symbol)

        if current is None:
            self._positions[fill.symbol] = self._open_new(fill)
            return

        self._positions[fill.symbol] = self._update_existing(current, fill)

    def _open_new(self, fill: PaperFill) -> PaperPosition:
        """Create a new position from a fill."""
        quantity = fill.quantity if fill.side.value == "buy" else -fill.quantity
        value = fill.price * Decimal(str(fill.quantity))

        buy_qty = fill.quantity if fill.side.value == "buy" else 0
        sell_qty = fill.quantity if fill.side.value == "sell" else 0
        buy_val = value if fill.side.value == "buy" else Decimal(0)
        sell_val = value if fill.side.value == "sell" else Decimal(0)

        return PaperPosition(
            symbol=fill.symbol,
            exchange=fill.exchange,
            quantity=quantity,
            average_price=fill.price,
            buy_quantity=buy_qty,
            sell_quantity=sell_qty,
            buy_value=buy_val,
            sell_value=sell_val,
            current_price=fill.price,
            mfe=Decimal(0),
            mae=Decimal(0),
            opened_at=fill.timestamp,
            updated_at=fill.timestamp,
        )

    def _update_existing(
        self,
        current: PaperPosition,
        fill: PaperFill,
    ) -> PaperPosition:
        """Update an existing position with a new fill."""
        is_buy = fill.side.value == "buy"

        if is_buy:
            new_quantity = current.quantity + fill.quantity
            new_buy_qty = current.buy_quantity + fill.quantity
            new_buy_val = current.buy_value + fill.price * Decimal(str(fill.quantity))
            new_sell_qty = current.sell_quantity
            new_sell_val = current.sell_value
        else:
            new_quantity = current.quantity - fill.quantity
            new_buy_qty = current.buy_quantity
            new_buy_val = current.buy_value
            new_sell_qty = current.sell_quantity + fill.quantity
            new_sell_val = current.sell_value + fill.price * Decimal(str(fill.quantity))

        realized_pnl = current.realized_pnl
        if (current.quantity > 0 and not is_buy) or (current.quantity < 0 and is_buy):
            if current.average_price is not None:
                if current.quantity > 0:
                    pnl_per_unit = fill.price - current.average_price
                else:
                    pnl_per_unit = current.average_price - fill.price
                closed_qty = min(fill.quantity, abs(current.quantity))
                realized_pnl += pnl_per_unit * Decimal(str(closed_qty))

        if new_quantity == 0:
            average_price = Decimal(0)
        elif is_buy:
            if new_buy_qty > 0:
                average_price = new_buy_val / Decimal(str(new_buy_qty))
            else:
                average_price = Decimal(0)
        else:
            if new_sell_qty > 0:
                average_price = new_sell_val / Decimal(str(new_sell_qty))
            else:
                average_price = Decimal(0)

        unrealized_pnl = self._compute_unrealized_pnl(
            quantity=new_quantity,
            average_price=average_price,
            current_price=fill.price,
        )

        excursion = abs(fill.price - average_price) if average_price else Decimal(0)
        mfe = max(current.mfe, excursion)
        mae = min(current.mae, -excursion)

        return PaperPosition(
            symbol=fill.symbol,
            exchange=fill.exchange,
            quantity=new_quantity,
            average_price=average_price,
            buy_quantity=new_buy_qty,
            sell_quantity=new_sell_qty,
            buy_value=new_buy_val,
            sell_value=new_sell_val,
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl,
            current_price=fill.price,
            mfe=mfe,
            mae=mae,
            opened_at=current.opened_at,
            updated_at=fill.timestamp,
        )

    def close_position(self, symbol: str) -> None:
        """Remove a fully closed position from tracking.

        Args:
            symbol: The symbol to remove.
        """
        if symbol in self._positions:
            pos = self._positions[symbol]
            if pos.quantity == 0:
                del self._positions[symbol]

    def get_position(self, symbol: str) -> PaperPosition | None:
        """Get the current position for a symbol.

        Args:
            symbol: Trading symbol.

        Returns:
            The current PaperPosition, or None if no position exists.
        """
        return self._positions.get(symbol)

    def all_positions(self) -> list[PaperPosition]:
        """Get all tracked positions.

        Returns:
            List of all PaperPosition objects (including closed).
        """
        return list(self._positions.values())

    def open_positions(self) -> list[PaperPosition]:
        """Get only positions with non-zero quantity.

        Returns:
            List of open PaperPosition objects.
        """
        return [p for p in self._positions.values() if p.quantity != 0]

    def to_broker_positions(self) -> list[Position]:
        """Convert internal positions to broker Position models.

        Returns:
            List of broker Position objects.
        """
        result: list[Position] = []
        for pos in self.open_positions():
            is_long = pos.quantity > 0
            result.append(
                Position(
                    symbol=pos.symbol,
                    exchange=pos.exchange,
                    instrument_type=InstrumentType.EQUITY,
                    product=ProductType.DELIVERY,
                    quantity=pos.quantity,
                    buy_quantity=pos.buy_quantity,
                    sell_quantity=pos.sell_quantity,
                    buy_price=pos.average_price if is_long else None,
                    sell_price=pos.average_price if not is_long else None,
                    current_price=pos.current_price,
                    pnl=pos.unrealized_pnl,
                    realised_pnl=pos.realized_pnl,
                )
            )
        return result

    def to_broker_holdings(self) -> list[Holding]:
        """Convert internal positions to broker Holding models.

        Returns:
            List of broker Holding objects.
        """
        result: list[Holding] = []
        for pos in self.open_positions():
            if pos.quantity > 0:
                result.append(
                    Holding(
                        symbol=pos.symbol,
                        exchange=pos.exchange,
                        instrument_type=InstrumentType.EQUITY,
                        quantity=pos.quantity,
                        available_quantity=pos.quantity,
                        buy_price=pos.average_price,
                        current_price=pos.current_price,
                        pnl=pos.unrealized_pnl if pos.average_price else None,
                    )
                )
        return result

    def _compute_unrealized_pnl(
        self,
        quantity: int,
        average_price: Decimal,
        current_price: Decimal,
    ) -> Decimal:
        """Compute unrealized P&L for a position."""
        if average_price == Decimal(0):
            return Decimal(0)
        return (current_price - average_price) * Decimal(str(quantity))

    def reset(self) -> None:
        """Clear all tracked positions."""
        self._positions.clear()
