import json
from abc import ABC
from datetime import datetime
from decimal import Decimal

import pytest

from titan.brokers import (
    AccountProfile,
    AccountProvider,
    AuthenticationError,
    Broker,
    BrokerError,
    BrokerFactory,
    BrokerType,
    CancelOrderRequest,
    Candle,
    ConnectionError,
    ConnectionStatus,
    Exchange,
    FundsInfo,
    HistoricalDataProvider,
    Holding,
    InstrumentType,
    MarginInfo,
    MarketDataError,
    MarketDataProvider,
    MarketDepth,
    MarketDepthLevel,
    ModifyOrderRequest,
    Order,
    OrderError,
    OrderProvider,
    OrderRequest,
    OrderResponse,
    OrderSide,
    OrderStatus,
    OrderType,
    PortfolioProvider,
    Position,
    ProductType,
    Quote,
    Trade,
    ValidationError,
    Validity,
)

# ===========================================================================
# Enum Tests
# ===========================================================================


class TestBrokerType:
    def test_values(self) -> None:
        assert BrokerType.ANGEL_ONE.value == "angel_one"
        assert BrokerType.ZERODHA.value == "zerodha"
        assert BrokerType.DHAN.value == "dhan"
        assert BrokerType.UPSTOX.value == "upstox"
        assert BrokerType.INTERACTIVE_BROKERS.value == "interactive_brokers"
        assert BrokerType.ALPACA.value == "alpaca"
        assert BrokerType.BINANCE.value == "binance"


class TestConnectionStatus:
    def test_values(self) -> None:
        assert ConnectionStatus.CONNECTED.value == "connected"
        assert ConnectionStatus.DISCONNECTED.value == "disconnected"
        assert ConnectionStatus.CONNECTING.value == "connecting"
        assert ConnectionStatus.RECONNECTING.value == "reconnecting"
        assert ConnectionStatus.ERROR.value == "error"


class TestOrderStatus:
    def test_values(self) -> None:
        assert OrderStatus.OPEN.value == "open"
        assert OrderStatus.FILLED.value == "filled"
        assert OrderStatus.REJECTED.value == "rejected"


class TestOrderSide:
    def test_values(self) -> None:
        assert OrderSide.BUY.value == "buy"
        assert OrderSide.SELL.value == "sell"


class TestOrderType:
    def test_values(self) -> None:
        assert OrderType.MARKET.value == "market"
        assert OrderType.LIMIT.value == "limit"
        assert OrderType.STOP_LOSS.value == "stop_loss"


class TestProductType:
    def test_values(self) -> None:
        assert ProductType.DELIVERY.value == "delivery"
        assert ProductType.OPTIONS.value == "options"


class TestValidity:
    def test_values(self) -> None:
        assert Validity.DAY.value == "day"
        assert Validity.GTC.value == "gtc"


class TestInstrumentType:
    def test_values(self) -> None:
        assert InstrumentType.EQUITY.value == "equity"
        assert InstrumentType.FUTURES.value == "futures"


class TestExchange:
    def test_values(self) -> None:
        assert Exchange.NSE.value == "nse"
        assert Exchange.BSE.value == "bse"
        assert Exchange.NFO.value == "nfo"


# ===========================================================================
# Model Tests
# ===========================================================================


