import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from titan.brokers.broker import Broker
from titan.brokers.models import (
    AccountProfile,
    BrokerType,
    CancelOrderRequest,
    Candle,
    ConnectionStatus,
    Exchange,
    FundsInfo,
    Holding,
    MarginInfo,
    MarketDepth,
    ModifyOrderRequest,
    Order as BrokerOrder,
    OrderRequest as BrokerOrderRequest,
    OrderResponse,
    OrderSide,
    OrderStatus as BrokerOrderStatus,
    OrderType,
    Position,
    ProductType,
    Quote,
    Trade,
)
from titan.execution import (
    BrokerUnavailableError,
    ExecutionEngine,
    ExecutionError,
    ExecutionExplanation,
    ExecutionReport,
    ExecutionRequest,
    ExecutionResult,
    InvalidStateTransitionError,
    Order,
    OrderBook,
    OrderEvent,
    OrderNotFoundError,
    OrderRoute,
    OrderRouter,
    OrderState,
    OrderStateMachine,
    OrderValidationError,
    RouteNotFoundError,
)

# ===========================================================================
# Helpers
# ===========================================================================


class _MockBroker(Broker):
    """In-memory mock broker for testing the OMS."""

    _connected: bool = True
    _next_status: BrokerOrderStatus = BrokerOrderStatus.OPEN

    def connect(self) -> ConnectionStatus:
        self._connected = True
        return ConnectionStatus.CONNECTED

    def disconnect(self) -> ConnectionStatus:
        self._connected = False
        return ConnectionStatus.DISCONNECTED

    def is_connected(self) -> bool:
        return self._connected

    def set_next_status(self, status: BrokerOrderStatus) -> None:
        self._next_status = status

    def quote(self, symbol: str) -> Quote:
        return Quote(symbol=symbol, exchange=Exchange.NSE, last_price=Decimal("100.00"))

    def quotes(self, symbols: list[str]) -> dict[str, Quote]:
        return {s: self.quote(s) for s in symbols}

    def ltp(self, symbol: str) -> Decimal:
        return Decimal("100.00")

    def option_chain(self, symbol: str, expiry: str | None = None) -> list[Quote]:
        return [self.quote(symbol)]

    def market_depth(self, symbol: str, level: int = 5) -> MarketDepth:
        return MarketDepth(symbol=symbol, exchange=Exchange.NSE)

    def history(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime | None = None,
    ) -> list[Candle]:
        return []

    def intraday(self, symbol: str, interval: str = "1min") -> list[Candle]:
        return []

    def ohlcv(
        self, symbol: str, interval: str = "1day", limit: int = 100
    ) -> list[Candle]:
        return []

    def place_order(self, request: BrokerOrderRequest) -> OrderResponse:
        return OrderResponse(
            broker_order_id="BROKER-O1",
            status=self._next_status,
            filled_quantity=(
                request.quantity if self._next_status == BrokerOrderStatus.FILLED else 0
            ),
            average_price=(
                Decimal("100.00")
                if self._next_status == BrokerOrderStatus.FILLED
                else None
            ),
            message="Mock order placed",
        )

    def modify_order(self, request: ModifyOrderRequest) -> OrderResponse:
        return OrderResponse(
            broker_order_id=request.broker_order_id,
            status=BrokerOrderStatus.OPEN,
        )

    def cancel_order(self, request: CancelOrderRequest) -> OrderResponse:
        return OrderResponse(
            broker_order_id=request.broker_order_id,
            status=BrokerOrderStatus.CANCELLED,
        )

    def order(self, broker_order_id: str) -> BrokerOrder:
        return BrokerOrder(
            broker_order_id=broker_order_id,
            symbol="TEST",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            product=ProductType.DELIVERY,
            status=BrokerOrderStatus.OPEN,
            quantity=10,
        )

    def orders(
        self, symbol: str | None = None, since: datetime | None = None
    ) -> list[BrokerOrder]:
        return [self.order("O1")]

    def positions(self) -> list[Position]:
        return []

    def holdings(self) -> list[Holding]:
        return []

    def trades(
        self, symbol: str | None = None, since: datetime | None = None
    ) -> list[Trade]:
        return []

    def funds(self) -> FundsInfo:
        return FundsInfo()

    def margin(self) -> MarginInfo:
        return MarginInfo()

    def profile(self) -> AccountProfile:
        return AccountProfile()


