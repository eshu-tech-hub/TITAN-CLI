import json
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from titan.brokers.models import (
    BrokerType,
    CancelOrderRequest,
    ConnectionStatus,
    Exchange,
    ModifyOrderRequest,
    OrderRequest,
    OrderSide,
    OrderStatus,
    OrderType,
    ProductType,
    Validity,
)
from titan.paper import (
    PaperBroker,
    FillEngine,
    PositionEngine,
    PaperPortfolio,
    TradeJournal,
    PerformanceEngine,
    PaperTradingReport,
    PaperTradingExplanation,
    generate_evidence,
    generate_explanation,
    PaperOrder,
    PaperFill,
    PaperPosition,
    PaperPortfolioState,
    PaperTradingError,
    PaperOrderError,
    PaperFillError,
    PaperPortfolioError,
)
from titan.paper.exceptions import (
    PaperPositionError,
)

# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def broker() -> PaperBroker:
    b = PaperBroker(initial_cash=Decimal("100000"))
    b.connect()
    b.set_price("RELIANCE", Decimal("2500.00"))
    return b


@pytest.fixture
def buy_request() -> OrderRequest:
    return OrderRequest(
        symbol="RELIANCE",
        exchange=Exchange.NSE,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=10,
        product=ProductType.DELIVERY,
        validity=Validity.DAY,
    )


@pytest.fixture
def sell_request() -> OrderRequest:
    return OrderRequest(
        symbol="RELIANCE",
        exchange=Exchange.NSE,
        side=OrderSide.SELL,
        order_type=OrderType.MARKET,
        quantity=10,
        product=ProductType.DELIVERY,
        validity=Validity.DAY,
    )


@pytest.fixture
def fill_engine() -> FillEngine:
    return FillEngine()


@pytest.fixture
def position_engine() -> PositionEngine:
    return PositionEngine()


@pytest.fixture
def portfolio() -> PaperPortfolio:
    return PaperPortfolio(initial_cash=Decimal("100000"))


@pytest.fixture
def journal() -> TradeJournal:
    return TradeJournal()


# ===========================================================================
# FillEngine Tests
# ===========================================================================


