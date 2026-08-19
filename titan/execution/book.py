from collections.abc import Sequence
from datetime import datetime

from titan.execution.exceptions import OrderNotFoundError
from titan.execution.models import OrderState
from titan.execution.order import Order


class OrderBook:
    """Central repository for all orders in the OMS.

    Maintains the authoritative state of every order. The OrderBook
    is the single source of truth — no other component holds order
    state directly.

    All mutation methods return the updated Order to support
    immutable dataclass patterns. The caller is responsible for
    providing the updated Order instance.
    """

    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def lookup(self, order_id: str) -> Order:
        """Retrieve an order by its TITAN internal ID.

        Raises:
            OrderNotFoundError: If the order ID is not found.
        """
        order = self._orders.get(order_id)
        if order is None:
            raise OrderNotFoundError(f"Order '{order_id}' not found in the order book.")
        return order

    def get(self, order_id: str) -> Order | None:
        """Retrieve an order without raising if not found."""
        return self._orders.get(order_id)

    @property
    def all_orders(self) -> Sequence[Order]:
        return tuple(self._orders.values())

    @property
    def open_orders(self) -> Sequence[Order]:
        return tuple(
            o
            for o in self._orders.values()
            if o.state
            in {
                OrderState.NEW,
                OrderState.VALIDATED,
                OrderState.SUBMITTED,
                OrderState.ACKNOWLEDGED,
                OrderState.MODIFIED,
                OrderState.PARTIALLY_FILLED,
            }
        )

    @property
    def filled_orders(self) -> Sequence[Order]:
        return tuple(o for o in self._orders.values() if o.state == OrderState.FILLED)

    @property
    def cancelled_orders(self) -> Sequence[Order]:
        return tuple(
            o for o in self._orders.values() if o.state == OrderState.CANCELLED
        )

    @property
    def rejected_orders(self) -> Sequence[Order]:
        return tuple(o for o in self._orders.values() if o.state == OrderState.REJECTED)

    @property
    def active_orders(self) -> Sequence[Order]:
        return self.open_orders

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def add(self, order: Order) -> Order:
        """Add a new order to the book.

        Args:
            order: The order to add.

        Raises:
            ValueError: If an order with the same ID already exists.
        """
        if order.order_id in self._orders:
            raise ValueError(
                f"Order '{order.order_id}' already exists in the order book."
            )
        self._orders[order.order_id] = order
        return order

    def update(self, order: Order) -> Order:
        """Replace an existing order with an updated version.

        Args:
            order: The updated order (must have an existing ID).

        Raises:
            OrderNotFoundError: If the order ID is not in the book.
        """
        if order.order_id not in self._orders:
            raise OrderNotFoundError(
                f"Cannot update order '{order.order_id}': not found."
            )
        self._orders[order.order_id] = order
        return order

    def remove(self, order_id: str) -> Order:
        """Remove an order from the book entirely.

        Args:
            order_id: The TITAN internal order ID.

        Raises:
            OrderNotFoundError: If the order ID is not found.
        """
        order = self._orders.pop(order_id, None)
        if order is None:
            raise OrderNotFoundError(f"Cannot remove order '{order_id}': not found.")
        return order

    # ------------------------------------------------------------------
    # Filtered queries
    # ------------------------------------------------------------------

    def orders_since(self, since: datetime) -> Sequence[Order]:
        return tuple(o for o in self._orders.values() if o.created_at >= since)

    def orders_by_symbol(self, symbol: str) -> Sequence[Order]:
        return tuple(o for o in self._orders.values() if o.symbol == symbol)

    def orders_by_state(self, state: OrderState) -> Sequence[Order]:
        return tuple(o for o in self._orders.values() if o.state == state)

    @property
    def count(self) -> int:
        return len(self._orders)

    def clear(self) -> None:
        self._orders.clear()