def _make_request(**overrides: object) -> ExecutionRequest:
    defaults = {
        "request_id": str(uuid.uuid4()),
        "symbol": "RELIANCE",
        "exchange": Exchange.NSE,
        "side": OrderSide.BUY,
        "order_type": OrderType.MARKET,
        "quantity": 10,
    }
    merged = {**defaults, **overrides}
    return ExecutionRequest(**merged)  # type: ignore[arg-type]


def _make_order(**overrides: object) -> Order:
    defaults = {
        "order_id": str(uuid.uuid4()),
        "symbol": "RELIANCE",
        "exchange": Exchange.NSE,
        "side": OrderSide.BUY,
        "order_type": OrderType.MARKET,
        "quantity": 10,
    }
    merged = {**defaults, **overrides}
    return Order(**merged)  # type: ignore[arg-type]


# ===========================================================================
# Enum Tests
# ===========================================================================


class TestOrderState:
    def test_values(self) -> None:
        assert OrderState.NEW.value == "new"
        assert OrderState.VALIDATED.value == "validated"
        assert OrderState.SUBMITTED.value == "submitted"
        assert OrderState.ACKNOWLEDGED.value == "acknowledged"
        assert OrderState.PARTIALLY_FILLED.value == "partially_filled"
        assert OrderState.FILLED.value == "filled"
        assert OrderState.REJECTED.value == "rejected"
        assert OrderState.CANCELLED.value == "cancelled"
        assert OrderState.EXPIRED.value == "expired"
        assert OrderState.MODIFIED.value == "modified"
        assert OrderState.FAILED.value == "failed"


# ===========================================================================
# Model Tests
# ===========================================================================


class TestOrderEvent:
    def test_defaults(self) -> None:
        event = OrderEvent()
        assert event.from_state is None
        assert event.to_state == OrderState.NEW
        assert event.reason == ""
        assert event.error is None

    def test_full_init(self) -> None:
        now = datetime.now(timezone.utc)
        event = OrderEvent(
            timestamp=now,
            from_state=OrderState.NEW,
            to_state=OrderState.VALIDATED,
            reason="Validation passed",
            broker_order_id="BROKER-1",
        )
        assert event.from_state == OrderState.NEW
        assert event.to_state == OrderState.VALIDATED
        assert event.broker_order_id == "BROKER-1"


class TestOrderRoute:
    def test_defaults(self) -> None:
        route = OrderRoute(broker_type=BrokerType.ANGEL_ONE)
        assert route.broker_order_id is None
        assert route.status == OrderState.NEW

    def test_full_init(self) -> None:
        route = OrderRoute(
            broker_type=BrokerType.ZERODHA,
            broker_order_id="Z-123",
            status=OrderState.ACKNOWLEDGED,
        )
        assert route.broker_type == BrokerType.ZERODHA
        assert route.broker_order_id == "Z-123"


class TestExecutionRequest:
    def test_required_fields(self) -> None:
        req = _make_request()
        assert req.symbol == "RELIANCE"
        assert req.price is None
        assert req.tag == ""

    def test_limit_order(self) -> None:
        req = _make_request(
            order_type=OrderType.LIMIT,
            price=Decimal("2500.50"),
            tag="my-tag",
        )
        assert req.order_type == OrderType.LIMIT
        assert req.price == Decimal("2500.50")
        assert req.tag == "my-tag"


class TestExecutionReport:
    def test_defaults(self) -> None:
        report = ExecutionReport(
            request_id="R1",
            order_id="O1",
            success=True,
            action="route",
            state=OrderState.ACKNOWLEDGED,
        )
        assert report.errors == ()

    def test_with_errors(self) -> None:
        report = ExecutionReport(
            request_id="R1",
            order_id="O1",
            success=False,
            action="block",
            state=OrderState.FAILED,
            errors=("Broker unavailable",),
        )
        assert "Broker unavailable" in report.errors