class TestOrderRequest:
    def test_required_fields(self) -> None:
        req = OrderRequest(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        assert req.symbol == "RELIANCE"
        assert req.price is None
        assert req.tag == ""

    def test_limit_order(self) -> None:
        req = OrderRequest(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=10,
            price=Decimal("2500.50"),
            tag="my-tag",
        )
        assert req.price == Decimal("2500.50")
        assert req.tag == "my-tag"

    def test_stop_loss_order(self) -> None:
        req = OrderRequest(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.SELL,
            order_type=OrderType.STOP_LOSS,
            quantity=10,
            price=Decimal("2400.00"),
            trigger_price=Decimal("2450.00"),
        )
        assert req.trigger_price == Decimal("2450.00")


class TestOrderResponse:
    def test_required_fields(self) -> None:
        resp = OrderResponse(
            broker_order_id="ABC123",
            status=OrderStatus.OPEN,
        )
        assert resp.broker_order_id == "ABC123"
        assert resp.filled_quantity == 0
        assert resp.message == ""

    def test_filled_response(self) -> None:
        resp = OrderResponse(
            broker_order_id="ABC123",
            status=OrderStatus.FILLED,
            filled_quantity=10,
            average_price=Decimal("2500.00"),
            message="Order filled successfully",
        )
        assert resp.average_price == Decimal("2500.00")

    def test_serialization(self) -> None:
        resp = OrderResponse(
            broker_order_id="ABC123",
            status=OrderStatus.OPEN,
        )
        data = {
            "broker_order_id": resp.broker_order_id,
            "status": resp.status.value,
        }
        json_str = json.dumps(data)
        assert json.loads(json_str)["status"] == "open"


class TestModifyOrderRequest:
    def test_required_fields(self) -> None:
        req = ModifyOrderRequest(broker_order_id="ABC123")
        assert req.quantity == 0
        assert req.price is None

    def test_with_changes(self) -> None:
        req = ModifyOrderRequest(
            broker_order_id="ABC123",
            quantity=15,
            price=Decimal("2600.00"),
        )
        assert req.quantity == 15
        assert req.price == Decimal("2600.00")


class TestCancelOrderRequest:
    def test_default(self) -> None:
        req = CancelOrderRequest(broker_order_id="ABC")
        assert req.reason == ""

    def test_with_reason(self) -> None:
        req = CancelOrderRequest(broker_order_id="ABC", reason="Changed my mind")
        assert req.reason == "Changed my mind"


class TestOrder:
    def test_required_fields(self) -> None:
        order = Order(
            broker_order_id="O1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            product=ProductType.DELIVERY,
            status=OrderStatus.OPEN,
            quantity=10,
        )
        assert order.symbol == "RELIANCE"
        assert order.filled_quantity == 0

    def test_filled_order(self) -> None:
        order = Order(
            broker_order_id="O1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            product=ProductType.DELIVERY,
            status=OrderStatus.FILLED,
            quantity=10,
            filled_quantity=10,
            average_price=Decimal("2500.00"),
        )
        assert order.average_price == Decimal("2500.00")


class TestPosition:
    def test_required_fields(self) -> None:
        pos = Position(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            instrument_type=InstrumentType.EQUITY,
            product=ProductType.DELIVERY,
            quantity=10,
        )
        assert pos.quantity == 10
        assert pos.pnl is None

    def test_short_position(self) -> None:
        pos = Position(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            instrument_type=InstrumentType.EQUITY,
            product=ProductType.DELIVERY,
            quantity=-5,
            buy_quantity=0,
            sell_quantity=5,
        )
        assert pos.quantity == -5


class TestHolding:
    def test_fields(self) -> None:
        h = Holding(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            instrument_type=InstrumentType.EQUITY,
            quantity=100,
            available_quantity=100,
            buy_price=Decimal("2400.00"),
        )
        assert h.quantity == 100
        assert h.buy_price == Decimal("2400.00")


class TestTrade:
    def test_fields(self) -> None:
        t = Trade(
            trade_id="T1",
            broker_order_id="O1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            quantity=10,
            price=Decimal("2500.00"),
        )
        assert t.price == Decimal("2500.00")
        assert t.trade_time is None


class TestQuote:
    def test_required_fields(self) -> None:
        q = Quote(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            last_price=Decimal("2500.00"),
        )
        assert q.last_price == Decimal("2500.00")
        assert q.bid is None

    def test_full_quote(self) -> None:
        q = Quote(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            last_price=Decimal("2500.00"),
            bid=Decimal("2499.00"),
            ask=Decimal("2501.00"),
            volume=100000,
        )
        assert q.bid == Decimal("2499.00")
        assert q.ask == Decimal("2501.00")


class TestMarketDepthLevel:
    def test_fields(self) -> None:
        level = MarketDepthLevel(
            price=Decimal("2500.00"),
            quantity=1000,
            orders=5,
        )
        assert level.price == Decimal("2500.00")
        assert level.orders == 5


class TestMarketDepth:
    def test_default(self) -> None:
        md = MarketDepth(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
        )
        assert md.bids == ()
        assert md.asks == ()

    def test_with_levels(self) -> None:
        md = MarketDepth(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            bids=(
                MarketDepthLevel(Decimal("2499.00"), 500, 3),
                MarketDepthLevel(Decimal("2498.00"), 300, 2),
            ),
            asks=(MarketDepthLevel(Decimal("2501.00"), 400, 4),),
        )
        assert len(md.bids) == 2
        assert len(md.asks) == 1


class TestMarginInfo:
    def test_default(self) -> None:
        mi = MarginInfo()
        assert mi.total_margin is None
        assert mi.available_margin is None

    def test_with_values(self) -> None:
        mi = MarginInfo(
            total_margin=Decimal("500000.00"),
            used_margin=Decimal("100000.00"),
            available_margin=Decimal("400000.00"),
        )
        assert mi.available_margin == Decimal("400000.00")


class TestFundsInfo:
    def test_default(self) -> None:
        fi = FundsInfo()
        assert fi.available_cash is None

    def test_with_values(self) -> None:
        fi = FundsInfo(
            available_cash=Decimal("500000.00"),
            realised_pnl=Decimal("25000.00"),
        )
        assert fi.realised_pnl == Decimal("25000.00")


class TestAccountProfile:
    def test_default(self) -> None:
        ap = AccountProfile()
        assert ap.account_id == ""
        assert ap.enabled_exchanges == ()

    def test_with_values(self) -> None:
        ap = AccountProfile(
            account_id="ACC123",
            name="Test User",
            broker="Angel One",
            enabled_exchanges=(Exchange.NSE, Exchange.BSE),
        )
        assert Exchange.NSE in ap.enabled_exchanges


class TestCandle:
    def test_fields(self) -> None:
        dt = datetime(2026, 7, 3, 9, 15)
        c = Candle(
            datetime=dt,
            open=Decimal("2500.00"),
            high=Decimal("2510.00"),
            low=Decimal("2490.00"),
            close=Decimal("2505.00"),
            volume=100000,
        )
        assert c.open == Decimal("2500.00")
        assert c.oi is None

    def test_with_oi(self) -> None:
        c = Candle(
            datetime=datetime(2026, 7, 3, 9, 15),
            open=Decimal("100.00"),
            high=Decimal("101.00"),
            low=Decimal("99.00"),
            close=Decimal("100.50"),
            volume=50000,
            oi=1000000,
        )
        assert c.oi == 1000000


# ===========================================================================
# Exception Tests
# ===========================================================================


class TestExceptions:
    def test_broker_error(self) -> None:
        with pytest.raises(BrokerError):
            raise BrokerError("Generic error")

    def test_connection_error(self) -> None:
        with pytest.raises(ConnectionError):
            raise ConnectionError("Connection refused")

    def test_authentication_error(self) -> None:
        with pytest.raises(AuthenticationError):
            raise AuthenticationError("Invalid credentials")

    def test_order_error(self) -> None:
        with pytest.raises(OrderError):
            raise OrderError("Order rejected")

    def test_market_data_error(self) -> None:
        with pytest.raises(MarketDataError):
            raise MarketDataError("Data unavailable")

    def test_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            raise ValidationError("Invalid request")

    def test_exception_hierarchy(self) -> None:
        assert issubclass(ConnectionError, BrokerError)
        assert issubclass(AuthenticationError, BrokerError)
        assert issubclass(OrderError, BrokerError)
        assert issubclass(MarketDataError, BrokerError)
        assert issubclass(ValidationError, BrokerError)


# ===========================================================================
# Interface Tests (abstract base classes)
# ===========================================================================


class TestInterfacesAreABC:
    def test_market_data_provider_is_abc(self) -> None:
        assert issubclass(MarketDataProvider, ABC)

    def test_historical_data_provider_is_abc(self) -> None:
        assert issubclass(HistoricalDataProvider, ABC)

    def test_order_provider_is_abc(self) -> None:
        assert issubclass(OrderProvider, ABC)

    def test_portfolio_provider_is_abc(self) -> None:
        assert issubclass(PortfolioProvider, ABC)

    def test_account_provider_is_abc(self) -> None:
        assert issubclass(AccountProvider, ABC)

    def test_broker_is_abc(self) -> None:
        assert issubclass(Broker, ABC)

    def test_broker_combines_all_providers(self) -> None:
        assert issubclass(Broker, MarketDataProvider)
        assert issubclass(Broker, HistoricalDataProvider)
        assert issubclass(Broker, OrderProvider)
        assert issubclass(Broker, PortfolioProvider)
        assert issubclass(Broker, AccountProvider)

    def test_broker_has_connect_disconnect(self) -> None:
        assert hasattr(Broker, "connect")
        assert hasattr(Broker, "disconnect")
        assert hasattr(Broker, "is_connected")


class TestBrokerCannotBeInstantiated:
    def test_cannot_instantiate_broker_directly(self) -> None:
        with pytest.raises(TypeError):
            Broker()  # type: ignore[abstract]

    def test_cannot_instantiate_providers_directly(self) -> None:
        with pytest.raises(TypeError):
            MarketDataProvider()  # type: ignore[abstract]
        with pytest.raises(TypeError):
            HistoricalDataProvider()  # type: ignore[abstract]
        with pytest.raises(TypeError):
            OrderProvider()  # type: ignore[abstract]
        with pytest.raises(TypeError):
            PortfolioProvider()  # type: ignore[abstract]
        with pytest.raises(TypeError):
            AccountProvider()  # type: ignore[abstract]


# ===========================================================================
# Concrete Broker Implementation Tests
# ===========================================================================


class TestConcreteBroker:
    """Concrete broker implementation for testing purposes."""

    def test_concrete_broker_can_be_instantiated(self) -> None:
        broker = _create_test_broker()
        assert isinstance(broker, Broker)

    def test_connect_disconnect(self) -> None:
        broker = _create_test_broker()
        status = broker.connect()
        assert status == ConnectionStatus.CONNECTED
        assert broker.is_connected() is True

        status = broker.disconnect()
        assert status == ConnectionStatus.DISCONNECTED
        assert broker.is_connected() is False

    def test_quote(self) -> None:
        broker = _create_test_broker()
        q = broker.quote("RELIANCE")
        assert isinstance(q, Quote)
        assert q.symbol == "RELIANCE"

    def test_quotes(self) -> None:
        broker = _create_test_broker()
        quotes = broker.quotes(["RELIANCE", "INFY"])
        assert len(quotes) == 2
        assert isinstance(quotes["RELIANCE"], Quote)

    def test_ltp(self) -> None:
        broker = _create_test_broker()
        price = broker.ltp("RELIANCE")
        assert isinstance(price, Decimal)

    def test_option_chain(self) -> None:
        broker = _create_test_broker()
        chain = broker.option_chain("NIFTY")
        assert isinstance(chain, list)

    def test_market_depth(self) -> None:
        broker = _create_test_broker()
        depth = broker.market_depth("RELIANCE")
        assert isinstance(depth, MarketDepth)
        assert depth.symbol == "RELIANCE"

    def test_history(self) -> None:
        broker = _create_test_broker()
        candles = broker.history("RELIANCE", "1day", datetime(2026, 1, 1))
        assert isinstance(candles, list)
        assert all(isinstance(c, Candle) for c in candles)

    def test_intraday(self) -> None:
        broker = _create_test_broker()
        candles = broker.intraday("RELIANCE")
        assert isinstance(candles, list)

    def test_ohlcv(self) -> None:
        broker = _create_test_broker()
        candles = broker.ohlcv("RELIANCE", limit=50)
        assert len(candles) <= 50

    def test_place_order(self) -> None:
        broker = _create_test_broker()
        req = OrderRequest(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        resp = broker.place_order(req)
        assert isinstance(resp, OrderResponse)
        assert resp.status == OrderStatus.FILLED

    def test_modify_order(self) -> None:
        broker = _create_test_broker()
        req = ModifyOrderRequest(
            broker_order_id="O1",
            quantity=15,
        )
        resp = broker.modify_order(req)
        assert isinstance(resp, OrderResponse)

    def test_cancel_order(self) -> None:
        broker = _create_test_broker()
        req = CancelOrderRequest(broker_order_id="O1")
        resp = broker.cancel_order(req)
        assert isinstance(resp, OrderResponse)

    def test_order(self) -> None:
        broker = _create_test_broker()
        order = broker.order("O1")
        assert isinstance(order, Order)
        assert order.broker_order_id == "O1"

    def test_orders(self) -> None:
        broker = _create_test_broker()
        orders = broker.orders()
        assert isinstance(orders, list)

    def test_positions(self) -> None:
        broker = _create_test_broker()
        positions = broker.positions()
        assert isinstance(positions, list)
        assert all(isinstance(p, Position) for p in positions)

    def test_holdings(self) -> None:
        broker = _create_test_broker()
        holdings = broker.holdings()
        assert isinstance(holdings, list)
        assert all(isinstance(h, Holding) for h in holdings)

    def test_trades(self) -> None:
        broker = _create_test_broker()
        trades = broker.trades()
        assert isinstance(trades, list)
        assert all(isinstance(t, Trade) for t in trades)

    def test_funds(self) -> None:
        broker = _create_test_broker()
        funds = broker.funds()
        assert isinstance(funds, FundsInfo)

    def test_margin(self) -> None:
        broker = _create_test_broker()
        margin = broker.margin()
        assert isinstance(margin, MarginInfo)

    def test_profile(self) -> None:
        broker = _create_test_broker()
        profile = broker.profile()
        assert isinstance(profile, AccountProfile)


# ===========================================================================
# Factory Tests
# ===========================================================================


class TestBrokerFactory:
    def test_register_and_create(self) -> None:
        factory = BrokerFactory()
        factory.register(BrokerType.ANGEL_ONE, _TestBroker)
        broker = factory.create(BrokerType.ANGEL_ONE)
        assert isinstance(broker, _TestBroker)

    def test_create_unregistered_raises_error(self) -> None:
        factory = BrokerFactory()
        with pytest.raises(BrokerError, match="No broker registered"):
            factory.create(BrokerType.ZERODHA)

    def test_duplicate_registration_raises_error(self) -> None:
        factory = BrokerFactory()
        factory.register(BrokerType.ANGEL_ONE, _TestBroker)
        with pytest.raises(BrokerError, match="already registered"):
            factory.register(BrokerType.ANGEL_ONE, _TestBroker)

    def test_register_invalid_class_raises_error(self) -> None:
        factory = BrokerFactory()

        class NotABroker:
            pass

        with pytest.raises(BrokerError, match="must implement the Broker interface"):
            factory.register(BrokerType.ANGEL_ONE, NotABroker)  # type: ignore[type-abstract]

    def test_supported_brokers(self) -> None:
        factory = BrokerFactory()
        assert factory.supported_brokers() == []
        factory.register(BrokerType.ANGEL_ONE, _TestBroker)
        factory.register(BrokerType.ZERODHA, _TestBroker)
        assert BrokerType.ANGEL_ONE in factory.supported_brokers()
        assert BrokerType.ZERODHA in factory.supported_brokers()

    def test_create_with_kwargs(self) -> None:
        factory = BrokerFactory()
        factory.register(BrokerType.ANGEL_ONE, _TestBrokerWithConfig)
        broker = factory.create(BrokerType.ANGEL_ONE, api_key="test-key")
        assert isinstance(broker, _TestBrokerWithConfig)
        assert broker.api_key == "test-key"


# ===========================================================================
# Test Helpers
# ===========================================================================


class _TestBroker(Broker):
    """Minimal concrete broker for testing the interface contract."""

    _connected: bool = False

    def connect(self) -> ConnectionStatus:
        self._connected = True
        return ConnectionStatus.CONNECTED

    def disconnect(self) -> ConnectionStatus:
        self._connected = False
        return ConnectionStatus.DISCONNECTED

    def is_connected(self) -> bool:
        return self._connected

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
        return [
            Candle(
                datetime=start,
                open=Decimal("100.00"),
                high=Decimal("101.00"),
                low=Decimal("99.00"),
                close=Decimal("100.50"),
                volume=1000,
            )
        ]

    def intraday(self, symbol: str, interval: str = "1min") -> list[Candle]:
        return self.history(symbol, interval, datetime(2026, 7, 3))

    def ohlcv(
        self, symbol: str, interval: str = "1day", limit: int = 100
    ) -> list[Candle]:
        return self.history(symbol, interval, datetime(2026, 7, 3))[:limit]

    def place_order(self, request: OrderRequest) -> OrderResponse:
        return OrderResponse(
            broker_order_id="TEST-O1",
            status=OrderStatus.FILLED,
            filled_quantity=request.quantity,
            average_price=Decimal("100.00"),
        )

    def modify_order(self, request: ModifyOrderRequest) -> OrderResponse:
        return OrderResponse(
            broker_order_id=request.broker_order_id,
            status=OrderStatus.OPEN,
        )

    def cancel_order(self, request: CancelOrderRequest) -> OrderResponse:
        return OrderResponse(
            broker_order_id=request.broker_order_id,
            status=OrderStatus.CANCELLED,
        )

    def order(self, broker_order_id: str) -> Order:
        return Order(
            broker_order_id=broker_order_id,
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            product=ProductType.DELIVERY,
            status=OrderStatus.OPEN,
            quantity=10,
        )

    def orders(
        self, symbol: str | None = None, since: datetime | None = None
    ) -> list[Order]:
        return [self.order("O1")]

    def positions(self) -> list[Position]:
        return [
            Position(
                symbol="RELIANCE",
                exchange=Exchange.NSE,
                instrument_type=InstrumentType.EQUITY,
                product=ProductType.DELIVERY,
                quantity=10,
            )
        ]

    def holdings(self) -> list[Holding]:
        return [
            Holding(
                symbol="RELIANCE",
                exchange=Exchange.NSE,
                instrument_type=InstrumentType.EQUITY,
                quantity=100,
            )
        ]

    def trades(
        self, symbol: str | None = None, since: datetime | None = None
    ) -> list[Trade]:
        return [
            Trade(
                trade_id="T1",
                broker_order_id="O1",
                symbol="RELIANCE",
                exchange=Exchange.NSE,
                side=OrderSide.BUY,
                quantity=10,
                price=Decimal("100.00"),
            )
        ]

    def funds(self) -> FundsInfo:
        return FundsInfo(
            available_cash=Decimal("500000.00"),
        )

    def margin(self) -> MarginInfo:
        return MarginInfo(
            total_margin=Decimal("500000.00"),
            available_margin=Decimal("400000.00"),
        )

    def profile(self) -> AccountProfile:
        return AccountProfile(
            account_id="ACC123",
            name="Test User",
            broker="Test Broker",
        )


class _TestBrokerWithConfig(Broker):
    """Test broker that accepts configuration kwargs."""

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key

    def connect(self) -> ConnectionStatus:
        return ConnectionStatus.CONNECTED

    def disconnect(self) -> ConnectionStatus:
        return ConnectionStatus.DISCONNECTED

    def is_connected(self) -> bool:
        return True

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

    def place_order(self, request: OrderRequest) -> OrderResponse:
        return OrderResponse(broker_order_id="O1", status=OrderStatus.OPEN)

    def modify_order(self, request: ModifyOrderRequest) -> OrderResponse:
        return OrderResponse(
            broker_order_id=request.broker_order_id, status=OrderStatus.OPEN
        )

    def cancel_order(self, request: CancelOrderRequest) -> OrderResponse:
        return OrderResponse(
            broker_order_id=request.broker_order_id, status=OrderStatus.CANCELLED
        )

    def order(self, broker_order_id: str) -> Order:
        return Order(
            broker_order_id=broker_order_id,
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            product=ProductType.DELIVERY,
            status=OrderStatus.OPEN,
            quantity=10,
        )

    def orders(
        self, symbol: str | None = None, since: datetime | None = None
    ) -> list[Order]:
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


def _create_test_broker() -> _TestBroker:
    return _TestBroker()
