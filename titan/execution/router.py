from titan.brokers.broker import Broker
from titan.brokers.exceptions import ConnectionError as BrokerConnectionError
from titan.brokers.models import (
    BrokerType,
    OrderRequest as BrokerOrderRequest,
    OrderStatus as BrokerOrderStatus,
)
from titan.execution.exceptions import BrokerUnavailableError, RouteNotFoundError
from titan.execution.models import (
    ExecutionAction,
    ExecutionReport,
    OrderState,
)
from titan.execution.order import Order


class OrderRouter:
    """Routes orders to broker adapters and normalises responses.

    The router is the bridge between the TITAN OMS and the broker
    abstraction layer. It knows about Broker interfaces but contains
    NO broker-specific logic.
    """

    # Mapping of broker OrderStatus values to TITAN OrderState values.
    _STATUS_MAP: dict[BrokerOrderStatus, OrderState] = {
        BrokerOrderStatus.PENDING: OrderState.SUBMITTED,
        BrokerOrderStatus.OPEN: OrderState.ACKNOWLEDGED,
        BrokerOrderStatus.PARTIALLY_FILLED: OrderState.PARTIALLY_FILLED,
        BrokerOrderStatus.FILLED: OrderState.FILLED,
        BrokerOrderStatus.CANCELLED: OrderState.CANCELLED,
        BrokerOrderStatus.REJECTED: OrderState.REJECTED,
        BrokerOrderStatus.EXPIRED: OrderState.EXPIRED,
    }

    def __init__(self) -> None:
        self._brokers: dict[BrokerType, Broker] = {}

    def register_broker(self, broker_type: BrokerType, broker: Broker) -> None:
        """Register a connected broker instance for routing."""
        self._brokers[broker_type] = broker

    def unregister_broker(self, broker_type: BrokerType) -> None:
        self._brokers.pop(broker_type, None)

    def registered_brokers(self) -> list[BrokerType]:
        return list(self._brokers.keys())

    def _get_broker(self, broker_type: BrokerType) -> Broker:
        broker = self._brokers.get(broker_type)
        if broker is None:
            raise RouteNotFoundError(f"No broker registered for '{broker_type.value}'.")
        return broker

    def route(self, order: Order) -> ExecutionReport:
        """Route a single order to its target broker.

        Args:
            order: The order to route. Must have state VALIDATED.

        Returns:
            An ExecutionReport describing the routing outcome.

        Raises:
            RouteNotFoundError: If no broker is registered for the order.
            BrokerUnavailableError: If the broker is not connected.
        """
        broker_type = order.route.broker_type if order.route else BrokerType.ANGEL_ONE

        broker = self._get_broker(broker_type)

        if not broker.is_connected():
            raise BrokerUnavailableError(
                f"Broker '{broker_type.value}' is not connected."
            )

        broker_request = BrokerOrderRequest(
            symbol=order.symbol,
            exchange=order.exchange,
            side=order.side,
            order_type=order.order_type,
            quantity=order.quantity,
            product=order.product,
            validity=order.validity,
            price=order.price,
            trigger_price=order.trigger_price,
            disclose_quantity=order.disclose_quantity,
            tag=order.tag,
        )

        try:
            broker_response = broker.place_order(broker_request)
        except BrokerConnectionError as e:
            raise BrokerUnavailableError(
                f"Broker '{broker_type.value}' connection failed: {e}"
            ) from e

        state = self._STATUS_MAP.get(broker_response.status, OrderState.ACKNOWLEDGED)

        return ExecutionReport(
            request_id=order.request_id,
            order_id=order.order_id,
            success=True,
            action=ExecutionAction.ROUTE,
            state=state,
            broker_order_id=broker_response.broker_order_id,
            message=broker_response.message,
        )

    @staticmethod
    def normalise_status(broker_status: BrokerOrderStatus) -> OrderState:
        """Convert a broker OrderStatus to a TITAN OrderState.

        Args:
            broker_status: The broker-level order status.

        Returns:
            The corresponding TITAN OrderState.
        """
        return OrderRouter._STATUS_MAP.get(broker_status, OrderState.ACKNOWLEDGED)

    @staticmethod
    def build_request(order: Order) -> BrokerOrderRequest:
        """Build a broker-level OrderRequest from a TITAN Order."""
        return BrokerOrderRequest(
            symbol=order.symbol,
            exchange=order.exchange,
            side=order.side,
            order_type=order.order_type,
            quantity=order.quantity,
            product=order.product,
            validity=order.validity,
            price=order.price,
            trigger_price=order.trigger_price,
            disclose_quantity=order.disclose_quantity,
            tag=order.tag,
        )