class TestExecutionResult:
    def test_defaults(self) -> None:
        result = ExecutionResult(request_id="R1", success=True)
        assert result.order is None
        assert result.reports == ()
        assert result.errors == ()
        assert result.execution_time_ms == 0.0


class TestExecutionExplanation:
    def test_defaults(self) -> None:
        exp = ExecutionExplanation()
        assert exp.summary == ""
        assert exp.validation_issues == ()


# ===========================================================================
# Exception Tests
# ===========================================================================


class TestExceptions:
    def test_execution_error(self) -> None:
        with pytest.raises(ExecutionError):
            raise ExecutionError("test")

    def test_order_not_found(self) -> None:
        with pytest.raises(OrderNotFoundError):
            raise OrderNotFoundError("not found")

    def test_invalid_state_transition(self) -> None:
        with pytest.raises(InvalidStateTransitionError):
            raise InvalidStateTransitionError("invalid")

    def test_order_validation_error(self) -> None:
        with pytest.raises(OrderValidationError):
            raise OrderValidationError("invalid")

    def test_broker_unavailable(self) -> None:
        with pytest.raises(BrokerUnavailableError):
            raise BrokerUnavailableError("unavailable")

    def test_route_not_found(self) -> None:
        with pytest.raises(RouteNotFoundError):
            raise RouteNotFoundError("no route")

    def test_hierarchy(self) -> None:
        assert issubclass(OrderNotFoundError, ExecutionError)
        assert issubclass(InvalidStateTransitionError, ExecutionError)
        assert issubclass(OrderValidationError, ExecutionError)
        assert issubclass(BrokerUnavailableError, ExecutionError)
        assert issubclass(RouteNotFoundError, ExecutionError)


# ===========================================================================
# OrderStateMachine Tests
# ===========================================================================