class TestFillEngine:
    def test_default_construction(self, fill_engine: FillEngine) -> None:
        assert fill_engine is not None

    def test_market_buy_fills(self, fill_engine: FillEngine) -> None:
        broker = PaperBroker()
        broker.set_price("TEST", Decimal("100.00"))
        broker.connect()
        quote = broker.quote("TEST")

        request = OrderRequest(
            symbol="TEST",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        fills = fill_engine.fill(request, quote, "order-1", "broker-1")
        assert len(fills) == 1
        assert fills[0].quantity == 10
        assert fills[0].price > Decimal("0")
        assert fills[0].order_id == "order-1"
        assert fills[0].broker_order_id == "broker-1"

    def test_market_sell_fills(self, fill_engine: FillEngine) -> None:
        broker = PaperBroker()
        broker.set_price("TEST", Decimal("100.00"))
        broker.connect()
        quote = broker.quote("TEST")

        request = OrderRequest(
            symbol="TEST",
            exchange=Exchange.NSE,
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=5,
        )
        fills = fill_engine.fill(request, quote, "order-2", "broker-2")
        assert len(fills) == 1
        assert fills[0].quantity == 5

    def test_limit_buy_fillable(self, fill_engine: FillEngine) -> None:
        broker = PaperBroker()
        broker.set_price("TEST", Decimal("100.00"))
        broker.connect()
        quote = broker.quote("TEST")

        request = OrderRequest(
            symbol="TEST",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=10,
            price=Decimal("101.00"),
        )
        fills = fill_engine.fill(request, quote, "order-3", "broker-3")
        assert len(fills) == 1

    def test_limit_buy_not_fillable(self, fill_engine: FillEngine) -> None:
        broker = PaperBroker()
        broker.set_price("TEST", Decimal("100.00"))
        broker.connect()
        quote = broker.quote("TEST")

        request = OrderRequest(
            symbol="TEST",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=10,
            price=Decimal("90.00"),
        )
        fills = fill_engine.fill(request, quote, "order-4", "broker-4")
        assert len(fills) == 0

    def test_limit_sell_fillable(self, fill_engine: FillEngine) -> None:
        broker = PaperBroker()
        broker.set_price("TEST", Decimal("100.00"))
        broker.connect()
        quote = broker.quote("TEST")

        request = OrderRequest(
            symbol="TEST",
            exchange=Exchange.NSE,
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=10,
            price=Decimal("99.00"),
        )
        fills = fill_engine.fill(request, quote, "order-5", "broker-5")
        assert len(fills) == 1

    def test_limit_sell_not_fillable(self, fill_engine: FillEngine) -> None:
        broker = PaperBroker()
        broker.set_price("TEST", Decimal("100.00"))
        broker.connect()
        quote = broker.quote("TEST")

        request = OrderRequest(
            symbol="TEST",
            exchange=Exchange.NSE,
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=10,
            price=Decimal("110.00"),
        )
        fills = fill_engine.fill(request, quote, "order-6", "broker-6")
        assert len(fills) == 0

    def test_stop_buy_triggers(self, fill_engine: FillEngine) -> None:
        broker = PaperBroker()
        broker.set_price("TEST", Decimal("100.00"))
        broker.connect()
        quote = broker.quote("TEST")

        request = OrderRequest(
            symbol="TEST",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.STOP_LOSS,
            quantity=10,
            trigger_price=Decimal("99.00"),
        )
        fills = fill_engine.fill(request, quote, "order-7", "broker-7")
        assert len(fills) == 1

    def test_stop_buy_not_triggers(self, fill_engine: FillEngine) -> None:
        broker = PaperBroker()
        broker.set_price("TEST", Decimal("100.00"))
        broker.connect()
        quote = broker.quote("TEST")

        request = OrderRequest(
            symbol="TEST",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.STOP_LOSS,
            quantity=10,
            trigger_price=Decimal("101.00"),
        )
        fills = fill_engine.fill(request, quote, "order-8", "broker-8")
        assert len(fills) == 0

    def test_stop_sell_triggers(self, fill_engine: FillEngine) -> None:
        broker = PaperBroker()
        broker.set_price("TEST", Decimal("100.00"))
        broker.connect()
        quote = broker.quote("TEST")

        request = OrderRequest(
            symbol="TEST",
            exchange=Exchange.NSE,
            side=OrderSide.SELL,
            order_type=OrderType.STOP_LOSS,
            quantity=10,
            trigger_price=Decimal("101.00"),
        )
        fills = fill_engine.fill(request, quote, "order-9", "broker-9")
        assert len(fills) == 1

    def test_zero_quantity_raises(self, fill_engine: FillEngine) -> None:
        broker = PaperBroker()
        broker.set_price("TEST", Decimal("100.00"))
        broker.connect()
        quote = broker.quote("TEST")

        request = OrderRequest(
            symbol="TEST",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0,
        )
        with pytest.raises(PaperFillError):
            fill_engine.fill(request, quote, "order-10", "broker-10")

    def test_custom_slippage_model(self) -> None:
        def zero_slippage(request: OrderRequest, quote: Quote) -> Decimal:
            return Decimal("0")

        engine = FillEngine(slippage_model=zero_slippage)
        assert engine.slippage_model is zero_slippage

    def test_custom_latency_model(self) -> None:
        def fast_latency(request: OrderRequest) -> float:
            return 1.0

        engine = FillEngine(latency_model=fast_latency)
        assert engine.latency_model is fast_latency

    def test_commission_computed(self, fill_engine: FillEngine) -> None:
        broker = PaperBroker()
        broker.set_price("TEST", Decimal("100.00"))
        broker.connect()
        quote = broker.quote("TEST")

        request = OrderRequest(
            symbol="TEST",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=100,
        )
        fills = fill_engine.fill(request, quote, "order-11", "broker-11")
        assert fills[0].commission > Decimal("0")


from titan.brokers.models import Quote  # noqa: E402, I100

# ===========================================================================
# PositionEngine Tests
# ===========================================================================


class TestPositionEngine:
    def test_initial_empty(self, position_engine: PositionEngine) -> None:
        assert position_engine.open_positions() == []

    def test_open_buy_position(self, position_engine: PositionEngine) -> None:
        fill = PaperFill(
            fill_id="f1",
            order_id="o1",
            broker_order_id="b1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            quantity=10,
            price=Decimal("2500.00"),
        )
        position_engine.apply_fill(fill)
        pos = position_engine.get_position("RELIANCE")
        assert pos is not None
        assert pos.quantity == 10
        assert pos.average_price == Decimal("2500.00")

    def test_open_sell_position(self, position_engine: PositionEngine) -> None:
        fill = PaperFill(
            fill_id="f2",
            order_id="o2",
            broker_order_id="b2",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.SELL,
            quantity=10,
            price=Decimal("2500.00"),
        )
        position_engine.apply_fill(fill)
        pos = position_engine.get_position("RELIANCE")
        assert pos is not None
        assert pos.quantity == -10

    def test_add_to_long_position(self, position_engine: PositionEngine) -> None:
        f1 = PaperFill(
            fill_id="f1",
            order_id="o1",
            broker_order_id="b1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            quantity=10,
            price=Decimal("2500.00"),
        )
        f2 = PaperFill(
            fill_id="f2",
            order_id="o2",
            broker_order_id="b2",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            quantity=5,
            price=Decimal("2600.00"),
        )
        position_engine.apply_fill(f1)
        position_engine.apply_fill(f2)
        pos = position_engine.get_position("RELIANCE")
        assert pos is not None
        assert pos.quantity == 15
        assert pos.buy_quantity == 15

    def test_reduce_long_position(self, position_engine: PositionEngine) -> None:
        f1 = PaperFill(
            fill_id="f1",
            order_id="o1",
            broker_order_id="b1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            quantity=10,
            price=Decimal("2500.00"),
        )
        f2 = PaperFill(
            fill_id="f2",
            order_id="o2",
            broker_order_id="b2",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.SELL,
            quantity=5,
            price=Decimal("2600.00"),
        )
        position_engine.apply_fill(f1)
        position_engine.apply_fill(f2)
        pos = position_engine.get_position("RELIANCE")
        assert pos is not None
        assert pos.quantity == 5
        assert pos.realized_pnl > Decimal("0")

    def test_close_position(self, position_engine: PositionEngine) -> None:
        f1 = PaperFill(
            fill_id="f1",
            order_id="o1",
            broker_order_id="b1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            quantity=10,
            price=Decimal("2500.00"),
        )
        f2 = PaperFill(
            fill_id="f2",
            order_id="o2",
            broker_order_id="b2",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.SELL,
            quantity=10,
            price=Decimal("2600.00"),
        )
        position_engine.apply_fill(f1)
        position_engine.apply_fill(f2)
        pos = position_engine.get_position("RELIANCE")
        assert pos is not None
        assert pos.quantity == 0

        position_engine.close_position("RELIANCE")
        assert position_engine.get_position("RELIANCE") is None

    def test_multiple_symbols(self, position_engine: PositionEngine) -> None:
        fills = [
            PaperFill(
                fill_id=f"f{i}",
                order_id=f"o{i}",
                broker_order_id=f"b{i}",
                symbol=sym,
                exchange=Exchange.NSE,
                side=OrderSide.BUY,
                quantity=10,
                price=Decimal("100.00"),
            )
            for i, sym in enumerate(["A", "B", "C"])
        ]
        for f in fills:
            position_engine.apply_fill(f)
        assert len(position_engine.open_positions()) == 3

    def test_to_broker_positions(self, position_engine: PositionEngine) -> None:
        fill = PaperFill(
            fill_id="f1",
            order_id="o1",
            broker_order_id="b1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            quantity=10,
            price=Decimal("2500.00"),
        )
        position_engine.apply_fill(fill)
        positions = position_engine.to_broker_positions()
        assert len(positions) == 1
        assert positions[0].symbol == "RELIANCE"
        assert positions[0].quantity == 10

    def test_to_broker_holdings(self, position_engine: PositionEngine) -> None:
        fill = PaperFill(
            fill_id="f1",
            order_id="o1",
            broker_order_id="b1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            quantity=10,
            price=Decimal("2500.00"),
        )
        position_engine.apply_fill(fill)
        holdings = position_engine.to_broker_holdings()
        assert len(holdings) == 1
        assert holdings[0].symbol == "RELIANCE"

    def test_reset(self, position_engine: PositionEngine) -> None:
        fill = PaperFill(
            fill_id="f1",
            order_id="o1",
            broker_order_id="b1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            quantity=10,
            price=Decimal("2500.00"),
        )
        position_engine.apply_fill(fill)
        position_engine.reset()
        assert position_engine.open_positions() == []

    def test_invalid_fill_raises(self, position_engine: PositionEngine) -> None:
        fill = PaperFill(
            fill_id="f1",
            order_id="o1",
            broker_order_id="b1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            quantity=0,
            price=Decimal("2500.00"),
        )
        with pytest.raises(PaperPositionError):
            position_engine.apply_fill(fill)

    def test_all_positions_includes_closed(
        self, position_engine: PositionEngine
    ) -> None:
        f1 = PaperFill(
            fill_id="f1",
            order_id="o1",
            broker_order_id="b1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            quantity=10,
            price=Decimal("2500.00"),
        )
        f2 = PaperFill(
            fill_id="f2",
            order_id="o2",
            broker_order_id="b2",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.SELL,
            quantity=10,
            price=Decimal("2600.00"),
        )
        position_engine.apply_fill(f1)
        position_engine.apply_fill(f2)
        assert len(position_engine.all_positions()) == 1
        assert len(position_engine.open_positions()) == 0


# ===========================================================================
# PaperPortfolio Tests
# ===========================================================================


class TestPaperPortfolio:
    def test_initial_cash(self) -> None:
        pf = PaperPortfolio(initial_cash=Decimal("50000"))
        state = pf.compute_state([])
        assert state.cash == Decimal("50000")
        assert state.equity == Decimal("50000")

    def test_buy_reduces_cash(self, portfolio: PaperPortfolio) -> None:
        fill = PaperFill(
            fill_id="f1",
            order_id="o1",
            broker_order_id="b1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            quantity=10,
            price=Decimal("100.00"),
            commission=Decimal("10.00"),
        )
        portfolio.apply_fill(fill)
        state = portfolio.compute_state([])
        assert state.cash == Decimal("100000") - Decimal("1010.00")

    def test_sell_increases_cash(self, portfolio: PaperPortfolio) -> None:
        fill = PaperFill(
            fill_id="f1",
            order_id="o1",
            broker_order_id="b1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.SELL,
            quantity=10,
            price=Decimal("100.00"),
            commission=Decimal("10.00"),
        )
        portfolio.apply_fill(fill)
        state = portfolio.compute_state([])
        assert state.cash == Decimal("100000") + Decimal("990.00")

    def test_insufficient_cash_raises(self, portfolio: PaperPortfolio) -> None:
        fill = PaperFill(
            fill_id="f1",
            order_id="o1",
            broker_order_id="b1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            quantity=100000,
            price=Decimal("100.00"),
        )
        with pytest.raises(PaperPortfolioError):
            portfolio.apply_fill(fill)

    def test_compute_state_with_positions(self, portfolio: PaperPortfolio) -> None:
        positions = [
            PaperPosition(
                symbol="RELIANCE",
                exchange=Exchange.NSE,
                quantity=10,
                average_price=Decimal("100.00"),
                current_price=Decimal("110.00"),
                buy_quantity=10,
                sell_quantity=0,
            )
        ]
        state = portfolio.compute_state(positions)
        assert state.equity > state.cash

    def test_equity_tracks_pnl(self) -> None:
        pf = PaperPortfolio(initial_cash=Decimal("100000"))
        positions = [
            PaperPosition(
                symbol="HDFC",
                exchange=Exchange.NSE,
                quantity=10,
                average_price=Decimal("100.00"),
                current_price=Decimal("110.00"),
                buy_quantity=10,
                sell_quantity=0,
                realized_pnl=Decimal("0"),
                unrealized_pnl=Decimal("100"),
            )
        ]
        state = pf.compute_state(positions)
        position_value = Decimal("110.00") * Decimal("10")
        assert state.equity == Decimal("100000") + position_value
        assert state.exposure == Decimal("1100")

    def test_to_funds_info(self, portfolio: PaperPortfolio) -> None:
        state = portfolio.compute_state([])
        funds = portfolio.to_funds_info(state)
        assert funds.available_cash == Decimal("100000")

    def test_to_margin_info(self, portfolio: PaperPortfolio) -> None:
        margin = portfolio.to_margin_info()
        assert margin.total_margin == Decimal("100000")

    def test_reset(self, portfolio: PaperPortfolio) -> None:
        fill = PaperFill(
            fill_id="f1",
            order_id="o1",
            broker_order_id="b1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            quantity=10,
            price=Decimal("100.00"),
        )
        portfolio.apply_fill(fill)
        portfolio.reset()
        state = portfolio.compute_state([])
        assert state.cash == Decimal("100000")

    def test_drawdown_computed(self) -> None:
        pf = PaperPortfolio(initial_cash=Decimal("100000"))
        state = pf.compute_state([])
        assert state.drawdown == Decimal("0")


# ===========================================================================
# TradeJournal Tests
# ===========================================================================


class TestTradeJournal:
    def test_record_and_get_order(self, journal: TradeJournal) -> None:
        order = PaperOrder(
            order_id="o1",
            broker_order_id="b1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        journal.record_order(order)
        retrieved = journal.get_order("o1")
        assert retrieved is not None
        assert retrieved.symbol == "RELIANCE"

    def test_get_nonexistent_order(self, journal: TradeJournal) -> None:
        assert journal.get_order("nonexistent") is None

    def test_get_by_broker_id(self, journal: TradeJournal) -> None:
        order = PaperOrder(
            order_id="o1",
            broker_order_id="b1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        journal.record_order(order)
        retrieved = journal.get_order_by_broker_id("b1")
        assert retrieved is not None

    def test_get_by_broker_id_nonexistent(self, journal: TradeJournal) -> None:
        assert journal.get_order_by_broker_id("nonexistent") is None

    def test_record_fill(self, journal: TradeJournal) -> None:
        order = PaperOrder(
            order_id="o1",
            broker_order_id="b1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        journal.record_order(order)

        fill = PaperFill(
            fill_id="f1",
            order_id="o1",
            broker_order_id="b1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            quantity=10,
            price=Decimal("2500.00"),
        )
        journal.record_fill(fill, order)
        updated = journal.get_order("o1")
        assert updated is not None
        assert updated.filled_quantity == 10
        assert updated.status == OrderStatus.FILLED

    def test_record_partial_fill(self, journal: TradeJournal) -> None:
        order = PaperOrder(
            order_id="o1",
            broker_order_id="b1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        journal.record_order(order)

        partial = PaperFill(
            fill_id="f1",
            order_id="o1",
            broker_order_id="b1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            quantity=5,
            price=Decimal("2500.00"),
        )
        journal.record_fill(partial, order)
        updated = journal.get_order("o1")
        assert updated is not None
        assert updated.filled_quantity == 5
        assert updated.pending_quantity == 5
        assert updated.status == OrderStatus.PARTIALLY_FILLED

    def test_record_modification(self, journal: TradeJournal) -> None:
        order = PaperOrder(
            order_id="o1",
            broker_order_id="b1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=10,
            price=Decimal("100.00"),
        )
        journal.record_order(order)
        journal.record_modification(
            order_id="o1",
            field_name="price",
            old_value="100.00",
            new_value="105.00",
        )
        events = journal.events()
        mod_events = [e for e in events if e["type"] == "modification"]
        assert len(mod_events) == 1

    def test_record_cancellation(self, journal: TradeJournal) -> None:
        order = PaperOrder(
            order_id="o1",
            broker_order_id="b1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=10,
            price=Decimal("100.00"),
        )
        journal.record_order(order)
        journal.record_cancellation("o1", reason="User cancelled")
        updated = journal.get_order("o1")
        assert updated is not None
        assert updated.status == OrderStatus.CANCELLED

    def test_to_broker_order(self, journal: TradeJournal) -> None:
        order = PaperOrder(
            order_id="o1",
            broker_order_id="b1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        broker_order = journal.to_broker_order(order)
        assert broker_order.symbol == "RELIANCE"
        assert broker_order.broker_order_id == "b1"

    def test_to_broker_orders_filtered(self, journal: TradeJournal) -> None:
        o1 = PaperOrder(
            order_id="o1",
            broker_order_id="b1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        o2 = PaperOrder(
            order_id="o2",
            broker_order_id="b2",
            symbol="HDFC",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=5,
        )
        journal.record_order(o1)
        journal.record_order(o2)
        results = journal.to_broker_orders(symbol="RELIANCE")
        assert len(results) == 1
        assert results[0].symbol == "RELIANCE"

    def test_to_broker_trades(self, journal: TradeJournal) -> None:
        order = PaperOrder(
            order_id="o1",
            broker_order_id="b1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        journal.record_order(order)
        fill = PaperFill(
            fill_id="f1",
            order_id="o1",
            broker_order_id="b1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            quantity=10,
            price=Decimal("2500.00"),
        )
        journal.record_fill(fill, order)
        trades = journal.to_broker_trades()
        assert len(trades) == 1

    def test_events_log(self, journal: TradeJournal) -> None:
        order = PaperOrder(
            order_id="o1",
            broker_order_id="b1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        journal.record_order(order)
        events = journal.events()
        assert len(events) == 1
        assert events[0]["type"] == "order_placed"

    def test_reset(self, journal: TradeJournal) -> None:
        order = PaperOrder(
            order_id="o1",
            broker_order_id="b1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        journal.record_order(order)
        journal.reset()
        assert journal.all_orders() == []
        assert journal.events() == []


# ===========================================================================
# PerformanceEngine Tests
# ===========================================================================


class TestPerformanceEngine:
    def test_compute_no_journal(self) -> None:
        engine = PerformanceEngine()
        metrics = engine.compute(PaperPortfolioState(cash=Decimal("100000")))
        assert metrics.total_trades == 0

    def test_compute_with_trades(self) -> None:
        journal = TradeJournal()
        order = PaperOrder(
            order_id="o1",
            broker_order_id="b1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        journal.record_order(order)
        buy = PaperFill(
            fill_id="f1",
            order_id="o1",
            broker_order_id="b1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            quantity=10,
            price=Decimal("100.00"),
        )
        journal.record_fill(buy, order)

        engine = PerformanceEngine(journal=journal)
        metrics = engine.compute(PaperPortfolioState(cash=Decimal("100000")))
        assert metrics.total_trades == 1


# ===========================================================================
# PaperBroker Tests
# ===========================================================================


class TestPaperBrokerConstruction:
    def test_default_construction(self) -> None:
        broker = PaperBroker()
        assert broker._initial_cash == Decimal("100000")
        assert not broker.is_connected()

    def test_custom_initial_cash(self) -> None:
        broker = PaperBroker(initial_cash=Decimal("50000"))
        assert broker._initial_cash == Decimal("50000")

    def test_custom_engines_injected(self) -> None:
        fill = FillEngine()
        pos = PositionEngine()
        pf = PaperPortfolio()
        journal = TradeJournal()
        perf = PerformanceEngine()
        broker = PaperBroker(
            initial_cash=Decimal("50000"),
            fill_engine=fill,
            position_engine=pos,
            portfolio=pf,
            journal=journal,
            performance=perf,
        )
        assert broker.fill_engine is fill
        assert broker.position_engine is pos
        assert broker.portfolio is pf
        assert broker.journal is journal
        assert broker.performance is perf


class TestPaperBrokerConnection:
    def test_connect(self) -> None:
        broker = PaperBroker()
        status = broker.connect()
        assert status == ConnectionStatus.CONNECTED
        assert broker.is_connected()

    def test_disconnect(self) -> None:
        broker = PaperBroker()
        broker.connect()
        status = broker.disconnect()
        assert status == ConnectionStatus.DISCONNECTED
        assert not broker.is_connected()

    def test_initial_disconnected(self) -> None:
        broker = PaperBroker()
        assert not broker.is_connected()


class TestPaperBrokerMarketData:
    def test_quote(self, broker: PaperBroker) -> None:
        q = broker.quote("RELIANCE")
        assert q.symbol == "RELIANCE"
        assert q.exchange == Exchange.NSE
        assert q.last_price == Decimal("2500.00")
        assert q.bid is not None
        assert q.ask is not None

    def test_quotes(self, broker: PaperBroker) -> None:
        quotes = broker.quotes(["RELIANCE", "HDFC"])
        assert len(quotes) == 2
        assert "RELIANCE" in quotes
        assert "HDFC" in quotes

    def test_option_chain(self, broker: PaperBroker) -> None:
        chain = broker.option_chain("RELIANCE")
        assert chain == []

    def test_market_depth(self, broker: PaperBroker) -> None:
        depth = broker.market_depth("RELIANCE")
        assert depth.symbol == "RELIANCE"
        assert len(depth.bids) == 5
        assert len(depth.asks) == 5

    def test_ltp(self, broker: PaperBroker) -> None:
        price = broker.ltp("RELIANCE")
        assert price == Decimal("2500.00")

    def test_default_price(self) -> None:
        broker = PaperBroker()
        broker.connect()
        assert broker.ltp("UNKNOWN") == Decimal("100.0")

    def test_set_price(self, broker: PaperBroker) -> None:
        broker.set_price("HDFC", Decimal("1500.00"))
        assert broker.ltp("HDFC") == Decimal("1500.00")


class TestPaperBrokerHistoricalData:
    def test_history(self, broker: PaperBroker) -> None:
        data = broker.history(
            "RELIANCE",
            "1day",
            datetime.now(timezone.utc),
        )
        assert data == []

    def test_intraday(self, broker: PaperBroker) -> None:
        data = broker.intraday("RELIANCE")
        assert data == []

    def test_ohlcv(self, broker: PaperBroker) -> None:
        data = broker.ohlcv("RELIANCE")
        assert data == []


class TestPaperBrokerOrders:
    def test_place_market_buy(self, broker: PaperBroker) -> None:
        request = OrderRequest(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        response = broker.place_order(request)
        assert response.status in (OrderStatus.FILLED,)
        assert response.broker_order_id.startswith("PAPER-")
        assert response.filled_quantity == 10

    def test_place_market_sell(self, broker: PaperBroker) -> None:
        request = OrderRequest(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        response = broker.place_order(request)
        assert response.status == OrderStatus.FILLED

    def test_place_limit_fillable(self, broker: PaperBroker) -> None:
        request = OrderRequest(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=10,
            price=Decimal("2600.00"),
        )
        response = broker.place_order(request)
        assert response.status == OrderStatus.FILLED

    def test_place_limit_not_fillable(self, broker: PaperBroker) -> None:
        request = OrderRequest(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=10,
            price=Decimal("2400.00"),
        )
        response = broker.place_order(request)
        assert response.status == OrderStatus.REJECTED

    def test_place_stop_buy_fillable(self, broker: PaperBroker) -> None:
        request = OrderRequest(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.STOP_LOSS,
            quantity=10,
            trigger_price=Decimal("2400.00"),
        )
        response = broker.place_order(request)
        assert response.status == OrderStatus.FILLED

    def test_place_stop_buy_not_fillable(self, broker: PaperBroker) -> None:
        request = OrderRequest(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.STOP_LOSS,
            quantity=10,
            trigger_price=Decimal("2600.00"),
        )
        response = broker.place_order(request)
        assert response.status == OrderStatus.REJECTED

    def test_place_order_not_connected(self) -> None:
        broker = PaperBroker()
        request = OrderRequest(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        with pytest.raises(PaperOrderError, match="not connected"):
            broker.place_order(request)

    def test_modify_order(self, broker: PaperBroker) -> None:
        request = OrderRequest(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=10,
            price=Decimal("2400.00"),
        )
        response = broker.place_order(request)
        assert response.status == OrderStatus.REJECTED

    def test_modify_order_not_found(self, broker: PaperBroker) -> None:
        req = ModifyOrderRequest(broker_order_id="NONEXISTENT")
        with pytest.raises(PaperOrderError, match="not found"):
            broker.modify_order(req)

    def test_cancel_order(self, broker: PaperBroker) -> None:
        request = OrderRequest(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=10,
            price=Decimal("2400.00"),
        )
        response = broker.place_order(request)
        cancel_req = CancelOrderRequest(broker_order_id=response.broker_order_id)
        cancel_resp = broker.cancel_order(cancel_req)
        assert cancel_resp.status == OrderStatus.CANCELLED

    def test_cancel_order_not_found(self, broker: PaperBroker) -> None:
        req = CancelOrderRequest(broker_order_id="NONEXISTENT")
        with pytest.raises(PaperOrderError, match="not found"):
            broker.cancel_order(req)

    def test_order_lookup(self, broker: PaperBroker) -> None:
        request = OrderRequest(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        response = broker.place_order(request)
        order = broker.order(response.broker_order_id)
        assert order.symbol == "RELIANCE"

    def test_order_lookup_not_found(self, broker: PaperBroker) -> None:
        with pytest.raises(PaperOrderError, match="not found"):
            broker.order("NONEXISTENT")

    def test_orders_filtered(self, broker: PaperBroker) -> None:
        r1 = OrderRequest(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        r2 = OrderRequest(
            symbol="HDFC",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=5,
        )
        broker.set_price("HDFC", Decimal("1500.00"))
        broker.place_order(r1)
        broker.place_order(r2)
        reliance_orders = broker.orders(symbol="RELIANCE")
        assert len(reliance_orders) == 1
        all_orders = broker.orders()
        assert len(all_orders) == 2

    def test_multiple_orders_increment_counter(self, broker: PaperBroker) -> None:
        request = OrderRequest(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        r1 = broker.place_order(request)
        r2 = broker.place_order(request)
        assert r1.broker_order_id != r2.broker_order_id


class TestPaperBrokerPortfolio:
    def test_positions_after_buy(self, broker: PaperBroker) -> None:
        request = OrderRequest(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        broker.place_order(request)
        positions = broker.positions()
        assert len(positions) == 1
        assert positions[0].symbol == "RELIANCE"

    def test_holdings_after_buy(self, broker: PaperBroker) -> None:
        request = OrderRequest(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        broker.place_order(request)
        holdings = broker.holdings()
        assert len(holdings) >= 1

    def test_trades_after_fill(self, broker: PaperBroker) -> None:
        request = OrderRequest(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        broker.place_order(request)
        trades = broker.trades()
        assert len(trades) == 1

    def test_funds_after_buy(self, broker: PaperBroker) -> None:
        request = OrderRequest(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        broker.place_order(request)
        funds = broker.funds()
        assert funds.available_cash is not None
        assert funds.available_cash < Decimal("100000")

    def test_margin(self, broker: PaperBroker) -> None:
        margin = broker.margin()
        assert margin.total_margin is not None

    def test_profile(self, broker: PaperBroker) -> None:
        profile = broker.profile()
        assert profile.name == "Paper Trader"
        assert profile.broker == "paper"

    def test_empty_positions(self, broker: PaperBroker) -> None:
        assert broker.positions() == []

    def test_empty_trades(self, broker: PaperBroker) -> None:
        assert broker.trades() == []


class TestPaperBrokerReset:
    def test_reset_clears_state(self, broker: PaperBroker) -> None:
        request = OrderRequest(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        broker.place_order(request)
        broker.reset()
        assert broker.positions() == []
        assert broker.trades() == []

    def test_reset_allows_new_orders(self, broker: PaperBroker) -> None:
        request = OrderRequest(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        broker.place_order(request)
        broker.reset()
        request2 = OrderRequest(
            symbol="HDFC",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=5,
        )
        broker.set_price("HDFC", Decimal("1500.00"))
        response = broker.place_order(request2)
        assert response.status == OrderStatus.FILLED


# ===========================================================================
# PaperTradingReport Tests
# ===========================================================================


class TestPaperTradingReport:
    def test_default_construction(self) -> None:
        report = PaperTradingReport()
        assert report.orders == ()
        assert report.trades == ()
        assert report.portfolio_state.cash == Decimal("0")

    def test_with_data(self) -> None:
        order = PaperOrder(
            order_id="o1",
            broker_order_id="b1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        report = PaperTradingReport(orders=(order,))
        assert len(report.orders) == 1

    def test_is_frozen(self) -> None:
        report = PaperTradingReport()
        with pytest.raises(AttributeError):
            report.orders = ("invalid",)  # type: ignore[assignment]


class TestPaperTradingExplanation:
    def test_default_construction(self) -> None:
        explanation = PaperTradingExplanation()
        assert explanation.execution == ""
        assert explanation.summary == ""

    def test_with_data(self) -> None:
        explanation = PaperTradingExplanation(
            execution="Executed 5 orders",
            summary="Paper trading completed",
        )
        assert explanation.execution == "Executed 5 orders"
        assert explanation.summary == "Paper trading completed"


# ===========================================================================
# Evidence Generation Tests
# ===========================================================================


class TestEvidenceGeneration:
    def test_generate_evidence_default(self) -> None:
        report = PaperTradingReport()
        evidence = generate_evidence(report)
        assert evidence.category.value == "execution"
        assert evidence.source == "titan.paper"

    def test_generate_evidence_with_trades(self) -> None:
        state = PaperPortfolioState(
            cash=Decimal("90000"),
            equity=Decimal("95000"),
            total_pnl=Decimal("5000"),
        )
        report = PaperTradingReport(portfolio_state=state)
        evidence = generate_evidence(report)
        assert evidence.signal.value == "bullish"

    def test_generate_evidence_loss(self) -> None:
        state = PaperPortfolioState(
            cash=Decimal("80000"),
            equity=Decimal("75000"),
            total_pnl=Decimal("-5000"),
        )
        report = PaperTradingReport(portfolio_state=state)
        evidence = generate_evidence(report)
        assert evidence.signal.value == "bearish"

    def test_generate_evidence_metadata(self) -> None:
        report = PaperTradingReport()
        evidence = generate_evidence(report)
        assert evidence.metadata.get("paper_execution") is True
        assert evidence.metadata.get("simulation") is True
        assert evidence.metadata.get("fill_quality") == "deterministic"

    def test_generate_explanation_default(self) -> None:
        report = PaperTradingReport()
        explanation = generate_explanation(report)
        assert "0" in explanation.execution

    def test_generate_explanation_with_orders(self) -> None:
        order = PaperOrder(
            order_id="o1",
            broker_order_id="b1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
            status=OrderStatus.FILLED,
            filled_quantity=10,
        )
        report = PaperTradingReport(orders=(order,))
        explanation = generate_explanation(report)
        assert "1" in explanation.execution


# ===========================================================================
# Serialization Tests
# ===========================================================================


class TestSerialization:
    def test_paper_fill_serializable(self) -> None:
        fill = PaperFill(
            fill_id="f1",
            order_id="o1",
            broker_order_id="b1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            quantity=10,
            price=Decimal("2500.00"),
        )
        data = {
            "fill_id": fill.fill_id,
            "order_id": fill.order_id,
            "quantity": fill.quantity,
            "price": str(fill.price),
        }
        json_str = json.dumps(data)
        assert json_str is not None

    def test_portfolio_state_serializable(self) -> None:
        state = PaperPortfolioState(
            cash=Decimal("100000"),
            equity=Decimal("105000"),
        )
        data = {
            "cash": str(state.cash),
            "equity": str(state.equity),
        }
        json_str = json.dumps(data)
        assert json_str is not None


# ===========================================================================
# BrokerType Registration Test
# ===========================================================================


class TestBrokerType:
    def test_paper_broker_type_exists(self) -> None:
        assert BrokerType.PAPER.value == "paper"


# ===========================================================================
# Exception Tests
# ===========================================================================


class TestExceptions:
    def test_paper_trading_error(self) -> None:
        with pytest.raises(PaperTradingError):
            raise PaperOrderError("test")

    def test_exception_hierarchy(self) -> None:
        assert issubclass(PaperOrderError, PaperTradingError)
        assert issubclass(PaperFillError, PaperTradingError)
        assert issubclass(PaperPortfolioError, PaperTradingError)
