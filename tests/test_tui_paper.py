"""Tests for TITAN TUI Paper Trading screen — models, widgets, helpers, screen, app."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from titan.tui.layout import (
    TITANApp,
    _format_inr,
    _format_pnl,
    _format_uptime,
    _read_paper_accounts,
    _read_paper_orders,
    _read_paper_performance,
    _read_paper_portfolio,
    _read_paper_positions,
    _read_paper_session,
    _read_paper_trades,
    build_paper_state,
)
from titan.tui.models import (
    PaperAccountInfo,
    PaperOrderEntry,
    PaperPerformanceInfo,
    PaperPortfolioInfo,
    PaperPositionEntry,
    PaperScreenState,
    PaperSessionInfo,
    PaperTradeEntry,
)
from titan.tui.screens.paper import PaperScreen
from titan.tui.widgets.paper import (
    AccountSummaryWidget,
    ActiveOrdersWidget,
    PaperSessionWidget,
    PerformanceWidget,
    PortfolioWidget,
    PositionWidget,
    TradeHistoryWidget,
    _pnl_class,
)

# ──────────────────────────────────────────────────
# Model tests
# ──────────────────────────────────────────────────


class TestPaperSessionInfo:
    def test_defaults(self) -> None:
        info = PaperSessionInfo()
        assert info.status == "Stopped"
        assert info.started == "--:--"
        assert info.duration == "00:00"

    def test_custom(self) -> None:
        info = PaperSessionInfo(status="Running", started="09:15", duration="02:48")
        assert info.status == "Running"
        assert info.started == "09:15"
        assert info.duration == "02:48"

    def test_frozen(self) -> None:
        info = PaperSessionInfo()
        with pytest.raises(AttributeError):
            info.status = "Stopped"  # type: ignore[misc]


class TestPaperAccountInfo:
    def test_defaults(self) -> None:
        info = PaperAccountInfo()
        assert info.available_cash == "₹0"
        assert info.used_margin == "₹0"
        assert info.available_margin == "₹0"
        assert info.payin == "₹0"
        assert info.payout == "₹0"

    def test_custom(self) -> None:
        info = PaperAccountInfo(
            available_cash="₹98,450",
            used_margin="₹12,000",
            available_margin="₹88,000",
            payin="₹50,000",
            payout="₹0",
        )
        assert info.available_cash == "₹98,450"
        assert info.used_margin == "₹12,000"
        assert info.available_margin == "₹88,000"

    def test_frozen(self) -> None:
        info = PaperAccountInfo()
        with pytest.raises(AttributeError):
            info.available_cash = "₹0"  # type: ignore[misc]


class TestPaperOrderEntry:
    def test_defaults(self) -> None:
        entry = PaperOrderEntry()
        assert entry.order_id == ""
        assert entry.symbol == ""
        assert entry.side == ""
        assert entry.quantity == 0

    def test_custom(self) -> None:
        entry = PaperOrderEntry(
            order_id="O001",
            symbol="RELIANCE",
            side="buy",
            order_type="LIMIT",
            quantity=10,
            filled_quantity=5,
            price="₹2,450",
            status="PARTIALLY_FILLED",
            placed_at="09:15",
        )
        assert entry.order_id == "O001"
        assert entry.symbol == "RELIANCE"
        assert entry.side == "buy"
        assert entry.filled_quantity == 5

    def test_frozen(self) -> None:
        entry = PaperOrderEntry()
        with pytest.raises(AttributeError):
            entry.symbol = "X"  # type: ignore[misc]


class TestPaperPortfolioInfo:
    def test_defaults(self) -> None:
        info = PaperPortfolioInfo()
        assert info.cash == "₹0"
        assert info.equity == "₹0"
        assert info.unrealized_pnl == "+₹0"
        assert info.realized_pnl == "+₹0"

    def test_custom(self) -> None:
        info = PaperPortfolioInfo(
            cash="₹198,450",
            equity="₹201,830",
            unrealized_pnl="+₹2,140",
            realized_pnl="+₹1,240",
        )
        assert info.cash == "₹198,450"
        assert info.equity == "₹201,830"

    def test_frozen(self) -> None:
        info = PaperPortfolioInfo()
        with pytest.raises(AttributeError):
            info.cash = "₹0"  # type: ignore[misc]


class TestPaperPerformanceInfo:
    def test_defaults(self) -> None:
        info = PaperPerformanceInfo()
        assert info.total_trades == 0
        assert info.win_rate == "0%"
        assert info.profit_factor == "0.00"
        assert info.expectancy == "+0.00R"
        assert info.max_drawdown == "0%"

    def test_custom(self) -> None:
        info = PaperPerformanceInfo(
            total_trades=18,
            win_rate="72%",
            profit_factor="2.31",
            expectancy="+1.42R",
            max_drawdown="-1.8%",
        )
        assert info.total_trades == 18
        assert info.win_rate == "72%"

    def test_frozen(self) -> None:
        info = PaperPerformanceInfo()
        with pytest.raises(AttributeError):
            info.total_trades = 1  # type: ignore[misc]


class TestPaperPositionEntry:
    def test_defaults(self) -> None:
        entry = PaperPositionEntry()
        assert entry.symbol == ""
        assert entry.quantity == 0

    def test_custom(self) -> None:
        entry = PaperPositionEntry(
            symbol="RELIANCE",
            quantity=10,
            avg_price="₹2,450",
            current_price="₹2,470",
            unrealized_pnl="+₹200",
        )
        assert entry.symbol == "RELIANCE"
        assert entry.quantity == 10

    def test_frozen(self) -> None:
        entry = PaperPositionEntry()
        with pytest.raises(AttributeError):
            entry.symbol = "X"  # type: ignore[misc]


class TestPaperTradeEntry:
    def test_defaults(self) -> None:
        entry = PaperTradeEntry()
        assert entry.symbol == ""
        assert entry.side == ""
        assert entry.quantity == 0

    def test_custom(self) -> None:
        entry = PaperTradeEntry(
            symbol="INFY", side="buy", quantity=5, price="₹1,500", pnl="+₹75"
        )
        assert entry.symbol == "INFY"
        assert entry.side == "buy"

    def test_frozen(self) -> None:
        entry = PaperTradeEntry()
        with pytest.raises(AttributeError):
            entry.symbol = "X"  # type: ignore[misc]


class TestPaperScreenState:
    def test_defaults(self) -> None:
        state = PaperScreenState()
        assert isinstance(state.session, PaperSessionInfo)
        assert isinstance(state.account, PaperAccountInfo)
        assert isinstance(state.portfolio, PaperPortfolioInfo)
        assert isinstance(state.performance, PaperPerformanceInfo)
        assert state.positions == ()
        assert state.orders == ()
        assert state.trades == ()
        assert state.last_refresh == ""

    def test_frozen(self) -> None:
        state = PaperScreenState()
        with pytest.raises(AttributeError):
            state.last_refresh = "12:00"  # type: ignore[misc]

    def test_with_positions(self) -> None:
        pos = (PaperPositionEntry(symbol="RELIANCE"),)
        state = PaperScreenState(positions=pos)
        assert len(state.positions) == 1
        assert state.positions[0].symbol == "RELIANCE"

    def test_with_trades(self) -> None:
        trades = (PaperTradeEntry(symbol="INFY", side="buy"),)
        state = PaperScreenState(trades=trades)
        assert len(state.trades) == 1

    def test_with_orders(self) -> None:
        orders = (PaperOrderEntry(symbol="RELIANCE", side="buy"),)
        state = PaperScreenState(orders=orders)
        assert len(state.orders) == 1
        assert state.orders[0].symbol == "RELIANCE"

    def test_with_account(self) -> None:
        acct = PaperAccountInfo(available_cash="₹98,450")
        state = PaperScreenState(account=acct)
        assert state.account.available_cash == "₹98,450"


# ──────────────────────────────────────────────────
# Helper function tests
# ──────────────────────────────────────────────────


class TestPnlClass:
    def test_positive(self) -> None:
        assert _pnl_class("+₹200") == "value-positive"

    def test_negative(self) -> None:
        assert _pnl_class("-₹150") == "value-negative"

    def test_zero(self) -> None:
        assert _pnl_class("+₹0") == "value-positive"

    def test_minus_sign(self) -> None:
        assert _pnl_class("-₹1,240") == "value-negative"

    def test_plain_positive_number(self) -> None:
        assert _pnl_class("₹500") == "value-positive"

    def test_plain_zero(self) -> None:
        result = _pnl_class("₹0")
        assert result in ("value-positive", "value-neutral")


class TestFormatPnl:
    def test_positive_decimal(self) -> None:
        assert _format_pnl(Decimal(2140)) == "+₹2,140"

    def test_negative_decimal(self) -> None:
        assert _format_pnl(Decimal(-1240)) == "-₹1,240"

    def test_zero(self) -> None:
        assert _format_pnl(Decimal(0)) == "+₹0"

    def test_float_input(self) -> None:
        result = _format_pnl(1500.0)
        assert result == "+₹1,500"

    def test_string_input(self) -> None:
        result = _format_pnl("500")
        assert result == "+₹500"

    def test_invalid_input(self) -> None:
        result = _format_pnl("abc")
        assert result == "+₹0"


class TestFormatInr:
    def test_positive_decimal(self) -> None:
        assert _format_inr(Decimal(2140)) == "₹2,140"

    def test_negative_decimal(self) -> None:
        assert _format_inr(Decimal(-1240)) == "-₹1,240"

    def test_zero(self) -> None:
        assert _format_inr(Decimal(0)) == "₹0"

    def test_none(self) -> None:
        assert _format_inr(None) == "₹0"

    def test_float_input(self) -> None:
        assert _format_inr(1500.0) == "₹1,500"

    def test_string_input(self) -> None:
        assert _format_inr("500") == "₹500"

    def test_invalid_input(self) -> None:
        assert _format_inr("abc") == "₹0"


class TestFormatUptime:
    def test_zero(self) -> None:
        assert _format_uptime(0) == "00:00:00"

    def test_hours_minutes_seconds(self) -> None:
        assert _format_uptime(3661) == "01:01:01"


# ──────────────────────────────────────────────────
# Widget tests
# ──────────────────────────────────────────────────


class TestPaperSessionWidget:
    def test_init(self) -> None:
        w = PaperSessionWidget()
        assert w._info.status == "Stopped"

    def test_update_data_running(self) -> None:
        w = PaperSessionWidget()
        info = PaperSessionInfo(status="Running", started="09:15", duration="02:48")
        w.update_data(info)
        assert w._info.status == "Running"

    def test_update_data_stopped(self) -> None:
        w = PaperSessionWidget()
        info = PaperSessionInfo(status="Stopped")
        w.update_data(info)
        assert w._info.status == "Stopped"

    def test_render_returns_empty_string(self) -> None:
        w = PaperSessionWidget()
        assert w.render() == ""


class TestAccountSummaryWidget:
    def test_init(self) -> None:
        w = AccountSummaryWidget()
        assert w._info.available_cash == "₹0"

    def test_update_data(self) -> None:
        w = AccountSummaryWidget()
        info = PaperAccountInfo(
            available_cash="₹98,450",
            used_margin="₹12,000",
            available_margin="₹88,000",
            payin="₹50,000",
            payout="₹0",
        )
        w.update_data(info)
        assert w._info.available_cash == "₹98,450"
        assert w._info.used_margin == "₹12,000"

    def test_update_data_defaults(self) -> None:
        w = AccountSummaryWidget()
        info = PaperAccountInfo()
        w.update_data(info)
        assert w._info.available_cash == "₹0"

    def test_render_returns_empty_string(self) -> None:
        w = AccountSummaryWidget()
        assert w.render() == ""


class TestActiveOrdersWidget:
    def test_init(self) -> None:
        w = ActiveOrdersWidget()
        assert w._orders == ()

    def test_update_data_empty(self) -> None:
        w = ActiveOrdersWidget()
        w.update_data(())
        assert w._orders == ()

    def test_update_data_with_orders(self) -> None:
        w = ActiveOrdersWidget()
        orders = (
            PaperOrderEntry(
                order_id="O001",
                symbol="RELIANCE",
                side="buy",
                order_type="LIMIT",
                quantity=10,
                filled_quantity=0,
                price="₹2,450",
                status="PENDING",
            ),
            PaperOrderEntry(
                order_id="O002",
                symbol="INFY",
                side="sell",
                order_type="MARKET",
                quantity=5,
                filled_quantity=0,
                price="₹1,500",
                status="OPEN",
            ),
        )
        w.update_data(orders)
        assert len(w._orders) == 2

    def test_update_data_replaces_previous(self) -> None:
        w = ActiveOrdersWidget()
        w.update_data((PaperOrderEntry(symbol="A", side="buy"),))
        assert len(w._orders) == 1
        w.update_data(())
        assert len(w._orders) == 0

    def test_render_returns_empty_string(self) -> None:
        w = ActiveOrdersWidget()
        assert w.render() == ""


class TestPortfolioWidget:
    def test_init(self) -> None:
        w = PortfolioWidget()
        assert w._info.cash == "₹0"

    def test_update_data(self) -> None:
        w = PortfolioWidget()
        info = PaperPortfolioInfo(
            cash="₹198,450",
            equity="₹201,830",
            unrealized_pnl="+₹2,140",
            realized_pnl="+₹1,240",
        )
        w.update_data(info)
        assert w._info.cash == "₹198,450"

    def test_update_data_negative_pnl(self) -> None:
        w = PortfolioWidget()
        info = PaperPortfolioInfo(unrealized_pnl="-₹500", realized_pnl="-₹200")
        w.update_data(info)
        assert w._info.unrealized_pnl == "-₹500"

    def test_render_returns_empty_string(self) -> None:
        w = PortfolioWidget()
        assert w.render() == ""


class TestPerformanceWidget:
    def test_init(self) -> None:
        w = PerformanceWidget()
        assert w._info.total_trades == 0

    def test_update_data(self) -> None:
        w = PerformanceWidget()
        info = PaperPerformanceInfo(
            total_trades=18,
            win_rate="72%",
            profit_factor="2.31",
            expectancy="+1.42R",
            max_drawdown="-1.8%",
        )
        w.update_data(info)
        assert w._info.total_trades == 18
        assert w._info.win_rate == "72%"

    def test_update_data_defaults(self) -> None:
        w = PerformanceWidget()
        info = PaperPerformanceInfo()
        w.update_data(info)
        assert w._info.profit_factor == "0.00"

    def test_render_returns_empty_string(self) -> None:
        w = PerformanceWidget()
        assert w.render() == ""


class TestPositionWidget:
    def test_init(self) -> None:
        w = PositionWidget()
        assert w._positions == ()

    def test_update_data_empty(self) -> None:
        w = PositionWidget()
        w.update_data(())
        assert w._positions == ()

    def test_update_data_with_positions(self) -> None:
        w = PositionWidget()
        positions = (
            PaperPositionEntry(symbol="RELIANCE", quantity=10),
            PaperPositionEntry(symbol="INFY", quantity=5),
        )
        w.update_data(positions)
        assert len(w._positions) == 2

    def test_update_data_replaces_previous(self) -> None:
        w = PositionWidget()
        w.update_data((PaperPositionEntry(symbol="A"),))
        assert len(w._positions) == 1
        w.update_data(())
        assert len(w._positions) == 0

    def test_render_returns_empty_string(self) -> None:
        w = PositionWidget()
        assert w.render() == ""


class TestTradeHistoryWidget:
    def test_init(self) -> None:
        w = TradeHistoryWidget()
        assert w._trades == ()

    def test_update_data_empty(self) -> None:
        w = TradeHistoryWidget()
        w.update_data(())
        assert w._trades == ()

    def test_update_data_with_trades(self) -> None:
        w = TradeHistoryWidget()
        trades = (
            PaperTradeEntry(symbol="RELIANCE", side="buy", quantity=10),
            PaperTradeEntry(symbol="INFY", side="sell", quantity=5),
        )
        w.update_data(trades)
        assert len(w._trades) == 2

    def test_update_data_replaces_previous(self) -> None:
        w = TradeHistoryWidget()
        w.update_data((PaperTradeEntry(symbol="A", side="buy"),))
        assert len(w._trades) == 1
        w.update_data(())
        assert len(w._trades) == 0

    def test_render_returns_empty_string(self) -> None:
        w = TradeHistoryWidget()
        assert w.render() == ""


# ──────────────────────────────────────────────────
# Screen unit tests
# ──────────────────────────────────────────────────


class TestPaperScreenUnit:
    def test_screen_creation(self) -> None:
        screen = PaperScreen()
        assert screen is not None

    def test_default_state(self) -> None:
        screen = PaperScreen()
        assert isinstance(screen.state, PaperScreenState)

    def test_set_state_builder(self) -> None:
        screen = PaperScreen()

        def builder() -> PaperScreenState:
            return PaperScreenState()

        screen.set_state_builder(builder)
        assert screen._state_builder is builder

    def test_refresh_state_with_builder(self) -> None:
        screen = PaperScreen()
        custom = PaperScreenState(
            session=PaperSessionInfo(status="Running"),
        )
        screen.set_state_builder(lambda: custom)
        screen._refresh_state()
        assert screen.state.session.status == "Running"

    def test_refresh_state_without_builder(self) -> None:
        screen = PaperScreen()
        screen._refresh_state()
        assert isinstance(screen.state, PaperScreenState)

    def test_refresh_state_builder_exception(self) -> None:
        screen = PaperScreen()
        screen.set_state_builder(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        screen._refresh_state()
        assert isinstance(screen.state, PaperScreenState)

    def test_update_widgets_before_compose(self) -> None:
        screen = PaperScreen()
        screen._state = PaperScreenState(
            session=PaperSessionInfo(status="Running"),
        )
        screen._update_widgets()
        assert screen._session_widget is None

    def test_bindings_exist(self) -> None:
        keys = [b[0] for b in PaperScreen.BINDINGS]
        assert "q" in keys
        assert "r" in keys
        assert "escape" in keys

    def test_paging_bindings_exist(self) -> None:
        keys = [b[0] for b in PaperScreen.BINDINGS]
        assert "page_up" in keys
        assert "page_down" in keys
        assert "home" in keys
        assert "end" in keys

    def test_scroll_actions_exist(self) -> None:
        screen = PaperScreen()
        assert hasattr(screen, "action_scroll_up")
        assert hasattr(screen, "action_scroll_down")
        assert hasattr(screen, "action_scroll_top")
        assert hasattr(screen, "action_scroll_bottom")

    def test_scroll_actions_with_no_container(self) -> None:
        screen = PaperScreen()
        screen.action_scroll_up()
        screen.action_scroll_down()
        screen.action_scroll_top()
        screen.action_scroll_bottom()


# ──────────────────────────────────────────────────
# App tests
# ──────────────────────────────────────────────────


class TestTITANAppPaper:
    def test_app_creation(self) -> None:
        app = TITANApp()
        assert app is not None

    def test_set_paper_state_builder(self) -> None:
        app = TITANApp()

        def builder() -> PaperScreenState:
            return PaperScreenState()

        app.set_paper_state_builder(builder)
        assert app._paper_state_builder is builder

    def test_f3_binding_exists(self) -> None:
        keys = [b[0] for b in TITANApp.BINDINGS]
        assert "f3" in keys


# ──────────────────────────────────────────────────
# State builder unit tests (with mocked broker)
# ──────────────────────────────────────────────────


def _make_mock_broker(
    connected: bool = True,
    initial_cash: Decimal = Decimal(100000),
) -> MagicMock:
    broker = MagicMock()
    broker.is_connected.return_value = connected
    broker._initial_cash = initial_cash
    return broker


def _make_mock_portfolio_state(
    cash: Decimal = Decimal(98450),
    equity: Decimal = Decimal(101830),
    total_pnl: Decimal = Decimal(1830),
) -> MagicMock:
    ps = MagicMock()
    ps.cash = cash
    ps.equity = equity
    ps.total_pnl = total_pnl
    ps.daily_pnl = Decimal(500)
    ps.drawdown = Decimal("0.018")
    return ps


def _make_mock_performance() -> MagicMock:
    perf = MagicMock()
    perf.total_trades = 18
    perf.winning_trades = 13
    perf.losing_trades = 5
    perf.win_rate = 0.7222
    perf.loss_rate = 0.2778
    perf.profit_factor = 2.31
    perf.expectancy = Decimal("1.42")
    perf.max_drawdown = Decimal("0.018")
    return perf


class TestBuildPaperState:
    @patch("titan.cli.commands.paper._paper_start_time", None)
    @patch("titan.cli.commands.paper._get_broker", return_value=None)
    def test_no_broker(self, mock_broker: MagicMock) -> None:
        state = build_paper_state()
        assert state.session.status == "Stopped"

    @patch("titan.cli.commands.paper._paper_start_time", None)
    @patch("titan.cli.commands.paper._get_broker")
    def test_with_broker(self, mock_broker: MagicMock) -> None:
        broker = _make_mock_broker()
        broker.position_engine.open_positions.return_value = []
        broker.position_engine.all_positions.return_value = []
        broker.portfolio.compute_state.return_value = _make_mock_portfolio_state()
        broker.performance.compute.return_value = _make_mock_performance()
        broker.journal.to_broker_trades.return_value = []
        mock_broker.return_value = broker
        state = build_paper_state()
        assert state.session.status == "Running"


class TestReadPaperSession:
    @patch("titan.cli.commands.paper._paper_start_time", None)
    @patch("titan.cli.commands.paper._get_broker", return_value=None)
    def test_no_broker(self, mock_broker: MagicMock) -> None:
        info = _read_paper_session()
        assert info.status == "Stopped"

    @patch("titan.cli.commands.paper._paper_start_time", None)
    @patch("titan.cli.commands.paper._get_broker")
    def test_broker_not_connected(self, mock_broker: MagicMock) -> None:
        broker = _make_mock_broker(connected=False)
        mock_broker.return_value = broker
        info = _read_paper_session()
        assert info.status == "Stopped"

    @patch("titan.cli.commands.paper._get_broker", side_effect=RuntimeError)
    def test_exception(self, mock_broker: MagicMock) -> None:
        info = _read_paper_session()
        assert info.status == "Stopped"


class TestReadPaperAccounts:
    @patch("titan.cli.commands.paper._get_broker", return_value=None)
    def test_no_broker(self, mock_broker: MagicMock) -> None:
        info = _read_paper_accounts()
        assert info.available_cash == "₹0"

    @patch("titan.cli.commands.paper._get_broker")
    def test_with_broker(self, mock_broker: MagicMock) -> None:
        broker = _make_mock_broker()
        funds = MagicMock()
        funds.available_cash = Decimal(98450)
        funds.used_cash = Decimal(1550)
        funds.payin = Decimal(50000)
        funds.payout = Decimal(0)
        funds.realised_pnl = Decimal(1240)
        funds.unrealised_pnl = Decimal(2140)
        broker.funds.return_value = funds
        margin = MagicMock()
        margin.total_margin = Decimal(100000)
        margin.used_margin = Decimal(12000)
        margin.available_margin = Decimal(88000)
        margin.delivery_margin = None
        margin.span_margin = None
        margin.exposure_margin = None
        broker.margin.return_value = margin
        mock_broker.return_value = broker
        info = _read_paper_accounts()
        assert "98,450" in info.available_cash
        assert "12,000" in info.used_margin
        assert "88,000" in info.available_margin
        assert "50,000" in info.payin

    @patch("titan.cli.commands.paper._get_broker", side_effect=RuntimeError)
    def test_exception(self, mock_broker: MagicMock) -> None:
        info = _read_paper_accounts()
        assert info.available_cash == "₹0"


class TestReadPaperOrders:
    @patch("titan.cli.commands.paper._get_broker", return_value=None)
    def test_no_broker(self, mock_broker: MagicMock) -> None:
        result = _read_paper_orders()
        assert result == ()

    @patch("titan.cli.commands.paper._get_broker")
    def test_empty_orders(self, mock_broker: MagicMock) -> None:
        broker = _make_mock_broker()
        broker.orders.return_value = []
        mock_broker.return_value = broker
        result = _read_paper_orders()
        assert result == ()

    @patch("titan.cli.commands.paper._get_broker")
    def test_with_pending_order(self, mock_broker: MagicMock) -> None:
        from titan.brokers.models import OrderSide, OrderStatus, OrderType

        order = MagicMock()
        order.broker_order_id = "O001"
        order.symbol = "RELIANCE"
        order.side = OrderSide.BUY
        order.order_type = OrderType.LIMIT
        order.quantity = 10
        order.filled_quantity = 0
        order.average_price = None
        order.price = Decimal(2450)
        order.status = OrderStatus.PENDING
        order.placed_at = None
        broker = _make_mock_broker()
        broker.orders.return_value = [order]
        mock_broker.return_value = broker
        result = _read_paper_orders()
        assert len(result) == 1
        assert result[0].symbol == "RELIANCE"
        assert result[0].status == "pending"

    @patch("titan.cli.commands.paper._get_broker")
    def test_filters_filled_orders(self, mock_broker: MagicMock) -> None:
        from titan.brokers.models import OrderStatus

        filled = MagicMock()
        filled.status = OrderStatus.FILLED
        filled.broker_order_id = "O001"
        broker = _make_mock_broker()
        broker.orders.return_value = [filled]
        mock_broker.return_value = broker
        result = _read_paper_orders()
        assert result == ()

    @patch("titan.cli.commands.paper._get_broker")
    def test_with_partially_filled_order(self, mock_broker: MagicMock) -> None:
        from titan.brokers.models import OrderStatus

        order = MagicMock()
        order.broker_order_id = "O002"
        order.symbol = "INFY"
        order.side.value = "sell"
        order.order_type.value = "market"
        order.quantity = 5
        order.filled_quantity = 2
        order.average_price = Decimal(1500)
        order.price = None
        order.status = OrderStatus.PARTIALLY_FILLED
        order.placed_at = MagicMock()
        order.placed_at.strftime.return_value = "10:30"
        broker = _make_mock_broker()
        broker.orders.return_value = [order]
        mock_broker.return_value = broker
        result = _read_paper_orders()
        assert len(result) == 1
        assert result[0].filled_quantity == 2
        assert result[0].placed_at == "10:30"

    @patch("titan.cli.commands.paper._get_broker", side_effect=RuntimeError)
    def test_exception(self, mock_broker: MagicMock) -> None:
        result = _read_paper_orders()
        assert result == ()


class TestReadPaperPortfolio:
    @patch("titan.cli.commands.paper._get_broker", return_value=None)
    def test_no_broker(self, mock_broker: MagicMock) -> None:
        info = _read_paper_portfolio()
        assert info.cash == "₹0"

    @patch("titan.cli.commands.paper._get_broker")
    def test_with_broker(self, mock_broker: MagicMock) -> None:
        broker = _make_mock_broker()
        broker.position_engine.open_positions.return_value = []
        broker.position_engine.all_positions.return_value = []
        broker.portfolio.compute_state.return_value = _make_mock_portfolio_state()
        mock_broker.return_value = broker
        info = _read_paper_portfolio()
        assert "98,450" in info.cash
        assert "101,830" in info.equity

    @patch("titan.cli.commands.paper._get_broker", side_effect=RuntimeError)
    def test_exception(self, mock_broker: MagicMock) -> None:
        info = _read_paper_portfolio()
        assert info.cash == "₹0"


class TestReadPaperPerformance:
    @patch("titan.cli.commands.paper._get_broker", return_value=None)
    def test_no_broker(self, mock_broker: MagicMock) -> None:
        info = _read_paper_performance()
        assert info.total_trades == 0

    @patch("titan.cli.commands.paper._get_broker")
    def test_with_broker(self, mock_broker: MagicMock) -> None:
        broker = _make_mock_broker()
        broker.position_engine.open_positions.return_value = []
        broker.portfolio.compute_state.return_value = _make_mock_portfolio_state()
        broker.performance.compute.return_value = _make_mock_performance()
        mock_broker.return_value = broker
        info = _read_paper_performance()
        assert info.total_trades == 18
        assert info.win_rate == "72%"
        assert info.profit_factor == "2.31"

    @patch("titan.cli.commands.paper._get_broker", side_effect=RuntimeError)
    def test_exception(self, mock_broker: MagicMock) -> None:
        info = _read_paper_performance()
        assert info.total_trades == 0


class TestReadPaperPositions:
    @patch("titan.cli.commands.paper._get_broker", return_value=None)
    def test_no_broker(self, mock_broker: MagicMock) -> None:
        result = _read_paper_positions()
        assert result == ()

    @patch("titan.cli.commands.paper._get_broker")
    def test_empty_positions(self, mock_broker: MagicMock) -> None:
        broker = _make_mock_broker()
        broker.position_engine.open_positions.return_value = []
        mock_broker.return_value = broker
        result = _read_paper_positions()
        assert result == ()

    @patch("titan.cli.commands.paper._get_broker")
    def test_with_positions(self, mock_broker: MagicMock) -> None:
        pos = MagicMock()
        pos.symbol = "RELIANCE"
        pos.quantity = 10
        pos.average_price = Decimal(2450)
        pos.current_price = Decimal(2470)
        pos.unrealized_pnl = Decimal(200)
        broker = _make_mock_broker()
        broker.position_engine.open_positions.return_value = [pos]
        mock_broker.return_value = broker
        result = _read_paper_positions()
        assert len(result) == 1
        assert result[0].symbol == "RELIANCE"

    @patch("titan.cli.commands.paper._get_broker", side_effect=RuntimeError)
    def test_exception(self, mock_broker: MagicMock) -> None:
        result = _read_paper_positions()
        assert result == ()


class TestReadPaperTrades:
    @patch("titan.cli.commands.paper._get_broker", return_value=None)
    def test_no_broker(self, mock_broker: MagicMock) -> None:
        result = _read_paper_trades()
        assert result == ()

    @patch("titan.cli.commands.paper._get_broker")
    def test_empty_trades(self, mock_broker: MagicMock) -> None:
        broker = _make_mock_broker()
        broker.journal.to_broker_trades.return_value = []
        mock_broker.return_value = broker
        result = _read_paper_trades()
        assert result == ()

    @patch("titan.cli.commands.paper._get_broker")
    def test_with_trades(self, mock_broker: MagicMock) -> None:
        trade = MagicMock()
        trade.symbol = "INFY"
        trade.side.value = "buy"
        trade.quantity = 5
        trade.price = Decimal(1500)
        trade.pnl = Decimal(75)
        trade.timestamp = MagicMock()
        trade.timestamp.strftime.return_value = "10:30"
        broker = _make_mock_broker()
        broker.journal.to_broker_trades.return_value = [trade]
        mock_broker.return_value = broker
        result = _read_paper_trades()
        assert len(result) == 1
        assert result[0].symbol == "INFY"
        assert result[0].side == "buy"

    @patch("titan.cli.commands.paper._get_broker", side_effect=RuntimeError)
    def test_exception(self, mock_broker: MagicMock) -> None:
        result = _read_paper_trades()
        assert result == ()


# ──────────────────────────────────────────────────
# Async integration tests
# ──────────────────────────────────────────────────


class TestPaperAsync:
    @pytest.mark.asyncio
    async def test_paper_screen_pushes(self) -> None:
        app = TITANApp()
        async with app.run_test() as pilot:
            screen = PaperScreen()
            app.push_screen(screen)
            await pilot.pause()
            assert isinstance(app.screen, PaperScreen)

    @pytest.mark.asyncio
    async def test_paper_screen_widgets_mounted(self) -> None:
        app = TITANApp()
        async with app.run_test() as pilot:
            screen = PaperScreen()
            app.push_screen(screen)
            await pilot.pause()
            assert screen.query_one("#session-widget") is not None
            assert screen.query_one("#account-widget") is not None
            assert screen.query_one("#portfolio-widget") is not None
            assert screen.query_one("#performance-widget") is not None
            assert screen.query_one("#position-widget") is not None
            assert screen.query_one("#orders-widget") is not None
            assert screen.query_one("#trades-widget") is not None

    @pytest.mark.asyncio
    async def test_paper_title_shown(self) -> None:
        app = TITANApp()
        async with app.run_test() as pilot:
            from textual.widgets import Static

            screen = PaperScreen()
            app.push_screen(screen)
            await pilot.pause()
            title = screen.query_one("#paper-title", Static)
            assert "Paper Trading" in str(title.render())

    @pytest.mark.asyncio
    async def test_paper_refresh_indicator(self) -> None:
        app = TITANApp()
        async with app.run_test() as pilot:
            from textual.widgets import Static

            screen = PaperScreen()
            app.push_screen(screen)
            await pilot.pause()
            indicator = screen.query_one("#refresh-indicator", Static)
            assert indicator is not None

    @pytest.mark.asyncio
    async def test_paper_manual_refresh(self) -> None:
        app = TITANApp()
        async with app.run_test() as pilot:
            from textual.widgets import Static

            screen = PaperScreen()
            app.push_screen(screen)
            await pilot.pause()
            screen.action_refresh()
            indicator = screen.query_one("#refresh-indicator", Static)
            assert "Last refresh:" in str(indicator.render())

    @pytest.mark.asyncio
    async def test_paper_escape_back(self) -> None:
        app = TITANApp()
        async with app.run_test() as pilot:
            from titan.tui.screens.dashboard import DashboardScreen

            screen = PaperScreen()
            app.push_screen(screen)
            await pilot.pause()
            assert isinstance(app.screen, PaperScreen)
            await pilot.press("escape")
            assert isinstance(app.screen, DashboardScreen)

    @pytest.mark.asyncio
    async def test_f3_navigates_to_paper(self) -> None:
        app = TITANApp()
        async with app.run_test() as pilot:
            await pilot.press("f3")
            assert isinstance(app.screen, PaperScreen)

    @pytest.mark.asyncio
    async def test_f1_navigates_to_dashboard(self) -> None:
        app = TITANApp()
        async with app.run_test() as pilot:
            from titan.tui.screens.dashboard import DashboardScreen

            app.push_screen(PaperScreen())
            await pilot.pause()
            await pilot.press("f1")
            assert isinstance(app.screen, DashboardScreen)