class TestOrderStateMachine:
    def test_initial_state(self) -> None:
        sm = OrderStateMachine()
        assert sm.current_state == OrderState.NEW
        assert sm.is_terminal is False

    def test_valid_transition(self) -> None:
        sm = OrderStateMachine()
        sm.transition(OrderState.VALIDATED, reason="Validation passed")
        assert sm.current_state == OrderState.VALIDATED
        assert len(sm.events) == 2

    def test_invalid_transition_raises(self) -> None:
        sm = OrderStateMachine()
        with pytest.raises(InvalidStateTransitionError):
            sm.transition(OrderState.FILLED, reason="Skip ahead")

    def test_full_lifecycle(self) -> None:
        sm = OrderStateMachine()
        sm.transition(OrderState.VALIDATED, reason="OK")
        sm.transition(OrderState.SUBMITTED, reason="Sent")
        sm.transition(
            OrderState.ACKNOWLEDGED, reason="Broker ack", broker_order_id="B1"
        )
        sm.transition(OrderState.PARTIALLY_FILLED, reason="Partial fill")
        sm.transition(OrderState.FILLED, reason="Fully filled")
        assert sm.current_state == OrderState.FILLED
        assert sm.is_terminal is True
        assert len(sm.events) == 6

    def test_modified_lifecycle(self) -> None:
        sm = OrderStateMachine()
        sm.transition(OrderState.VALIDATED, reason="OK")
        sm.transition(OrderState.SUBMITTED, reason="Sent")
        sm.transition(OrderState.ACKNOWLEDGED, reason="Ack")
        sm.transition(OrderState.MODIFIED, reason="Price change")
        assert sm.current_state == OrderState.MODIFIED
        sm.transition(OrderState.ACKNOWLEDGED, reason="Modification ack")
        assert sm.current_state == OrderState.ACKNOWLEDGED

    def test_rejected_from_validated(self) -> None:
        sm = OrderStateMachine()
        sm.transition(OrderState.VALIDATED, reason="OK")
        sm.transition(OrderState.REJECTED, reason="Insufficient margin")
        assert sm.current_state == OrderState.REJECTED
        assert sm.is_terminal is True

    def test_failed_from_submitted(self) -> None:
        sm = OrderStateMachine()
        sm.transition(OrderState.VALIDATED, reason="OK")
        sm.transition(OrderState.SUBMITTED, reason="Sent")
        sm.transition(OrderState.FAILED, reason="System error")
        assert sm.current_state == OrderState.FAILED

    def test_terminal_has_no_transitions(self) -> None:
        sm = OrderStateMachine()
        sm.transition(OrderState.VALIDATED, reason="OK")
        sm.transition(OrderState.REJECTED, reason="No")
        assert sm.is_terminal is True
        with pytest.raises(InvalidStateTransitionError):
            sm.transition(OrderState.NEW, reason="Cannot go back")

    def test_is_valid_transition_static(self) -> None:
        assert (
            OrderStateMachine.is_valid_transition(OrderState.NEW, OrderState.VALIDATED)
            is True
        )
        assert (
            OrderStateMachine.is_valid_transition(OrderState.NEW, OrderState.FILLED)
            is False
        )
        assert (
            OrderStateMachine.is_valid_transition(OrderState.FILLED, OrderState.NEW)
            is False
        )

    def test_validate_transition_instance(self) -> None:
        sm = OrderStateMachine()
        assert sm.validate_transition(OrderState.VALIDATED) is True
        assert sm.validate_transition(OrderState.FILLED) is False

    def test_reset(self) -> None:
        sm = OrderStateMachine()
        sm.transition(OrderState.VALIDATED, reason="OK")
        sm.reset()
        assert sm.current_state == OrderState.NEW
        assert len(sm.events) == 1

    def test_partially_filled_self_transition(self) -> None:
        sm = OrderStateMachine()
        sm.transition(OrderState.VALIDATED, reason="OK")
        sm.transition(OrderState.SUBMITTED, reason="Sent")
        sm.transition(OrderState.ACKNOWLEDGED, reason="Ack")
        sm.transition(OrderState.PARTIALLY_FILLED, reason="Fill 5")
        assert sm.current_state == OrderState.PARTIALLY_FILLED
        sm.transition(OrderState.PARTIALLY_FILLED, reason="Fill 3 more")
        assert sm.current_state == OrderState.PARTIALLY_FILLED
        sm.transition(OrderState.FILLED, reason="Fill rest")
        assert sm.current_state == OrderState.FILLED

    def test_events_record_correctly(self) -> None:
        sm = OrderStateMachine()
        sm.transition(OrderState.VALIDATED, reason="OK", broker_order_id="B1")
        events = sm.events
        assert len(events) == 2
        assert events[0].to_state == OrderState.NEW
        assert events[1].from_state == OrderState.NEW
        assert events[1].to_state == OrderState.VALIDATED
        assert events[1].broker_order_id == "B1"


# ===========================================================================
# Order Domain Model Tests
# ===========================================================================


