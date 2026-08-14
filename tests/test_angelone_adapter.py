"""Tests for the Angel One broker adapter.

All tests mock the SmartAPI SDK. No live servers are contacted.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

import pytest

from titan.brokers.angelone.account import AngelOneAccountProvider
from titan.brokers.angelone.adapter import AngelOneBroker
from titan.brokers.angelone.auth import AngelOneAuthenticator
from titan.brokers.angelone.exceptions import translate_error
from titan.brokers.angelone.history import AngelOneHistoricalDataProvider
from titan.brokers.angelone.mapper import (
    candle_from_smartapi,
    funds_from_smartapi,
    holding_from_smartapi,
    margin_from_smartapi,
    market_depth_from_smartapi,
    order_from_smartapi,
    order_request_to_smartapi,
    order_response_from_smartapi,
    position_from_smartapi,
    profile_from_smartapi,
    quote_from_smartapi,
    trade_from_smartapi,
)
from titan.brokers.angelone.market import AngelOneMarketDataProvider
from titan.brokers.angelone.orders import AngelOneOrderProvider
from titan.brokers.angelone.portfolio import AngelOnePortfolioProvider
from titan.brokers.exceptions import (
    AuthenticationError,
    BrokerError,
    ConnectionError,
    MarketDataError,
    OrderError,
)
from titan.brokers.models import (
    BrokerType,
    CancelOrderRequest,
    Exchange,
    ModifyOrderRequest,
    OrderRequest,
    OrderResponse,
    OrderSide,
    OrderStatus,
    OrderType,
    Quote,
)

# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def mock_smart_connect() -> MagicMock:
    """Create a mock SmartConnect instance."""
    return MagicMock()


@pytest.fixture
def mock_session_response() -> dict[str, Any]:
    return {
        "data": {
            "jwtToken": "test-jwt-token",
            "refreshToken": "test-refresh-token",
        }
    }


@pytest.fixture
def sample_quote_data() -> dict[str, Any]:
    return {
        "symbol": "RELIANCE",
        "exchange": "NSE",
        "ltp": 2500.50,
        "open": 2480.00,
        "high": 2510.00,
        "low": 2475.00,
        "close": 2490.00,
        "volume": 100000,
        "bid": 2499.00,
        "ask": 2501.00,
        "bid_qty": 500,
        "ask_qty": 300,
        "oi": 0,
        "change": 10.50,
        "change_percent": 0.42,
    }


@pytest.fixture
def sample_candle_data() -> dict[str, Any]:
    return {
        "timestamp": "2026-07-03T09:15:00+00:00",
        "open": 2500.00,
        "high": 2510.00,
        "low": 2490.00,
        "close": 2505.00,
        "volume": 100000,
        "oi": 0,
    }


@pytest.fixture
def sample_order_data() -> dict[str, Any]:
    return {
        "orderid": "ORD-001",
        "symbol": "RELIANCE",
        "exchange": "NSE",
        "transactiontype": "BUY",
        "ordertype": "MARKET",
        "quantity": 10,
        "producttype": "DELIVERY",
        "status": "FILLED",
        "filledqty": 10,
        "pendingqty": 0,
        "averageprice": 2500.00,
        "price": 0,
        "triggerprice": 0,
        "validity": "DAY",
    }


@pytest.fixture
def sample_position_data() -> dict[str, Any]:
    return {
        "symbol": "RELIANCE",
        "exchange": "NSE",
        "instrumenttype": "EQ",
        "producttype": "DELIVERY",
        "netqty": 10,
        "buyqty": 10,
        "sellqty": 0,
        "buyavgprice": 2500.00,
        "ltp": 2520.00,
        "pnl": 200.00,
    }


@pytest.fixture
def sample_holding_data() -> dict[str, Any]:
    return {
        "symbol": "RELIANCE",
        "exchange": "NSE",
        "instrumenttype": "EQ",
        "quantity": 100,
        "availablequantity": 100,
        "buyavgprice": 2400.00,
        "ltp": 2500.00,
        "pnl": 10000.00,
    }


@pytest.fixture
def sample_trade_data() -> dict[str, Any]:
    return {
        "tradeid": "TRD-001",
        "orderid": "ORD-001",
        "symbol": "RELIANCE",
        "exchange": "NSE",
        "transactiontype": "BUY",
        "filledqty": 10,
        "fillprice": 2500.00,
        "producttype": "DELIVERY",
    }


@pytest.fixture
def sample_depth_data() -> dict[str, Any]:
    return {
        "symbol": "RELIANCE",
        "exchange": "NSE",
        "bids": [
            {"price": 2499.00, "quantity": 500, "orders": 3},
            {"price": 2498.00, "quantity": 300, "orders": 2},
        ],
        "asks": [
            {"price": 2501.00, "quantity": 400, "orders": 4},
        ],
    }


@pytest.fixture
def sample_funds_data() -> dict[str, Any]:
    return {
        "availablecash": 500000.00,
        "usedcash": 100000.00,
        "realisedpnl": 25000.00,
        "unrealisedpnl": 5000.00,
    }


@pytest.fixture
def sample_profile_data() -> dict[str, Any]:
    return {
        "clientid": "ACC123",
        "name": "Test User",
        "email": "test@example.com",
        "mobile": "9999999999",
    }


# ===========================================================================
# Mapper Tests
# ===========================================================================


class TestQuoteFromSmartAPI:
    def test_full_quote(self, sample_quote_data: dict[str, Any]) -> None:
        quote = quote_from_smartapi(sample_quote_data)
        assert quote.symbol == "RELIANCE"
        assert quote.last_price == Decimal("2500.50")
        assert quote.bid == Decimal("2499.00")
        assert quote.ask == Decimal("2501.00")
        assert quote.volume == 100000
        assert quote.bid_quantity == 500

    def test_minimal_quote(self) -> None:
        quote = quote_from_smartapi({"symbol": "TEST", "exchange": "NSE", "ltp": 100})
        assert quote.symbol == "TEST"
        assert quote.last_price == Decimal("100")
        assert quote.bid is None

    def test_empty_data(self) -> None:
        quote = quote_from_smartapi({})
        assert quote.symbol == ""
        assert quote.last_price == Decimal("0")


class TestCandleFromSmartAPI:
    def test_full_candle(self, sample_candle_data: dict[str, Any]) -> None:
        candle = candle_from_smartapi(sample_candle_data)
        assert candle.open == Decimal("2500.00")
        assert candle.high == Decimal("2510.00")
        assert candle.close == Decimal("2505.00")
        assert candle.volume == 100000
        assert candle.oi == 0

    def test_minimal_candle(self) -> None:
        candle = candle_from_smartapi(
            {
                "timestamp": "2026-07-03T09:15:00",
                "open": 100,
                "close": 101,
                "high": 102,
                "low": 99,
                "volume": 5000,
            }
        )
        assert candle.open == Decimal("100")
        assert candle.volume == 5000


class TestOrderResponseFromSmartAPI:
    def test_filled_order(self, sample_order_data: dict[str, Any]) -> None:
        resp = order_response_from_smartapi(sample_order_data)
        assert resp.broker_order_id == "ORD-001"
        assert resp.status == OrderStatus.FILLED
        assert resp.filled_quantity == 10

    def test_pending_order(self) -> None:
        resp = order_response_from_smartapi({"orderid": "ORD-002", "status": "OPEN"})
        assert resp.status == OrderStatus.OPEN
        assert resp.filled_quantity == 0


class TestOrderFromSmartAPI:
    def test_full_order(self, sample_order_data: dict[str, Any]) -> None:
        order = order_from_smartapi(sample_order_data)
        assert order.broker_order_id == "ORD-001"
        assert order.symbol == "RELIANCE"
        assert order.side == OrderSide.BUY
        assert order.status == OrderStatus.FILLED

    def test_cancelled_order(self) -> None:
        order = order_from_smartapi(
            {
                "orderid": "ORD-003",
                "symbol": "INFY",
                "exchange": "NSE",
                "transactiontype": "SELL",
                "ordertype": "LIMIT",
                "quantity": 5,
                "producttype": "DELIVERY",
                "status": "CANCELLED",
            }
        )
        assert order.status == OrderStatus.CANCELLED
        assert order.side == OrderSide.SELL


class TestPositionFromSmartAPI:
    def test_full_position(self, sample_position_data: dict[str, Any]) -> None:
        pos = position_from_smartapi(sample_position_data)
        assert pos.symbol == "RELIANCE"
        assert pos.quantity == 10
        assert pos.buy_price == Decimal("2500.00")
        assert pos.pnl == Decimal("200.00")

    def test_short_position(self) -> None:
        pos = position_from_smartapi(
            {
                "symbol": "INFY",
                "exchange": "NSE",
                "instrumenttype": "EQ",
                "producttype": "DELIVERY",
                "netqty": -5,
            }
        )
        assert pos.quantity == -5


class TestHoldingFromSmartAPI:
    def test_full_holding(self, sample_holding_data: dict[str, Any]) -> None:
        h = holding_from_smartapi(sample_holding_data)
        assert h.symbol == "RELIANCE"
        assert h.quantity == 100
        assert h.available_quantity == 100
        assert h.buy_price == Decimal("2400.00")


class TestTradeFromSmartAPI:
    def test_full_trade(self, sample_trade_data: dict[str, Any]) -> None:
        t = trade_from_smartapi(sample_trade_data)
        assert t.trade_id == "TRD-001"
        assert t.broker_order_id == "ORD-001"
        assert t.symbol == "RELIANCE"
        assert t.price == Decimal("2500.00")


class TestMarketDepthFromSmartAPI:
    def test_full_depth(self, sample_depth_data: dict[str, Any]) -> None:
        md = market_depth_from_smartapi(sample_depth_data)
        assert md.symbol == "RELIANCE"
        assert len(md.bids) == 2
        assert len(md.asks) == 1
        assert md.bids[0].price == Decimal("2499.00")
        assert md.asks[0].price == Decimal("2501.00")

    def test_empty_depth(self) -> None:
        md = market_depth_from_smartapi({"symbol": "TEST", "exchange": "NSE"})
        assert md.bids == ()
        assert md.asks == ()


class TestFundsFromSmartAPI:
    def test_full_funds(self, sample_funds_data: dict[str, Any]) -> None:
        f = funds_from_smartapi(sample_funds_data)
        assert f.available_cash == Decimal("500000.00")
        assert f.used_cash == Decimal("100000.00")
        assert f.realised_pnl == Decimal("25000.00")


class TestMarginFromSmartAPI:
    def test_margin(self) -> None:
        m = margin_from_smartapi(
            {"totalmargin": 500000, "usedmargin": 100000, "availablemargin": 400000}
        )
        assert m.total_margin == Decimal("500000")
        assert m.available_margin == Decimal("400000")

    def test_empty_margin(self) -> None:
        m = margin_from_smartapi({})
        assert m.total_margin is None


class TestProfileFromSmartAPI:
    def test_profile(self, sample_profile_data: dict[str, Any]) -> None:
        p = profile_from_smartapi(sample_profile_data)
        assert p.account_id == "ACC123"
        assert p.name == "Test User"
        assert p.broker == "Angel One"


class TestOrderRequestToSmartAPI:
    def test_market_order(self) -> None:
        req = OrderRequest(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        payload = order_request_to_smartapi(req)
        assert payload["symbol"] == "RELIANCE"
        assert payload["exchange"] == "NSE"
        assert payload["transactiontype"] == "BUY"
        assert payload["ordertype"] == "MARKET"
        assert payload["quantity"] == 10

    def test_limit_order(self) -> None:
        req = OrderRequest(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=5,
            price=Decimal("2600.00"),
        )
        payload = order_request_to_smartapi(req)
        assert payload["transactiontype"] == "SELL"
        assert payload["ordertype"] == "LIMIT"
        assert payload["price"] == "2600.00"


# ===========================================================================
# Exception Translation Tests
# ===========================================================================


class TestTranslateError:
    def test_known_error_code(self) -> None:
        exc = MagicMock()
        exc.code = "AB1010"
        exc.message = "Invalid credentials"
        translated = translate_error(exc)
        assert isinstance(translated, AuthenticationError)
        assert "AB1010" in str(translated)

    def test_order_error_code(self) -> None:
        exc = MagicMock()
        exc.code = "AB2000"
        exc.message = "Order rejected"
        translated = translate_error(exc)
        assert isinstance(translated, OrderError)

    def test_market_data_error_code(self) -> None:
        exc = MagicMock()
        exc.code = "AB3000"
        exc.message = "Data unavailable"
        translated = translate_error(exc)
        assert isinstance(translated, MarketDataError)

    def test_connection_error_code(self) -> None:
        exc = MagicMock()
        exc.code = "AB4000"
        exc.message = "Connection failed"
        translated = translate_error(exc)
        assert isinstance(translated, ConnectionError)

    def test_unknown_error_code(self) -> None:
        exc = MagicMock()
        exc.code = "UNKNOWN"
        exc.message = "Something broke"
        translated = translate_error(exc)
        assert isinstance(translated, BrokerError)

    def test_exception_without_attributes(self) -> None:
        exc = Exception("Generic error")
        translated = translate_error(exc)
        assert isinstance(translated, BrokerError)
        assert "Generic error" in str(translated)


# ===========================================================================
# Authenticator Tests
# ===========================================================================


class TestAngelOneAuthenticator:
    def test_login_success(
        self, mock_smart_connect: MagicMock, mock_session_response: dict[str, Any]
    ) -> None:
        mock_smart_connect.generateSession.return_value = mock_session_response
        mock_smart_connect.getfeedToken.return_value = "feed-token-123"

        auth = AngelOneAuthenticator(
            api_key="test-key",
            client_id="test-client",
            pin="test-pin",
            totp_secret="test-secret",
            smart_connect=mock_smart_connect,
            totp_generator=lambda _: "123456",
        )
        status = auth.login()

        assert status.value == "connected"
        assert auth.feed_token == "feed-token-123"
        assert auth.validate_session() is True

    def test_login_failure_missing_jwt(self, mock_smart_connect: MagicMock) -> None:
        mock_smart_connect.generateSession.return_value = {"data": {}}

        auth = AngelOneAuthenticator(
            api_key="test-key",
            client_id="test-client",
            pin="test-pin",
            totp_secret="test-secret",
            smart_connect=mock_smart_connect,
            totp_generator=lambda _: "123456",
        )
        with pytest.raises(AuthenticationError):
            auth.login()

    def test_logout(self, mock_smart_connect: MagicMock) -> None:
        auth = AngelOneAuthenticator(
            api_key="test-key",
            client_id="test-client",
            pin="test-pin",
            totp_secret="test-secret",
            smart_connect=mock_smart_connect,
            totp_generator=lambda _: "123456",
        )
        status = auth.logout()
        assert status.value == "disconnected"
        assert auth.validate_session() is False

    def test_validate_session_false_when_not_connected(self) -> None:
        auth = AngelOneAuthenticator()
        assert auth.validate_session() is False

    def test_connection_status_default(self) -> None:
        auth = AngelOneAuthenticator()
        assert auth.connection_status.value == "disconnected"


# ===========================================================================
# Market Data Provider Tests
# ===========================================================================


class TestAngelOneMarketDataProvider:
    def test_ltp(self, mock_smart_connect: MagicMock) -> None:
        mock_smart_connect.getMarketData.return_value = {"data": {"ltp": 2500.50}}
        provider = AngelOneMarketDataProvider(smart_connect=mock_smart_connect)
        price = provider.ltp("RELIANCE")
        assert price == Decimal("2500.50")

    def test_quote(
        self, mock_smart_connect: MagicMock, sample_quote_data: dict[str, Any]
    ) -> None:
        mock_smart_connect.getMarketData.return_value = {"data": sample_quote_data}
        provider = AngelOneMarketDataProvider(smart_connect=mock_smart_connect)
        quote = provider.quote("RELIANCE")
        assert quote.symbol == "RELIANCE"
        assert quote.last_price == Decimal("2500.50")

    def test_quotes(self, mock_smart_connect: MagicMock) -> None:
        mock_smart_connect.getMarketData.return_value = {
            "data": {"symbol": "RELIANCE", "exchange": "NSE", "ltp": 100}
        }
        provider = AngelOneMarketDataProvider(smart_connect=mock_smart_connect)
        quotes = provider.quotes(["RELIANCE", "INFY"])
        assert len(quotes) == 2

    def test_raises_when_not_connected(self) -> None:
        provider = AngelOneMarketDataProvider()
        with pytest.raises(ConnectionError):
            provider.ltp("RELIANCE")


# ===========================================================================
# Historical Data Provider Tests
# ===========================================================================


class TestAngelOneHistoricalDataProvider:
    def test_history(self, mock_smart_connect: MagicMock) -> None:
        mock_smart_connect.getCandleData.return_value = {
            "data": [
                ["2026-07-03 09:15:00", 2500.0, 2510.0, 2490.0, 2505.0, 100000, 0],
                ["2026-07-03 09:16:00", 2505.0, 2515.0, 2495.0, 2510.0, 80000, 0],
            ]
        }
        provider = AngelOneHistoricalDataProvider(smart_connect=mock_smart_connect)
        candles = provider.history(
            "RELIANCE",
            "1min",
            start=datetime(2026, 7, 3, 9, 15, tzinfo=timezone.utc),
        )
        assert len(candles) == 2
        assert candles[0].open == Decimal("2500.00")
        assert candles[1].close == Decimal("2510.00")
        assert candles[0].volume == 100000

    def test_raises_when_not_connected(self) -> None:
        provider = AngelOneHistoricalDataProvider()
        with pytest.raises(ConnectionError):
            provider.history("RELIANCE", "1day")


# ===========================================================================
# Order Provider Tests
# ===========================================================================


class TestAngelOneOrderProvider:
    def test_place_order(self, mock_smart_connect: MagicMock) -> None:
        mock_smart_connect.placeOrder.return_value = {
            "data": {"orderid": "ORD-001", "status": "OPEN"}
        }
        provider = AngelOneOrderProvider(smart_connect=mock_smart_connect)
        req = OrderRequest(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        resp = provider.place_order(req)
        assert resp.broker_order_id == "ORD-001"
        assert resp.status == OrderStatus.OPEN

    def test_modify_order(self, mock_smart_connect: MagicMock) -> None:
        mock_smart_connect.modifyOrder.return_value = {
            "data": {"orderid": "ORD-001", "status": "OPEN"}
        }
        provider = AngelOneOrderProvider(smart_connect=mock_smart_connect)
        req = ModifyOrderRequest(broker_order_id="ORD-001", quantity=15)
        resp = provider.modify_order(req)
        assert resp.broker_order_id == "ORD-001"

    def test_cancel_order(self, mock_smart_connect: MagicMock) -> None:
        mock_smart_connect.cancelOrder.return_value = {
            "data": {"orderid": "ORD-001", "status": "CANCELLED"}
        }
        provider = AngelOneOrderProvider(smart_connect=mock_smart_connect)
        req = CancelOrderRequest(broker_order_id="ORD-001")
        resp = provider.cancel_order(req)
        assert resp.status == OrderStatus.CANCELLED

    def test_orders(
        self, mock_smart_connect: MagicMock, sample_order_data: dict[str, Any]
    ) -> None:
        mock_smart_connect.getOrderBook.return_value = {"data": [sample_order_data]}
        provider = AngelOneOrderProvider(smart_connect=mock_smart_connect)
        orders = provider.orders()
        assert len(orders) == 1
        assert orders[0].broker_order_id == "ORD-001"

    def test_order_by_id(
        self, mock_smart_connect: MagicMock, sample_order_data: dict[str, Any]
    ) -> None:
        mock_smart_connect.getOrderBook.return_value = {"data": [sample_order_data]}
        provider = AngelOneOrderProvider(smart_connect=mock_smart_connect)
        order = provider.order("ORD-001")
        assert order.broker_order_id == "ORD-001"

    def test_order_by_id_not_found(self, mock_smart_connect: MagicMock) -> None:
        mock_smart_connect.getOrderBook.return_value = {"data": []}
        provider = AngelOneOrderProvider(smart_connect=mock_smart_connect)
        with pytest.raises(OrderError):
            provider.order("NONEXISTENT")

    def test_raises_when_not_connected(self) -> None:
        provider = AngelOneOrderProvider()
        with pytest.raises(ConnectionError):
            provider.orders()


# ===========================================================================
# Portfolio Provider Tests
# ===========================================================================


class TestAngelOnePortfolioProvider:
    def test_positions(
        self, mock_smart_connect: MagicMock, sample_position_data: dict[str, Any]
    ) -> None:
        mock_smart_connect.getPosition.return_value = {"data": [sample_position_data]}
        provider = AngelOnePortfolioProvider(smart_connect=mock_smart_connect)
        positions = provider.positions()
        assert len(positions) == 1
        assert positions[0].symbol == "RELIANCE"
        assert positions[0].quantity == 10

    def test_holdings(
        self, mock_smart_connect: MagicMock, sample_holding_data: dict[str, Any]
    ) -> None:
        mock_smart_connect.holdings.return_value = {"data": [sample_holding_data]}
        provider = AngelOnePortfolioProvider(smart_connect=mock_smart_connect)
        holdings = provider.holdings()
        assert len(holdings) == 1
        assert holdings[0].symbol == "RELIANCE"

    def test_trades(
        self, mock_smart_connect: MagicMock, sample_trade_data: dict[str, Any]
    ) -> None:
        mock_smart_connect.getTradeBook.return_value = {"data": [sample_trade_data]}
        provider = AngelOnePortfolioProvider(smart_connect=mock_smart_connect)
        trades = provider.trades()
        assert len(trades) == 1
        assert trades[0].trade_id == "TRD-001"

    def test_raises_when_not_connected(self) -> None:
        provider = AngelOnePortfolioProvider()
        with pytest.raises(ConnectionError):
            provider.positions()


# ===========================================================================
# Account Provider Tests
# ===========================================================================


class TestAngelOneAccountProvider:
    def test_funds(
        self, mock_smart_connect: MagicMock, sample_funds_data: dict[str, Any]
    ) -> None:
        mock_smart_connect.getFundsAndMargin.return_value = {"data": sample_funds_data}
        provider = AngelOneAccountProvider(smart_connect=mock_smart_connect)
        funds = provider.funds()
        assert funds.available_cash == Decimal("500000.00")

    def test_margin(self, mock_smart_connect: MagicMock) -> None:
        mock_smart_connect.getFundsAndMargin.return_value = {
            "data": {"totalmargin": 500000, "availablemargin": 400000}
        }
        provider = AngelOneAccountProvider(smart_connect=mock_smart_connect)
        margin = provider.margin()
        assert margin.total_margin == Decimal("500000")

    def test_profile(
        self, mock_smart_connect: MagicMock, sample_profile_data: dict[str, Any]
    ) -> None:
        mock_smart_connect.getProfile.return_value = {"data": sample_profile_data}
        mock_smart_connect.refreshToken = "test-token"
        provider = AngelOneAccountProvider(smart_connect=mock_smart_connect)
        profile = provider.profile()
        assert profile.name == "Test User"

    def test_raises_when_not_connected(self) -> None:
        provider = AngelOneAccountProvider()
        with pytest.raises(ConnectionError):
            provider.funds()


# ===========================================================================
# Broker Adapter Integration Tests
# ===========================================================================


class TestAngelOneBrokerAdapter:
    def test_connect(
        self, mock_smart_connect: MagicMock, mock_session_response: dict[str, Any]
    ) -> None:
        mock_smart_connect.generateSession.return_value = mock_session_response
        mock_smart_connect.getfeedToken.return_value = "feed-token"

        broker = AngelOneBroker(
            api_key="test-key",
            client_id="test-client",
            pin="test-pin",
            totp_secret="test-secret",
            smart_connect=mock_smart_connect,
            totp_generator=lambda _: "123456",
        )
        status = broker.connect()
        assert status.value == "connected"
        assert broker.is_connected() is True

    def test_disconnect(
        self, mock_smart_connect: MagicMock, mock_session_response: dict[str, Any]
    ) -> None:
        broker = AngelOneBroker(smart_connect=mock_smart_connect)
        status = broker.disconnect()
        assert status.value == "disconnected"
        assert broker.is_connected() is False

    def test_broker_type_registration(self) -> None:
        from titan.brokers.factory import BrokerFactory

        factory = BrokerFactory()
        factory.register(BrokerType.ANGEL_ONE, AngelOneBroker)
        broker = factory.create(BrokerType.ANGEL_ONE)
        assert isinstance(broker, AngelOneBroker)

    def test_implements_all_broker_methods(self) -> None:
        from titan.brokers.broker import Broker

        assert issubclass(AngelOneBroker, Broker)

    def test_quote_after_connect(
        self,
        mock_smart_connect: MagicMock,
        mock_session_response: dict[str, Any],
        sample_quote_data: dict[str, Any],
    ) -> None:
        mock_smart_connect.generateSession.return_value = mock_session_response
        mock_smart_connect.getfeedToken.return_value = "feed-token"
        mock_smart_connect.getMarketData.return_value = {"data": sample_quote_data}

        broker = AngelOneBroker(
            smart_connect=mock_smart_connect,
            client_id="test-client-id",
            pin="test-pin",
            totp_secret="test-secret",
            totp_generator=lambda _: "123456",
        )
        broker.connect()
        quote = broker.quote("RELIANCE")
        assert isinstance(quote, Quote)
        assert quote.last_price == Decimal("2500.50")

    def test_place_order_after_connect(
        self, mock_smart_connect: MagicMock, mock_session_response: dict[str, Any]
    ) -> None:
        mock_smart_connect.generateSession.return_value = mock_session_response
        mock_smart_connect.getfeedToken.return_value = "feed-token"
        mock_smart_connect.placeOrder.return_value = {
            "data": {"orderid": "ORD-001", "status": "FILLED"}
        }

        broker = AngelOneBroker(
            smart_connect=mock_smart_connect,
            client_id="test-client-id",
            pin="test-pin",
            totp_secret="test-secret",
            totp_generator=lambda _: "123456",
        )
        broker.connect()
        req = OrderRequest(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        resp = broker.place_order(req)
        assert isinstance(resp, OrderResponse)
        assert resp.broker_order_id == "ORD-001"
