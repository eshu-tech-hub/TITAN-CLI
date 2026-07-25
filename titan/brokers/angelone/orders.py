from datetime import datetime
from typing import Any

from titan.brokers.angelone.exceptions import translate_error
from titan.brokers.angelone.mapper import (
    cancel_request_to_smartapi,
    modify_request_to_smartapi,
    order_from_smartapi,
    order_request_to_smartapi,
    order_response_from_smartapi,
)
from titan.brokers.models import (
    CancelOrderRequest,
    ModifyOrderRequest,
    Order,
    OrderRequest,
    OrderResponse,
)


class AngelOneOrderProvider:
    """Order management provider using the Angel One SmartAPI.

    Implements the OrderProvider interface defined in
    titan.brokers.broker.
    """

    def __init__(self, smart_connect: Any | None = None) -> None:
        self._smart_connect = smart_connect

    @property
    def smart_connect(self) -> Any | None:
        return self._smart_connect

    @smart_connect.setter
    def smart_connect(self, value: Any | None) -> None:
        self._smart_connect = value

    def place_order(self, request: OrderRequest) -> OrderResponse:
        """Place a new order via SmartAPI."""
        sc = self._require_client()
        payload = order_request_to_smartapi(request)

        try:
            response = sc.placeOrder(payload)
        except Exception as exc:
            raise translate_error(exc) from exc

        data = self._extract_data(response)
        return order_response_from_smartapi(data)

    def modify_order(self, request: ModifyOrderRequest) -> OrderResponse:
        """Modify an existing open order."""
        sc = self._require_client()
        payload = modify_request_to_smartapi(
            broker_order_id=request.broker_order_id,
            quantity=request.quantity,
            price=str(request.price) if request.price is not None else None,
            trigger_price=(
                str(request.trigger_price)
                if request.trigger_price is not None
                else None
            ),
            validity=request.validity.value if request.validity else None,
        )

        try:
            response = sc.modifyOrder(payload)
        except Exception as exc:
            raise translate_error(exc) from exc

        data = self._extract_data(response)
        return order_response_from_smartapi(data)

    def cancel_order(self, request: CancelOrderRequest) -> OrderResponse:
        """Cancel an existing open order."""
        sc = self._require_client()
        payload = cancel_request_to_smartapi(request.broker_order_id)

        try:
            response = sc.cancelOrder(payload)
        except Exception as exc:
            raise translate_error(exc) from exc

        data = self._extract_data(response)
        return order_response_from_smartapi(data)

    def order(self, broker_order_id: str) -> Order:
        """Fetch details of a single order by its broker-assigned ID."""
        orders = self.orders()
        for o in orders:
            if o.broker_order_id == broker_order_id:
                return o
        from titan.brokers.exceptions import OrderError

        raise OrderError(
            f"Order '{broker_order_id}' not found in Angel One order book."
        )

    def orders(
        self,
        symbol: str | None = None,
        since: datetime | None = None,
    ) -> list[Order]:
        """Fetch a list of orders, optionally filtered."""
        sc = self._require_client()

        try:
            response = sc.getOrderBook()
        except Exception as exc:
            raise translate_error(exc) from exc

        raw_orders = self._extract_data_list(response)
        result: list[Order] = []

        for item in raw_orders:
            titan_order = order_from_smartapi(item)
            if symbol and titan_order.symbol != symbol:
                continue
            if since and titan_order.placed_at and titan_order.placed_at < since:
                continue
            result.append(titan_order)

        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_client(self) -> Any:
        if self._smart_connect is None:
            from titan.brokers.exceptions import ConnectionError

            raise ConnectionError(
                "SmartAPI client is not available. Call connect() first."
            )
        return self._smart_connect

    @staticmethod
    def _extract_data(response: Any) -> dict[str, Any]:
        if isinstance(response, dict):
            data = response.get("data") or {}
            if isinstance(data, dict):
                return data
            if isinstance(data, list) and data:
                return dict(data[0]) if isinstance(data[0], dict) else {}
            return {}
        return {}

    @staticmethod
    def _extract_data_list(response: Any) -> list[dict[str, Any]]:
        if isinstance(response, dict):
            data = response.get("data") or []
            if isinstance(data, list):
                return [dict(d) for d in data if isinstance(d, dict)]
            return []
        return []