class TestOrderModel:
    def test_defaults(self) -> None:
        order = _make_order()
        assert order.state == OrderState.NEW
        assert order.filled_quantity == 0
        assert order.broker_order_id is None

    def test_active_state(self) -> None:
        assert _make_order(state=OrderState.NEW).is_active is True
        assert _make_order(state=OrderState.VALIDATED).is_active is True
        assert _make_order(state=OrderState.SUBMITTED).is_active is True
        assert _make_order(state=OrderState.ACKNOWLEDGED).is_active is True
        assert _make_order(state=OrderState.FILLED).is_active is False
        assert _make_order(state=OrderState.REJECTED).is_active is False
        assert _make_order(state=OrderState.CANCELLED).is_active is False

    def test_terminal_state(self) -> None:
        assert _make_order(state=OrderState.FILLED).is_terminal is True
        assert _make_order(state=OrderState.REJECTED).is_terminal is True
        assert _make_order(state=OrderState.CANCELLED).is_terminal is True
        assert _make_order(state=OrderState.EXPIRED).is_terminal is True
        assert _make_order(state=OrderState.FAILED).is_terminal is True
        assert _make_order(state=OrderState.NEW).is_terminal is False

    def test_with_state_creates_new_instance(self) -> None:
        order = _make_order()
        updated = order.with_state(OrderState.VALIDATED, reason="Passed")
        assert updated.state == OrderState.VALIDATED
        assert order.state == OrderState.NEW
        assert updated is not order

    def test_with_state_adds_event(self) -> None:
        order = _make_order()
        updated = order.with_state(OrderState.VALIDATED, reason="Passed")
        assert len(updated.events) == 1
        assert updated.events[0].from_state == OrderState.NEW
        assert updated.events[0].to_state == OrderState.VALIDATED

    def test_with_state_preserves_fields(self) -> None:
        order = _make_order(symbol="INFY", quantity=50)
        updated = order.with_state(OrderState.VALIDATED)
        assert updated.symbol == "INFY"
        assert updated.quantity == 50
        assert updated.order_id == order.order_id

    def test_with_state_broker_order_id(self) -> None:
        order = _make_order()
        updated = order.with_state(
            OrderState.ACKNOWLEDGED,
            broker_order_id="BROKER-123",
        )
        assert updated.broker_order_id == "BROKER-123"

    def test_with_state_fill_details(self) -> None:
        order = _make_order(quantity=10)
        updated = order.with_state(
            OrderState.PARTIALLY_FILLED,
            reason="Partial",
            filled_quantity=5,
            pending_quantity=5,
            average_price=Decimal("100.00"),
        )
        assert updated.filled_quantity == 5
        assert updated.pending_quantity == 5
        assert updated.average_price == Decimal("100.00")

    def test_with_state_route(self) -> None:
        route = OrderRoute(broker_type=BrokerType.ANGEL_ONE)
        order = _make_order()
        updated = order.with_state(OrderState.SUBMITTED, route=route)
        assert updated.route is not None
        assert updated.route.broker_type == BrokerType.ANGEL_ONE

    def test_serialization(self) -> None:
        order = _make_order(symbol="RELIANCE", quantity=10)
        data = {
            "order_id": order.order_id,
            "symbol": order.symbol,
            "state": order.state.value,
        }
        payload = json.dumps(data)
        assert json.loads(payload)["symbol"] == "RELIANCE"
        assert json.loads(payload)["state"] == "new"


# ===========================================================================
# OrderBook Tests
# ===========================================================================


class TestOrderBook:
    def test_add_and_lookup(self) -> None:
        book = OrderBook()
        order = _make_order()
        book.add(order)
        found = book.lookup(order.order_id)
        assert found.order_id == order.order_id

    def test_lookup_not_found_raises(self) -> None:
        book = OrderBook()
        with pytest.raises(OrderNotFoundError):
            book.lookup("non-existent")

    def test_get_returns_none(self) -> None:
        book = OrderBook()
        assert book.get("non-existent") is None

    def test_add_duplicate_raises(self) -> None:
        book = OrderBook()
        order = _make_order()
        book.add(order)
        with pytest.raises(ValueError, match="already exists"):
            book.add(order)

    def test_update(self) -> None:
        book = OrderBook()
        order = _make_order()
        book.add(order)
        updated = order.with_state(OrderState.VALIDATED)
        book.update(updated)
        assert book.lookup(order.order_id).state == OrderState.VALIDATED

    def test_update_not_found_raises(self) -> None:
        book = OrderBook()
        order = _make_order()
        with pytest.raises(OrderNotFoundError):
            book.update(order)

    def test_remove(self) -> None:
        book = OrderBook()
        order = _make_order()
        book.add(order)
        removed = book.remove(order.order_id)
        assert removed.order_id == order.order_id
        assert book.get(order.order_id) is None

    def test_remove_not_found_raises(self) -> None:
        book = OrderBook()
        with pytest.raises(OrderNotFoundError):
            book.remove("non-existent")

    def test_open_orders(self) -> None:
        book = OrderBook()
        book.add(_make_order(order_id="1", state=OrderState.NEW))
        book.add(_make_order(order_id="2", state=OrderState.VALIDATED))
        book.add(_make_order(order_id="3", state=OrderState.FILLED))
        book.add(_make_order(order_id="4", state=OrderState.CANCELLED))
        assert len(book.open_orders) == 2
        assert {o.order_id for o in book.open_orders} == {"1", "2"}

    def test_filled_orders(self) -> None:
        book = OrderBook()
        book.add(_make_order(order_id="1", state=OrderState.FILLED))
        book.add(_make_order(order_id="2", state=OrderState.NEW))
        assert len(book.filled_orders) == 1
        assert book.filled_orders[0].order_id == "1"

    def test_cancelled_orders(self) -> None:
        book = OrderBook()
        book.add(_make_order(order_id="1", state=OrderState.CANCELLED))
        book.add(_make_order(order_id="2", state=OrderState.NEW))
        assert len(book.cancelled_orders) == 1

    def test_active_orders_alias(self) -> None:
        book = OrderBook()
        book.add(_make_order(order_id="1", state=OrderState.NEW))
        book.add(_make_order(order_id="2", state=OrderState.FILLED))
        assert len(book.active_orders) == 1
        assert book.active_orders[0].order_id == "1"

    def test_all_orders(self) -> None:
        book = OrderBook()
        book.add(_make_order(order_id="1"))
        book.add(_make_order(order_id="2"))
        assert len(book.all_orders) == 2

    def test_orders_by_symbol(self) -> None:
        book = OrderBook()
        book.add(_make_order(order_id="1", symbol="RELIANCE"))
        book.add(_make_order(order_id="2", symbol="INFY"))
        book.add(_make_order(order_id="3", symbol="RELIANCE"))
        assert len(book.orders_by_symbol("RELIANCE")) == 2

    def test_orders_by_state(self) -> None:
        book = OrderBook()
        book.add(_make_order(order_id="1", state=OrderState.FILLED))
        book.add(_make_order(order_id="2", state=OrderState.FILLED))
        book.add(_make_order(order_id="3", state=OrderState.NEW))
        assert len(book.orders_by_state(OrderState.FILLED)) == 2

    def test_count(self) -> None:
        book = OrderBook()
        assert book.count == 0
        book.add(_make_order())
        assert book.count == 1

    def test_clear(self) -> None:
        book = OrderBook()
        book.add(_make_order())
        book.clear()
        assert book.count == 0


