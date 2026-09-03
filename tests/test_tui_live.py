"""Tests for TITAN TUI Live Trading screen — models, widgets, helpers, screen."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from textual.widgets import Static

from titan.tui.layout import (
    _format_inr,
    _format_pnl,
    _format_uptime,
    _read_broker_status,
    _read_live_account,
    _read_live_exposure,
    _read_live_orders,
    _read_live_positions,
    _read_live_status,
    _read_recent_executions,
    build_live_state,
)
from titan.tui.models import (
    AccountInfo,
    BrokerStatusInfo,
    ExecutionEntry,
    ExposureInfo,
    LiveOrderEntry,
    LivePositionEntry,
    LiveScreenState,
    LiveStatusInfo,
)
from titan.tui.screens.live import LiveScreen
from titan.tui.widgets.live import (
    AccountWidget,
    BrokerStatusWidget,
    ExecutionsWidget,
    ExposureWidget,
    LiveHealthWidget,
    LiveOrdersWidget,
    LivePositionsWidget,
    LiveStatusWidget,
    _health_class,
    _live_status_class,
    _pnl_class,
)

# ──────────────────────────────────────────────────
# Model tests: LiveStatusInfo
# ──────────────────────────────────────────────────


class TestLiveStatusInfo:
    def test_defaults(self) -> None:
        info = LiveStatusInfo()
        assert info.status == "Stopped"
        assert info.uptime == "00:00:00"
        assert info.is_running is False
        assert info.broker_connected is False
        assert info.stream_connected is False
        assert info.pipeline_executions == 0

    def test_custom(self) -> None:
        info = LiveStatusInfo(
            status="RUNNING",
            uptime="02:30:00",
            is_running=True,
            broker_connected=True,
            stream_connected=True,
            pipeline_executions=42,
        )
        assert info.status == "RUNNING"
        assert info.uptime == "02:30:00"
        assert info.is_running is True
        assert info.broker_connected is True
        assert info.stream_connected is True
        assert info.pipeline_executions == 42

    def test_frozen(self) -> None:
        info = LiveStatusInfo()
        with pytest.raises(AttributeError):
            info.status = "Stopped"  # type: ignore[misc]

    def test_slots(self) -> None:
        info = LiveStatusInfo()
        assert not hasattr(info, "__dict__")


# ──────────────────────────────────────────────────
# Model tests: BrokerStatusInfo
# ──────────────────────────────────────────────────


class TestBrokerStatusInfo:
    def test_defaults(self) -> None:
        info = BrokerStatusInfo()
        assert info.provider == "None"
        assert info.connection_status == "Disconnected"
        assert info.is_connected is False
        assert info.exchange == ""
        assert info.account_id == ""

    def test_custom(self) -> None:
        info = BrokerStatusInfo(
            provider="AngelOneBroker",
            connection_status="Connected",
            is_connected=True,
            exchange="NSE",
            account_id="AB1234",
        )
        assert info.provider == "AngelOneBroker"
        assert info.connection_status == "Connected"
        assert info.is_connected is True

    def test_frozen(self) -> None:
        info = BrokerStatusInfo()
        with pytest.raises(AttributeError):
            info.provider = "X"  # type: ignore[misc]

    def test_slots(self) -> None:
        info = BrokerStatusInfo()
        assert not hasattr(info, "__dict__")


# ──────────────────────────────────────────────────
# Model tests: AccountInfo
# ──────────────────────────────────────────────────


class TestAccountInfo:
    def test_defaults(self) -> None:
        info = AccountInfo()
        assert info.available_cash == "₹0"
        assert info.used_margin == "₹0"
        assert info.available_margin == "₹0"
        assert info.payin == "₹0"
        assert info.payout == "₹0"

    def test_custom(self) -> None:
        info = AccountInfo(
            available_cash="₹98,450",
            used_margin="₹12,000",
            available_margin="₹88,000",
            payin="₹50,000",
            payout="₹0",
        )
        assert info.available_cash == "₹98,450"
        assert info.used_margin == "₹12,000"
        assert info.available_margin == "₹88,000"
        assert info.payin == "₹50,000"
        assert info.payout == "₹0"

    def test_frozen(self) -> None:
        info = AccountInfo()
        with pytest.raises(AttributeError):
            info.available_cash = "₹0"  # type: ignore[misc]

    def test_slots(self) -> None:
        info = AccountInfo()
        assert not hasattr(info, "__dict__")


# ──────────────────────────────────────────────────
# Model tests: ExposureInfo
# ──────────────────────────────────────────────────


class TestExposureInfo:
    def test_defaults(self) -> None:
        info = ExposureInfo()
        assert info.total_positions == 0
        assert info.long_positions == 0
        assert info.short_positions == 0
        assert info.gross_exposure == "₹0"
        assert info.net_exposure == "₹0"
        assert info.unrealized_pnl == "+₹0"

    def test_custom(self) -> None:
        info = ExposureInfo(
            total_positions=5,
            long_positions=3,
            short_positions=2,
            gross_exposure="₹2,50,000",
            net_exposure="₹50,000",
            unrealized_pnl="+₹12,500",
        )
        assert info.total_positions == 5
        assert info.long_positions == 3
        assert info.short_positions == 2
        assert info.gross_exposure == "₹2,50,000"
        assert info.unrealized_pnl == "+₹12,500"

    def test_frozen(self) -> None:
        info = ExposureInfo()
        with pytest.raises(AttributeError):
            info.total_positions = 1  # type: ignore[misc]

    def test_slots(self) -> None:
        info = ExposureInfo()
        assert not hasattr(info, "__dict__")


# ──────────────────────────────────────────────────
# Model tests: LivePositionEntry
# ──────────────────────────────────────────────────


class TestLivePositionEntry:
    def test_defaults(self) -> None:
        entry = LivePositionEntry()
        assert entry.symbol == ""
        assert entry.exchange == ""
        assert entry.product == ""
        assert entry.quantity == 0
        assert entry.buy_qty == 0
        assert entry.sell_qty == 0
        assert entry.avg_price == "0"
        assert entry.current_price == "0"
        assert entry.pnl == "+₹0"
        assert entry.realised_pnl == "+₹0"

    def test_custom(self) -> None:
        entry = LivePositionEntry(
            symbol="RELIANCE",
            exchange="NSE",
            product="delivery",
            quantity=10,
            buy_qty=10,
            sell_qty=0,
            avg_price="₹2,450",
            current_price="₹2,470",
            pnl="+₹200",
            realised_pnl="+₹0",
        )
        assert entry.symbol == "RELIANCE"
        assert entry.exchange == "NSE"
        assert entry.quantity == 10
        assert entry.pnl == "+₹200"

    def test_frozen(self) -> None:
        entry = LivePositionEntry()
        with pytest.raises(AttributeError):
            entry.symbol = "X"  # type: ignore[misc]

    def test_slots(self) -> None:
        entry = LivePositionEntry()
        assert not hasattr(entry, "__dict__")


# ──────────────────────────────────────────────────
# Model tests: LiveOrderEntry
# ──────────────────────────────────────────────────


class TestLiveOrderEntry:
    def test_defaults(self) -> None:
        entry = LiveOrderEntry()
        assert entry.order_id == ""
        assert entry.symbol == ""
        assert entry.side == ""
        assert entry.order_type == ""
        assert entry.quantity == 0
        assert entry.filled_quantity == 0
        assert entry.price == ""
        assert entry.status == ""
        assert entry.placed_at == ""

    def test_custom(self) -> None:
        entry = LiveOrderEntry(
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
        entry = LiveOrderEntry()
        with pytest.raises(AttributeError):
            entry.symbol = "X"  # type: ignore[misc]

    def test_slots(self) -> None:
        entry = LiveOrderEntry()
        assert not hasattr(entry, "__dict__")


# ──────────────────────────────────────────────────
# Model tests: ExecutionEntry
# ──────────────────────────────────────────────────


class TestExecutionEntry:
    def test_defaults(self) -> None:
        entry = ExecutionEntry()
        assert entry.trade_id == ""
        assert entry.order_id == ""
        assert entry.symbol == ""
        assert entry.side == ""
        assert entry.quantity == 0
        assert entry.price == ""
        assert entry.time == ""

    def test_custom(self) -> None:
        entry = ExecutionEntry(
            trade_id="T001",
            order_id="O001",
            symbol="RELIANCE",
            side="buy",
            quantity=10,
            price="₹2,450",
            time="09:15",
        )
        assert entry.trade_id == "T001"
        assert entry.order_id == "O001"
        assert entry.symbol == "RELIANCE"
        assert entry.quantity == 10

    def test_frozen(self) -> None:
        entry = ExecutionEntry()
        with pytest.raises(AttributeError):
            entry.trade_id = "X"  # type: ignore[misc]

    def test_slots(self) -> None:
        entry = ExecutionEntry()
        assert not hasattr(entry, "__dict__")


# ──────────────────────────────────────────────────
# Model tests: LiveScreenState
# ──────────────────────────────────────────────────


class TestLiveScreenState:
    def test_defaults(self) -> None:
        state = LiveScreenState()
        assert isinstance(state.live_status, LiveStatusInfo)
        assert isinstance(state.broker_status, BrokerStatusInfo)
        assert isinstance(state.account, AccountInfo)
        assert isinstance(state.exposure, ExposureInfo)
        assert state.positions == ()
        assert state.orders == ()
        assert state.executions == ()
        assert state.last_refresh == ""

    def test_custom(self) -> None:
        state = LiveScreenState(
            live_status=LiveStatusInfo(status="RUNNING"),
            broker_status=BrokerStatusInfo(provider="Paper"),
            account=AccountInfo(available_cash="₹1,00,000"),
            exposure=ExposureInfo(total_positions=3),
            positions=(LivePositionEntry(symbol="RELIANCE"),),
            orders=(LiveOrderEntry(order_id="O1"),),
            executions=(ExecutionEntry(trade_id="T1"),),
            last_refresh="10:30:00",
        )
        assert state.live_status.status == "RUNNING"
        assert state.broker_status.provider == "Paper"
        assert state.account.available_cash == "₹1,00,000"
        assert state.exposure.total_positions == 3
        assert len(state.positions) == 1
        assert len(state.orders) == 1
        assert len(state.executions) == 1
        assert state.last_refresh == "10:30:00"

    def test_frozen(self) -> None:
        state = LiveScreenState()
        with pytest.raises(AttributeError):
            state.last_refresh = "X"  # type: ignore[misc]

    def test_slots(self) -> None:
        state = LiveScreenState()
        assert not hasattr(state, "__dict__")

    def test_tuple_positions_immutable(self) -> None:
        state = LiveScreenState(
            positions=(LivePositionEntry(symbol="A"), LivePositionEntry(symbol="B"))
        )
        assert len(state.positions) == 2

    def test_tuple_orders_immutable(self) -> None:
        state = LiveScreenState(
            orders=(LiveOrderEntry(order_id="1"), LiveOrderEntry(order_id="2"))
        )
        assert len(state.orders) == 2

    def test_tuple_executions_immutable(self) -> None:
        state = LiveScreenState(
            executions=(
                ExecutionEntry(trade_id="T1"),
                ExecutionEntry(trade_id="T2"),
            )
        )
        assert len(state.executions) == 2


# ──────────────────────────────────────────────────
# Helper function tests
# ──────────────────────────────────────────────────


class TestLiveStatusClass:
    def test_running(self) -> None:
        assert _live_status_class("RUNNING") == "value-running"

    def test_connected(self) -> None:
        assert _live_status_class("Connected") == "value-running"

    def test_active(self) -> None:
        assert _live_status_class("active") == "value-running"

    def test_stopped(self) -> None:
        assert _live_status_class("STOPPED") == "value-stopped"

    def test_error(self) -> None:
        assert _live_status_class("error") == "value-stopped"

    def test_disconnected(self) -> None:
        assert _live_status_class("Disconnected") == "value-stopped"

    def test_unknown(self) -> None:
        assert _live_status_class("unknown") == "value-stopped"


class TestPnlClass:
    def test_positive(self) -> None:
        assert _pnl_class("+₹1,200") == "value-positive"

    def test_negative(self) -> None:
        assert _pnl_class("-₹500") == "value-negative"

    def test_neutral_zero(self) -> None:
        assert _pnl_class("₹0") == "value-neutral"

    def test_positive_numeric(self) -> None:
        assert _pnl_class("1500") == "value-positive"

    def test_negative_unicode(self) -> None:
        assert _pnl_class("\u2212₹300") == "value-negative"

    def test_empty(self) -> None:
        assert _pnl_class("") == "value-neutral"


class TestHealthClass:
    def test_healthy(self) -> None:
        assert _health_class("healthy") == "value-healthy"

    def test_ok(self) -> None:
        assert _health_class("OK") == "value-healthy"

    def test_degraded(self) -> None:
        assert _health_class("degraded") == "value-degraded"

    def test_warning(self) -> None:
        assert _health_class("warning") == "value-degraded"

    def test_unhealthy(self) -> None:
        assert _health_class("unhealthy") == "value-unhealthy"

    def test_critical(self) -> None:
        assert _health_class("critical") == "value-unhealthy"

    def test_unknown(self) -> None:
        assert _health_class("unknown") == "value-unknown"

    def test_empty(self) -> None:
        assert _health_class("") == "value-unknown"


class TestFormatHelpers:
    def test_format_uptime_basic(self) -> None:
        assert _format_uptime(3661) == "01:01:01"

    def test_format_uptime_zero(self) -> None:
        assert _format_uptime(0) == "00:00:00"

    def test_format_uptime_large(self) -> None:
        assert _format_uptime(86400) == "24:00:00"

    def test_format_inr_positive(self) -> None:
        assert _format_inr(Decimal(1234)) == "INR 1,234"

    def test_format_inr_negative(self) -> None:
        assert _format_inr(Decimal(-1234)) == "-INR 1,234"

    def test_format_inr_zero(self) -> None:
        assert _format_inr(0) == "INR 0"

    def test_format_inr_none(self) -> None:
        assert _format_inr(None) == "INR 0"

    def test_format_pnl_positive(self) -> None:
        assert _format_pnl(Decimal(500)) == "+INR 500"

    def test_format_pnl_negative(self) -> None:
        assert _format_pnl(Decimal(-300)) == "-INR 300"

    def test_format_pnl_zero(self) -> None:
        assert _format_pnl(Decimal(0)) == "+INR 0"


# ──────────────────────────────────────────────────
# Widget tests
# ──────────────────────────────────────────────────


class TestLiveStatusWidget:
    def test_import(self) -> None:
        assert LiveStatusWidget is not None

    def test_default_info(self) -> None:
        w = LiveStatusWidget()
        assert isinstance(w._info, LiveStatusInfo)

    def test_update_data(self) -> None:
        w = LiveStatusWidget()
        w._title = MagicMock()
        w._status = MagicMock()
        w._uptime = MagicMock()
        w._broker = MagicMock()
        w._stream = MagicMock()
        w._pipeline = MagicMock()
        info = LiveStatusInfo(
            status="RUNNING",
            uptime="01:30:00",
            is_running=True,
            broker_connected=True,
            stream_connected=True,
            pipeline_executions=10,
        )
        w.update_data(info)
        assert w._info == info
        w._status.update.assert_called_once()
        w._uptime.update.assert_called_once()
        w._broker.update.assert_called_once()
        w._stream.update.assert_called_once()
        w._pipeline.update.assert_called_once()

    def test_update_data_before_compose(self) -> None:
        w = LiveStatusWidget()
        info = LiveStatusInfo(status="RUNNING")
        w.update_data(info)
        assert w._info == info

    def test_render(self) -> None:
        w = LiveStatusWidget()
        assert w.render() == ""

    def test_update_data_disconnected(self) -> None:
        w = LiveStatusWidget()
        w._title = MagicMock()
        w._status = MagicMock()
        w._uptime = MagicMock()
        w._broker = MagicMock()
        w._stream = MagicMock()
        w._pipeline = MagicMock()
        info = LiveStatusInfo(
            status="STOPPED",
            broker_connected=False,
            stream_connected=False,
        )
        w.update_data(info)
        w._broker.update.assert_called_once()


class TestBrokerStatusWidget:
    def test_import(self) -> None:
        assert BrokerStatusWidget is not None

    def test_default_info(self) -> None:
        w = BrokerStatusWidget()
        assert isinstance(w._info, BrokerStatusInfo)

    def test_update_data(self) -> None:
        w = BrokerStatusWidget()
        w._title = MagicMock()
        w._provider = MagicMock()
        w._connection = MagicMock()
        w._exchange = MagicMock()
        w._account = MagicMock()
        info = BrokerStatusInfo(
            provider="PaperBroker",
            connection_status="Connected",
            is_connected=True,
            exchange="NSE",
            account_id="AB123",
        )
        w.update_data(info)
        assert w._info == info
        w._provider.update.assert_called_once()
        w._connection.update.assert_called_once()
        w._exchange.update.assert_called_once()
        w._account.update.assert_called_once()

    def test_update_data_before_compose(self) -> None:
        w = BrokerStatusWidget()
        info = BrokerStatusInfo(provider="Paper")
        w.update_data(info)
        assert w._info == info

    def test_render(self) -> None:
        w = BrokerStatusWidget()
        assert w.render() == ""


class TestAccountWidget:
    def test_import(self) -> None:
        assert AccountWidget is not None

    def test_default_info(self) -> None:
        w = AccountWidget()
        assert isinstance(w._info, AccountInfo)

    def test_update_data(self) -> None:
        w = AccountWidget()
        w._title = MagicMock()
        w._cash = MagicMock()
        w._used = MagicMock()
        w._available = MagicMock()
        w._payin = MagicMock()
        w._payout = MagicMock()
        info = AccountInfo(
            available_cash="₹1,00,000",
            used_margin="₹10,000",
            available_margin="₹90,000",
            payin="₹50,000",
            payout="₹0",
        )
        w.update_data(info)
        assert w._info == info
        w._cash.update.assert_called_once()
        w._used.update.assert_called_once()
        w._available.update.assert_called_once()
        w._payin.update.assert_called_once()
        w._payout.update.assert_called_once()

    def test_update_data_before_compose(self) -> None:
        w = AccountWidget()
        info = AccountInfo(available_cash="₹1,00,000")
        w.update_data(info)
        assert w._info == info

    def test_render(self) -> None:
        w = AccountWidget()
        assert w.render() == ""


class TestExposureWidget:
    def test_import(self) -> None:
        assert ExposureWidget is not None

    def test_default_info(self) -> None:
        w = ExposureWidget()
        assert isinstance(w._info, ExposureInfo)

    def test_update_data(self) -> None:
        w = ExposureWidget()
        w._title = MagicMock()
        w._total = MagicMock()
        w._long = MagicMock()
        w._short = MagicMock()
        w._gross = MagicMock()
        w._net = MagicMock()
        w._pnl = MagicMock()
        info = ExposureInfo(
            total_positions=5,
            long_positions=3,
            short_positions=2,
            gross_exposure="₹2,50,000",
            net_exposure="₹50,000",
            unrealized_pnl="+₹12,500",
        )
        w.update_data(info)
        assert w._info == info
        w._total.update.assert_called_once()
        w._long.update.assert_called_once()
        w._short.update.assert_called_once()
        w._gross.update.assert_called_once()
        w._net.update.assert_called_once()
        w._pnl.update.assert_called_once()

    def test_update_data_before_compose(self) -> None:
        w = ExposureWidget()
        info = ExposureInfo(total_positions=3)
        w.update_data(info)
        assert w._info == info

    def test_render(self) -> None:
        w = ExposureWidget()
        assert w.render() == ""

    def test_update_data_negative_pnl(self) -> None:
        w = ExposureWidget()
        w._title = MagicMock()
        w._total = MagicMock()
        w._long = MagicMock()
        w._short = MagicMock()
        w._gross = MagicMock()
        w._net = MagicMock()
        w._pnl = MagicMock()
        info = ExposureInfo(unrealized_pnl="-₹500")
        w.update_data(info)
        w._pnl.update.assert_called_once()


class TestLiveHealthWidget:
    def test_import(self) -> None:
        assert LiveHealthWidget is not None

    def test_default_state(self) -> None:
        w = LiveHealthWidget()
        assert w._monitoring_status == "Unknown"
        assert w._critical_alerts == 0
        assert w._total_alerts == 0
        assert w._recovery_status == "Idle"
        assert w._recovery_attempts == 0

    def test_update_data(self) -> None:
        w = LiveHealthWidget()
        w._title = MagicMock()
        w._monitoring = MagicMock()
        w._alerts = MagicMock()
        w._recovery = MagicMock()
        w.update_data(
            monitoring_status="healthy",
            critical_alerts=0,
            total_alerts=3,
            recovery_status="Idle",
            recovery_attempts=0,
        )
        assert w._monitoring_status == "healthy"
        assert w._critical_alerts == 0
        assert w._total_alerts == 3
        w._monitoring.update.assert_called_once()
        w._alerts.update.assert_called_once()
        w._recovery.update.assert_called_once()

    def test_update_data_before_compose(self) -> None:
        w = LiveHealthWidget()
        w.update_data(
            monitoring_status="degraded",
            critical_alerts=1,
            total_alerts=5,
            recovery_status="Active",
            recovery_attempts=2,
        )
        assert w._monitoring_status == "degraded"
        assert w._critical_alerts == 1

    def test_render(self) -> None:
        w = LiveHealthWidget()
        assert w.render() == ""

    def test_critical_alerts_highlight(self) -> None:
        w = LiveHealthWidget()
        w._title = MagicMock()
        w._monitoring = MagicMock()
        w._alerts = MagicMock()
        w._recovery = MagicMock()
        w.update_data(
            monitoring_status="unhealthy",
            critical_alerts=2,
            total_alerts=5,
            recovery_status="Active",
            recovery_attempts=1,
        )
        w._alerts.update.assert_called_once()


class TestLivePositionsWidget:
    def test_import(self) -> None:
        assert LivePositionsWidget is not None

    def test_default_state(self) -> None:
        w = LivePositionsWidget()
        assert w._positions == ()
        assert w._rows == []

    def test_update_data_empty(self) -> None:
        w = LivePositionsWidget()
        w._title = MagicMock()
        w._rows = []
        w.mount = MagicMock()
        w.update_data(())
        assert w._positions == ()

    def test_update_data_before_compose(self) -> None:
        w = LivePositionsWidget()
        positions = (LivePositionEntry(symbol="RELIANCE"),)
        w.update_data(positions)
        assert w._positions == positions

    def test_update_data_with_positions(self) -> None:
        w = LivePositionsWidget()
        w._title = MagicMock()
        w._rows = []
        w.mount = MagicMock()
        positions = (
            LivePositionEntry(
                symbol="RELIANCE",
                exchange="NSE",
                quantity=10,
                avg_price="₹2,450",
                current_price="₹2,470",
                pnl="+₹200",
            ),
        )
        w.update_data(positions)
        assert len(w._rows) == 1
        w.mount.assert_called_once()

    def test_render(self) -> None:
        w = LivePositionsWidget()
        assert w.render() == ""


class TestLiveOrdersWidget:
    def test_import(self) -> None:
        assert LiveOrdersWidget is not None

    def test_default_state(self) -> None:
        w = LiveOrdersWidget()
        assert w._orders == ()
        assert w._rows == []

    def test_update_data_empty(self) -> None:
        w = LiveOrdersWidget()
        w._title = MagicMock()
        w._rows = []
        w.mount = MagicMock()
        w.update_data(())
        assert w._orders == ()

    def test_update_data_before_compose(self) -> None:
        w = LiveOrdersWidget()
        orders = (LiveOrderEntry(order_id="O1"),)
        w.update_data(orders)
        assert w._orders == orders

    def test_update_data_with_orders(self) -> None:
        w = LiveOrdersWidget()
        w._title = MagicMock()
        w._rows = []
        w.mount = MagicMock()
        orders = (
            LiveOrderEntry(
                order_id="O001",
                symbol="RELIANCE",
                side="buy",
                order_type="LIMIT",
                quantity=10,
                price="₹2,450",
                status="OPEN",
            ),
        )
        w.update_data(orders)
        assert len(w._rows) == 1
        w.mount.assert_called_once()

    def test_render(self) -> None:
        w = LiveOrdersWidget()
        assert w.render() == ""


class TestExecutionsWidget:
    def test_import(self) -> None:
        assert ExecutionsWidget is not None

    def test_default_state(self) -> None:
        w = ExecutionsWidget()
        assert w._executions == ()
        assert w._rows == []

    def test_update_data_empty(self) -> None:
        w = ExecutionsWidget()
        w._title = MagicMock()
        w._rows = []
        w.mount = MagicMock()
        w.update_data(())
        assert w._executions == ()

    def test_update_data_before_compose(self) -> None:
        w = ExecutionsWidget()
        execs = (ExecutionEntry(trade_id="T1"),)
        w.update_data(execs)
        assert w._executions == execs

    def test_update_data_with_executions(self) -> None:
        w = ExecutionsWidget()
        w._title = MagicMock()
        w._rows = []
        w.mount = MagicMock()
        execs = (
            ExecutionEntry(
                trade_id="T001",
                order_id="O001",
                symbol="RELIANCE",
                side="buy",
                quantity=10,
                price="₹2,450",
                time="09:15",
            ),
        )
        w.update_data(execs)
        assert len(w._rows) == 1
        w.mount.assert_called_once()

    def test_render(self) -> None:
        w = ExecutionsWidget()
        assert w.render() == ""


# ──────────────────────────────────────────────────
# Dynamic widget row removal tests
# ──────────────────────────────────────────────────


class TestDynamicWidgetRowRemoval:
    def test_positions_clears_old_rows(self) -> None:
        w = LivePositionsWidget()
        w._title = MagicMock()
        mock_row = MagicMock()
        w._rows = [mock_row]
        w.mount = MagicMock()
        w.update_data(())
        mock_row.remove.assert_called_once()
        assert len(w._rows) == 1
        assert w._rows[0] is not mock_row

    def test_orders_clears_old_rows(self) -> None:
        w = LiveOrdersWidget()
        w._title = MagicMock()
        mock_row = MagicMock()
        w._rows = [mock_row]
        w.mount = MagicMock()
        w.update_data(())
        mock_row.remove.assert_called_once()
        assert len(w._rows) == 1
        assert w._rows[0] is not mock_row

    def test_executions_clears_old_rows(self) -> None:
        w = ExecutionsWidget()
        w._title = MagicMock()
        mock_row = MagicMock()
        w._rows = [mock_row]
        w.mount = MagicMock()
        w.update_data(())
        mock_row.remove.assert_called_once()
        assert len(w._rows) == 1
        assert w._rows[0] is not mock_row


# ──────────────────────────────────────────────────
# Layout reader tests
# ──────────────────────────────────────────────────


class TestReadLiveStatus:
    @patch("titan.cli.common.get_runtime_engine")
    def test_connected(self, mock_get: MagicMock) -> None:
        engine = MagicMock()
        report = MagicMock()
        report.runtime_status.name = "RUNNING"
        report.performance.uptime_seconds = 3600.0
        report.broker.connection.value = "connected"
        report.market.stream_status = "connected"
        report.scheduler.pipeline_executions = 42
        engine.generate_report.return_value = report
        engine.is_running = True
        mock_get.return_value = engine
        info = _read_live_status()
        assert info.status == "RUNNING"
        assert info.is_running is True
        assert info.broker_connected is True
        assert info.stream_connected is True
        assert info.pipeline_executions == 42

    @patch("titan.cli.common.get_runtime_engine")
    def test_exception(self, mock_get: MagicMock) -> None:
        mock_get.side_effect = RuntimeError("fail")
        info = _read_live_status()
        assert info.status == "Stopped"


class TestReadBrokerStatus:
    @patch("titan.cli.common.get_runtime_engine")
    def test_connected(self, mock_get: MagicMock) -> None:
        engine = MagicMock()
        report = MagicMock()
        report.broker.connection.value = "connected"
        engine.generate_report.return_value = report
        engine.broker.is_connected.return_value = True
        engine.broker.__class__ = type("PaperBroker", (), {})
        mock_get.return_value = engine
        info = _read_broker_status()
        assert info.is_connected is True
        assert info.connection_status == "connected"

    @patch("titan.cli.common.get_runtime_engine")
    def test_exception(self, mock_get: MagicMock) -> None:
        mock_get.side_effect = RuntimeError("fail")
        info = _read_broker_status()
        assert info.provider == "None"


class TestReadLiveAccount:
    @patch("titan.cli.common.get_runtime_engine")
    def test_with_funds(self, mock_get: MagicMock) -> None:
        engine = MagicMock()
        engine.broker.funds.return_value = MagicMock(
            available_cash=Decimal(100000),
            payin=Decimal(50000),
            payout=Decimal(0),
        )
        engine.broker.margin.return_value = MagicMock(
            used_margin=Decimal(10000),
            available_margin=Decimal(90000),
        )
        mock_get.return_value = engine
        info = _read_live_account()
        assert "100,000" in info.available_cash
        assert "10,000" in info.used_margin

    @patch("titan.cli.common.get_runtime_engine")
    def test_exception(self, mock_get: MagicMock) -> None:
        mock_get.side_effect = RuntimeError("fail")
        info = _read_live_account()
        assert info.available_cash == "₹0"


class TestReadLiveExposure:
    @patch("titan.cli.common.get_runtime_engine")
    def test_with_positions(self, mock_get: MagicMock) -> None:
        engine = MagicMock()
        pos1 = MagicMock()
        pos1.quantity = 10
        pos1.current_price = Decimal(100)
        pos1.pnl = Decimal(200)
        pos2 = MagicMock()
        pos2.quantity = -5
        pos2.current_price = Decimal(200)
        pos2.pnl = Decimal(-100)
        engine.broker.positions.return_value = [pos1, pos2]
        mock_get.return_value = engine
        info = _read_live_exposure()
        assert info.total_positions == 2
        assert info.long_positions == 1
        assert info.short_positions == 1

    @patch("titan.cli.common.get_runtime_engine")
    def test_exception(self, mock_get: MagicMock) -> None:
        mock_get.side_effect = RuntimeError("fail")
        info = _read_live_exposure()
        assert info.total_positions == 0


class TestReadLivePositions:
    @patch("titan.cli.common.get_runtime_engine")
    def test_with_positions(self, mock_get: MagicMock) -> None:
        engine = MagicMock()
        from titan.brokers.models import Exchange, ProductType

        pos = MagicMock()
        pos.symbol = "RELIANCE"
        pos.exchange = Exchange.NSE
        pos.product = ProductType.DELIVERY
        pos.quantity = 10
        pos.buy_quantity = 10
        pos.sell_quantity = 0
        pos.buy_price = Decimal(2450)
        pos.current_price = Decimal(2470)
        pos.pnl = Decimal(200)
        pos.realised_pnl = Decimal(0)
        engine.broker.positions.return_value = [pos]
        mock_get.return_value = engine
        result = _read_live_positions()
        assert len(result) == 1
        assert result[0].symbol == "RELIANCE"
        assert result[0].quantity == 10

    @patch("titan.cli.common.get_runtime_engine")
    def test_exception(self, mock_get: MagicMock) -> None:
        mock_get.side_effect = RuntimeError("fail")
        result = _read_live_positions()
        assert result == ()


class TestReadLiveOrders:
    @patch("titan.cli.common.get_runtime_engine")
    def test_with_active_orders(self, mock_get: MagicMock) -> None:
        engine = MagicMock()
        from titan.brokers.models import OrderSide, OrderStatus, OrderType

        o = MagicMock()
        o.broker_order_id = "O001"
        o.symbol = "RELIANCE"
        o.side = OrderSide.BUY
        o.order_type = OrderType.LIMIT
        o.quantity = 10
        o.filled_quantity = 5
        o.average_price = Decimal(2450)
        o.price = None
        o.status = OrderStatus.OPEN
        o.placed_at = None
        engine.broker.orders.return_value = [o]
        mock_get.return_value = engine
        result = _read_live_orders()
        assert len(result) == 1
        assert result[0].order_id == "O001"
        assert result[0].side == "buy"

    @patch("titan.cli.common.get_runtime_engine")
    def test_filters_filled_orders(self, mock_get: MagicMock) -> None:
        engine = MagicMock()
        from titan.brokers.models import OrderStatus

        o = MagicMock()
        o.status = OrderStatus.FILLED
        engine.broker.orders.return_value = [o]
        mock_get.return_value = engine
        result = _read_live_orders()
        assert len(result) == 0

    @patch("titan.cli.common.get_runtime_engine")
    def test_exception(self, mock_get: MagicMock) -> None:
        mock_get.side_effect = RuntimeError("fail")
        result = _read_live_orders()
        assert result == ()


class TestReadRecentExecutions:
    @patch("titan.cli.common.get_runtime_engine")
    def test_with_trades(self, mock_get: MagicMock) -> None:
        engine = MagicMock()
        from titan.brokers.models import OrderSide

        t = MagicMock()
        t.trade_id = "T001"
        t.broker_order_id = "O001"
        t.symbol = "RELIANCE"
        t.side = OrderSide.BUY
        t.quantity = 10
        t.price = Decimal(2450)
        t.trade_time = None
        engine.broker.trades.return_value = [t]
        mock_get.return_value = engine
        result = _read_recent_executions()
        assert len(result) == 1
        assert result[0].trade_id == "T001"

    @patch("titan.cli.common.get_runtime_engine")
    def test_exception(self, mock_get: MagicMock) -> None:
        mock_get.side_effect = RuntimeError("fail")
        result = _read_recent_executions()
        assert result == ()


# ──────────────────────────────────────────────────
# Build live state tests
# ──────────────────────────────────────────────────


class TestBuildLiveState:
    @patch("titan.tui.layout._read_recent_executions")
    @patch("titan.tui.layout._read_live_orders")
    @patch("titan.tui.layout._read_live_positions")
    @patch("titan.tui.layout._read_live_exposure")
    @patch("titan.tui.layout._read_live_account")
    @patch("titan.tui.layout._read_broker_status")
    @patch("titan.tui.layout._read_live_status")
    def test_builds_state(
        self,
        mock_status: MagicMock,
        mock_broker: MagicMock,
        mock_account: MagicMock,
        mock_exposure: MagicMock,
        mock_positions: MagicMock,
        mock_orders: MagicMock,
        mock_executions: MagicMock,
    ) -> None:
        mock_status.return_value = LiveStatusInfo(status="RUNNING")
        mock_broker.return_value = BrokerStatusInfo(provider="Paper")
        mock_account.return_value = AccountInfo(available_cash="₹1,00,000")
        mock_exposure.return_value = ExposureInfo(total_positions=2)
        mock_positions.return_value = (LivePositionEntry(symbol="RELIANCE"),)
        mock_orders.return_value = (LiveOrderEntry(order_id="O1"),)
        mock_executions.return_value = (ExecutionEntry(trade_id="T1"),)
        state = build_live_state()
        assert state.live_status.status == "RUNNING"
        assert state.broker_status.provider == "Paper"
        assert state.account.available_cash == "₹1,00,000"
        assert state.exposure.total_positions == 2
        assert len(state.positions) == 1
        assert len(state.orders) == 1
        assert len(state.executions) == 1
        assert state.last_refresh != ""


# ──────────────────────────────────────────────────
# Screen tests
# ──────────────────────────────────────────────────


class TestLiveScreenUnit:
    def test_creation(self) -> None:
        screen = LiveScreen()
        assert screen._state_builder is None
        assert isinstance(screen._state, LiveScreenState)

    def test_set_state_builder(self) -> None:
        screen = LiveScreen()

        def builder() -> LiveScreenState:
            return LiveScreenState()

        screen.set_state_builder(builder)
        assert screen._state_builder is builder

    def test_state_property(self) -> None:
        screen = LiveScreen()
        assert isinstance(screen.state, LiveScreenState)

    def test_refresh_without_builder(self) -> None:
        screen = LiveScreen()
        screen._refresh_state()
        assert isinstance(screen._state, LiveScreenState)

    def test_refresh_with_builder(self) -> None:
        screen = LiveScreen()
        custom_state = LiveScreenState(live_status=LiveStatusInfo(status="RUNNING"))
        screen.set_state_builder(lambda: custom_state)
        screen._refresh_state()
        assert screen._state.live_status.status == "RUNNING"

    def test_refresh_builder_exception(self) -> None:
        screen = LiveScreen()
        screen.set_state_builder(lambda: (_ for _ in ()).throw(RuntimeError))
        screen._refresh_state()
        assert isinstance(screen._state, LiveScreenState)


class TestLiveScreenWidgetUpdate:
    def test_update_widgets_no_compose(self) -> None:
        screen = LiveScreen()
        screen._update_widgets()

    def test_update_widgets_with_none_widgets(self) -> None:
        screen = LiveScreen()
        screen._live_status_widget = None
        screen._broker_status_widget = None
        screen._account_widget = None
        screen._exposure_widget = None
        screen._health_widget = None
        screen._positions_widget = None
        screen._orders_widget = None
        screen._executions_widget = None
        screen._update_widgets()


class TestLiveScreenActions:
    def test_action_back(self) -> None:
        screen = LiveScreen()
        mock_app = MagicMock()
        screen._app = mock_app
        with patch.object(
            type(screen), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            screen.action_back()
        mock_app.action_go_back.assert_called_once()

    def test_action_refresh(self) -> None:
        screen = LiveScreen()
        screen.action_refresh()
        assert isinstance(screen._state, LiveScreenState)


# ──────────────────────────────────────────────────
# Health widget edge cases
# ──────────────────────────────────────────────────


class TestLiveHealthWidgetEdgeCases:
    def test_all_critical(self) -> None:
        w = LiveHealthWidget()
        w._title = MagicMock()
        w._monitoring = MagicMock()
        w._alerts = MagicMock()
        w._recovery = MagicMock()
        w.update_data(
            monitoring_status="unhealthy",
            critical_alerts=5,
            total_alerts=10,
            recovery_status="Active",
            recovery_attempts=3,
        )
        assert w._critical_alerts == 5
        assert w._recovery_attempts == 3

    def test_no_alerts(self) -> None:
        w = LiveHealthWidget()
        w._title = MagicMock()
        w._monitoring = MagicMock()
        w._alerts = MagicMock()
        w._recovery = MagicMock()
        w.update_data(
            monitoring_status="healthy",
            critical_alerts=0,
            total_alerts=0,
            recovery_status="Idle",
            recovery_attempts=0,
        )
        assert w._critical_alerts == 0


# ──────────────────────────────────────────────────
# Widget has_composed property
# ──────────────────────────────────────────────────


class TestHasComposedProperty:
    def test_positions_has_composed_false(self) -> None:
        w = LivePositionsWidget()
        assert w._has_composed is False

    def test_positions_has_composed_true(self) -> None:
        w = LivePositionsWidget()
        w._title = Static("Test")
        assert w._has_composed is True

    def test_orders_has_composed_false(self) -> None:
        w = LiveOrdersWidget()
        assert w._has_composed is False

    def test_orders_has_composed_true(self) -> None:
        w = LiveOrdersWidget()
        w._title = Static("Test")
        assert w._has_composed is True

    def test_executions_has_composed_false(self) -> None:
        w = ExecutionsWidget()
        assert w._has_composed is False

    def test_executions_has_composed_true(self) -> None:
        w = ExecutionsWidget()
        w._title = Static("Test")
        assert w._has_composed is True


# ──────────────────────────────────────────────────
# Screen CSS and bindings tests
# ──────────────────────────────────────────────────


class TestLiveScreenBindings:
    def test_has_bindings(self) -> None:
        assert len(LiveScreen.BINDINGS) > 0

    def test_refresh_binding(self) -> None:
        keys = [b[0] for b in LiveScreen.BINDINGS]
        assert "r" in keys

    def test_escape_binding(self) -> None:
        keys = [b[0] for b in LiveScreen.BINDINGS]
        assert "escape" in keys

    def test_quit_binding(self) -> None:
        keys = [b[0] for b in LiveScreen.BINDINGS]
        assert "q" in keys

    def test_page_up_binding(self) -> None:
        keys = [b[0] for b in LiveScreen.BINDINGS]
        assert "page_up" in keys

    def test_page_down_binding(self) -> None:
        keys = [b[0] for b in LiveScreen.BINDINGS]
        assert "page_down" in keys

    def test_up_binding(self) -> None:
        keys = [b[0] for b in LiveScreen.BINDINGS]
        assert "up" in keys

    def test_down_binding(self) -> None:
        keys = [b[0] for b in LiveScreen.BINDINGS]
        assert "down" in keys

    def test_home_binding(self) -> None:
        keys = [b[0] for b in LiveScreen.BINDINGS]
        assert "home" in keys

    def test_end_binding(self) -> None:
        keys = [b[0] for b in LiveScreen.BINDINGS]
        assert "end" in keys


# ──────────────────────────────────────────────────
# JSON serialization tests
# ──────────────────────────────────────────────────


class TestJsonSerialization:
    def test_live_status_to_dict(self) -> None:
        from dataclasses import asdict

        info = LiveStatusInfo(status="RUNNING", uptime="01:00:00")
        d = asdict(info)
        assert d["status"] == "RUNNING"
        assert d["uptime"] == "01:00:00"

    def test_broker_status_to_dict(self) -> None:
        from dataclasses import asdict

        info = BrokerStatusInfo(provider="Paper", is_connected=True)
        d = asdict(info)
        assert d["provider"] == "Paper"
        assert d["is_connected"] is True

    def test_account_to_dict(self) -> None:
        from dataclasses import asdict

        info = AccountInfo(available_cash="₹1,00,000")
        d = asdict(info)
        assert d["available_cash"] == "₹1,00,000"

    def test_exposure_to_dict(self) -> None:
        from dataclasses import asdict

        info = ExposureInfo(total_positions=5)
        d = asdict(info)
        assert d["total_positions"] == 5

    def test_position_entry_to_dict(self) -> None:
        from dataclasses import asdict

        entry = LivePositionEntry(symbol="RELIANCE", quantity=10)
        d = asdict(entry)
        assert d["symbol"] == "RELIANCE"

    def test_order_entry_to_dict(self) -> None:
        from dataclasses import asdict

        entry = LiveOrderEntry(order_id="O001", symbol="RELIANCE")
        d = asdict(entry)
        assert d["order_id"] == "O001"

    def test_execution_entry_to_dict(self) -> None:
        from dataclasses import asdict

        entry = ExecutionEntry(trade_id="T001", symbol="RELIANCE")
        d = asdict(entry)
        assert d["trade_id"] == "T001"

    def testScreenState_to_dict(self) -> None:
        from dataclasses import asdict

        state = LiveScreenState(
            live_status=LiveStatusInfo(status="RUNNING"),
            positions=(LivePositionEntry(symbol="RELIANCE"),),
        )
        d = asdict(state)
        assert d["live_status"]["status"] == "RUNNING"
        assert len(d["positions"]) == 1

    def testScreenState_json_roundtrip(self) -> None:
        import json
        from dataclasses import asdict

        state = LiveScreenState(
            live_status=LiveStatusInfo(status="RUNNING"),
            broker_status=BrokerStatusInfo(provider="Paper"),
            account=AccountInfo(available_cash="₹1,00,000"),
            exposure=ExposureInfo(total_positions=3),
            positions=(LivePositionEntry(symbol="RELIANCE"),),
            orders=(LiveOrderEntry(order_id="O1"),),
            executions=(ExecutionEntry(trade_id="T1"),),
            last_refresh="10:30:00",
        )
        json_str = json.dumps(asdict(state))
        loaded = json.loads(json_str)
        assert loaded["live_status"]["status"] == "RUNNING"
        assert loaded["broker_status"]["provider"] == "Paper"
        assert loaded["positions"][0]["symbol"] == "RELIANCE"


# ──────────────────────────────────────────────────
# Empty state tests
# ──────────────────────────────────────────────────


class TestEmptyState:
    def test_all_defaults_produce_safe_state(self) -> None:
        state = LiveScreenState()
        assert state.live_status.status == "Stopped"
        assert state.broker_status.provider == "None"
        assert state.account.available_cash == "₹0"
        assert state.exposure.total_positions == 0
        assert state.positions == ()
        assert state.orders == ()
        assert state.executions == ()
        assert state.last_refresh == ""

    def test_widgets_handle_empty_dto(self) -> None:
        w = LiveStatusWidget()
        w._title = MagicMock()
        w._status = MagicMock()
        w._uptime = MagicMock()
        w._broker = MagicMock()
        w._stream = MagicMock()
        w._pipeline = MagicMock()
        w.update_data(LiveStatusInfo())
        w._status.update.assert_called_once()

    def test_broker_widget_handle_empty(self) -> None:
        w = BrokerStatusWidget()
        w._title = MagicMock()
        w._provider = MagicMock()
        w._connection = MagicMock()
        w._exchange = MagicMock()
        w._account = MagicMock()
        w.update_data(BrokerStatusInfo())
        w._provider.update.assert_called_once()

    def test_account_widget_handle_empty(self) -> None:
        w = AccountWidget()
        w._title = MagicMock()
        w._cash = MagicMock()
        w._used = MagicMock()
        w._available = MagicMock()
        w._payin = MagicMock()
        w._payout = MagicMock()
        w.update_data(AccountInfo())
        w._cash.update.assert_called_once()


# ──────────────────────────────────────────────────
# Screen refresh indicator test
# ──────────────────────────────────────────────────


class TestRefreshIndicator:
    def test_update_refresh_indicator_no_widget(self) -> None:
        screen = LiveScreen()
        screen._update_refresh_indicator()


# ──────────────────────────────────────────────────
# Screen import
# ──────────────────────────────────────────────────


class TestScreenImport:
    def test_live_screen_importable(self) -> None:
        from titan.tui.screens.live import LiveScreen

        assert LiveScreen is not None

    def test_screens_init_exports(self) -> None:
        from titan.tui.screens import LiveScreen as LS

        assert LS is not None

    def test_widgets_init_imports(self) -> None:
        from titan.tui.widgets.live import (
            AccountWidget,
            BrokerStatusWidget,
            ExecutionsWidget,
            ExposureWidget,
            LiveHealthWidget,
            LiveOrdersWidget,
            LivePositionsWidget,
            LiveStatusWidget,
        )

        assert all(
            cls is not None
            for cls in [
                AccountWidget,
                BrokerStatusWidget,
                ExecutionsWidget,
                ExposureWidget,
                LiveHealthWidget,
                LiveOrdersWidget,
                LivePositionsWidget,
                LiveStatusWidget,
            ]
        )