# ===========================================================================
# OrderRouter Tests
# ===========================================================================


class TestOrderRouter:
    def test_register_and_route(self) -> None:
        router = OrderRouter()
        broker = _MockBroker()
        router.register_broker(BrokerType.ANGEL_ONE, broker)
        assert BrokerType.ANGEL_ONE in router.registered_brokers()

    def test_unregister(self) -> None:
        router = OrderRouter()
        broker = _MockBroker()
        router.register_broker(BrokerType.ANGEL_ONE, broker)
        router.unregister_broker(BrokerType.ANGEL_ONE)
        assert router.registered_brokers() == []

    def test_route_order(self) -> None:
        router = OrderRouter()
        broker = _MockBroker()
        router.register_broker(BrokerType.ANGEL_ONE, broker)
        order = _make_order(
            state=OrderState.VALIDATED,
            route=OrderRoute(broker_type=BrokerType.ANGEL_ONE),
        )
        report = router.route(order)
        assert report.success is True
        assert report.state == OrderState.ACKNOWLEDGED
        assert report.broker_order_id == "BROKER-O1"

    def test_route_no_broker_raises(self) -> None:
        router = OrderRouter()
        order = _make_order()
        with pytest.raises(RouteNotFoundError):
            router.route(order)

    def test_route_disconnected_broker_raises(self) -> None:
        router = OrderRouter()
        broker = _MockBroker()
        broker.disconnect()
        router.register_broker(BrokerType.ANGEL_ONE, broker)
        order = _make_order(
            state=OrderState.VALIDATED,
            route=OrderRoute(broker_type=BrokerType.ANGEL_ONE),
        )
        with pytest.raises(BrokerUnavailableError):
            router.route(order)

    def test_route_filled_order(self) -> None:
        router = OrderRouter()
        broker = _MockBroker()
        broker.set_next_status(BrokerOrderStatus.FILLED)
        router.register_broker(BrokerType.ANGEL_ONE, broker)
        order = _make_order(
            state=OrderState.VALIDATED,
            route=OrderRoute(broker_type=BrokerType.ANGEL_ONE),
        )
        report = router.route(order)
        assert report.success is True
        assert report.state == OrderState.FILLED

    def test_route_rejected_order(self) -> None:
        router = OrderRouter()
        broker = _MockBroker()
        broker.set_next_status(BrokerOrderStatus.REJECTED)
        router.register_broker(BrokerType.ANGEL_ONE, broker)
        order = _make_order(
            state=OrderState.VALIDATED,
            route=OrderRoute(broker_type=BrokerType.ANGEL_ONE),
        )
        report = router.route(order)
        assert report.state == OrderState.REJECTED

    def test_normalise_status(self) -> None:
        assert (
            OrderRouter.normalise_status(BrokerOrderStatus.OPEN)
            == OrderState.ACKNOWLEDGED
        )
        assert (
            OrderRouter.normalise_status(BrokerOrderStatus.FILLED) == OrderState.FILLED
        )
        assert (
            OrderRouter.normalise_status(BrokerOrderStatus.REJECTED)
            == OrderState.REJECTED
        )
        assert (
            OrderRouter.normalise_status(BrokerOrderStatus.PENDING)
            == OrderState.SUBMITTED
        )

    def test_build_request(self) -> None:
        order = _make_order(price=Decimal("2500.00"))
        broker_req = OrderRouter.build_request(order)
        assert broker_req.symbol == "RELIANCE"
        assert broker_req.price == Decimal("2500.00")


# ===========================================================================
# ExecutionEngine Tests
# ===========================================================================


class TestExecutionEngine:
    def test_execute_success(self) -> None:
        book = OrderBook()
        router = OrderRouter()
        broker = _MockBroker()
        router.register_broker(BrokerType.ANGEL_ONE, broker)
        engine = ExecutionEngine(order_book=book, router=router)
        req = _make_request()
        result = engine.execute(req)
        assert result.success is True
        assert result.order is not None
        assert result.order.state == OrderState.ACKNOWLEDGED
        assert result.errors == ()

    def test_execute_and_fill(self) -> None:
        book = OrderBook()
        router = OrderRouter()
        broker = _MockBroker()
        broker.set_next_status(BrokerOrderStatus.FILLED)
        router.register_broker(BrokerType.ANGEL_ONE, broker)
        engine = ExecutionEngine(order_book=book, router=router)
        req = _make_request()
        result = engine.execute(req)
        assert result.success is True
        assert result.order is not None
        assert result.order.state == OrderState.FILLED
        assert result.order.filled_quantity == 10

    def test_execute_invalid_request(self) -> None:
        book = OrderBook()
        router = OrderRouter()
        engine = ExecutionEngine(order_book=book, router=router)
        req = _make_request(quantity=0)
        result = engine.execute(req)
        assert result.success is False
        assert len(result.errors) > 0
        assert "greater than zero" in result.errors[0]

    def test_execute_no_broker_registered(self) -> None:
        book = OrderBook()
        router = OrderRouter()
        engine = ExecutionEngine(order_book=book, router=router)
        req = _make_request()
        result = engine.execute(req)
        assert result.success is False
        assert "No connected broker" in result.errors[0]

    def test_execute_creates_order_in_book(self) -> None:
        book = OrderBook()
        router = OrderRouter()
        broker = _MockBroker()
        router.register_broker(BrokerType.ANGEL_ONE, broker)
        engine = ExecutionEngine(order_book=book, router=router)
        req = _make_request()
        result = engine.execute(req)
        assert result.order is not None
        found = book.lookup(result.order.order_id)
        assert found.order_id == result.order.order_id

    def test_validate_request_valid(self) -> None:
        engine = ExecutionEngine(order_book=OrderBook(), router=OrderRouter())
        req = _make_request()
        errors = engine.validate_request(req)
        assert errors == []

    def test_validate_request_missing_symbol(self) -> None:
        engine = ExecutionEngine(order_book=OrderBook(), router=OrderRouter())
        req = _make_request(symbol="")
        errors = engine.validate_request(req)
        assert any("symbol" in e.lower() for e in errors)

    def test_validate_request_limit_price(self) -> None:
        engine = ExecutionEngine(order_book=OrderBook(), router=OrderRouter())
        req = _make_request(order_type=OrderType.LIMIT)
        errors = engine.validate_request(req)
        assert any("price" in e.lower() for e in errors)

    def test_validate_request_stop_loss_price(self) -> None:
        engine = ExecutionEngine(order_book=OrderBook(), router=OrderRouter())
        req = _make_request(order_type=OrderType.STOP_LOSS)
        errors = engine.validate_request(req)
        assert any("trigger" in e.lower() for e in errors)

    def test_validate_request_disclose_exceeds_quantity(self) -> None:
        engine = ExecutionEngine(order_book=OrderBook(), router=OrderRouter())
        req = _make_request(disclose_quantity=20, quantity=10)
        errors = engine.validate_request(req)
        assert any("exceed" in e.lower() for e in errors)

    def test_validate_request_negative_disclose(self) -> None:
        engine = ExecutionEngine(order_book=OrderBook(), router=OrderRouter())
        req = _make_request(disclose_quantity=-1)
        errors = engine.validate_request(req)
        assert any("negative" in e.lower() for e in errors)

    def test_engine_properties(self) -> None:
        book = OrderBook()
        router = OrderRouter()
        engine = ExecutionEngine(order_book=book, router=router)
        assert engine.order_book is book
        assert engine.router is router


# ===========================================================================
# Audit Trail Tests
# ===========================================================================


class TestAuditTrail:
    def test_order_events_recorded(self) -> None:
        book = OrderBook()
        router = OrderRouter()
        broker = _MockBroker()
        router.register_broker(BrokerType.ANGEL_ONE, broker)
        engine = ExecutionEngine(order_book=book, router=router)
        req = _make_request()
        result = engine.execute(req)
        assert result.order is not None
        assert (
            len(result.order.events) >= 3
        )  # NEW -> VALIDATED -> SUBMITTED -> ACKNOWLEDGED

    def test_events_contain_reasons(self) -> None:
        order = _make_order()
        updated = order.with_state(OrderState.VALIDATED, reason="Passed validation")
        assert updated.events[0].reason == "Passed validation"

    def test_failure_records_error(self) -> None:
        book = OrderBook()
        router = OrderRouter()
        engine = ExecutionEngine(order_book=book, router=router)
        req = _make_request()
        result = engine.execute(req)
        assert result.order is not None
        failure_events = [e for e in result.order.events if e.error is not None]
        assert len(failure_events) > 0


# ===========================================================================
# Multiple Orders Tests
# ===========================================================================


class TestMultipleOrders:
    def test_multiple_orders_in_book(self) -> None:
        book = OrderBook()
        router = OrderRouter()
        broker = _MockBroker()
        router.register_broker(BrokerType.ANGEL_ONE, broker)
        engine = ExecutionEngine(order_book=book, router=router)

        req1 = _make_request(symbol="RELIANCE")
        req2 = _make_request(symbol="INFY")
        r1 = engine.execute(req1)
        r2 = engine.execute(req2)
        assert r1.success is True
        assert r2.success is True
        assert book.count == 2

    def test_orders_by_symbol_filter(self) -> None:
        book = OrderBook()
        router = OrderRouter()
        broker = _MockBroker()
        router.register_broker(BrokerType.ANGEL_ONE, broker)
        engine = ExecutionEngine(order_book=book, router=router)

        engine.execute(_make_request(symbol="RELIANCE"))
        engine.execute(_make_request(symbol="RELIANCE"))
        engine.execute(_make_request(symbol="INFY"))
        assert len(book.orders_by_symbol("RELIANCE")) == 2
        assert len(book.orders_by_symbol("INFY")) == 1


# ===========================================================================
# Failure Handling Tests
# ===========================================================================


class TestFailureHandling:
    def test_quantity_zero(self) -> None:
        engine = ExecutionEngine(order_book=OrderBook(), router=OrderRouter())
        req = _make_request(quantity=0)
        result = engine.execute(req)
        assert result.success is False

    def test_empty_request_id(self) -> None:
        engine = ExecutionEngine(order_book=OrderBook(), router=OrderRouter())
        req = _make_request(request_id="")
        result = engine.execute(req)
        assert result.success is False
        assert any("Request ID" in e for e in result.errors)

    def test_execution_time_measured(self) -> None:
        engine = ExecutionEngine(order_book=OrderBook(), router=OrderRouter())
        req = _make_request(quantity=0)
        result = engine.execute(req)
        assert result.execution_time_ms >= 0
