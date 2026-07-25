"""Tests for TITAN TUI Dashboard screen and widgets."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from titan.tui.layout import TITANApp, _format_uptime
from titan.tui.models import (
    DashboardState,
    HealthInfo,
    MarketInfo,
    RuntimeInfo,
    SystemInfo,
    TradingInfo,
)
from titan.tui.screens.dashboard import DashboardScreen
from titan.tui.widgets.health_card import HealthCard
from titan.tui.widgets.market_card import MarketCard
from titan.tui.widgets.runtime_card import RuntimeCard
from titan.tui.widgets.runtime_card import _status_class
from titan.tui.widgets.system_card import SystemCard
from titan.tui.widgets.trading_card import TradingCard
from titan.tui.widgets.trading_card import _trading_status_class

# ──────────────────────────────────────────────────
# Model tests
# ──────────────────────────────────────────────────


class TestDashboardState:
    def test_default_state(self) -> None:
        state = DashboardState()
        assert state.runtime.status == "Unknown"
        assert state.market.broker_connected is False
        assert state.trading.live_status == "Stopped"
        assert state.health.monitoring_status == "Unknown"
        assert state.system.version == "1.0.0"

    def test_state_is_frozen(self) -> None:
        state = DashboardState()
        with pytest.raises(AttributeError):
            state.runtime = RuntimeInfo(status="Running")  # type: ignore[misc]

    def test_custom_state(self) -> None:
        state = DashboardState(
            runtime=RuntimeInfo(status="Running", uptime="01:00:00"),
            market=MarketInfo(broker_connected=True, symbols_tracked=24),
        )
        assert state.runtime.status == "Running"
        assert state.runtime.uptime == "01:00:00"
        assert state.market.broker_connected is True
        assert state.market.symbols_tracked == 24


class TestRuntimeInfo:
    def test_defaults(self) -> None:
        info = RuntimeInfo()
        assert info.status == "Unknown"
        assert info.uptime == "00:00:00"
        assert info.is_running is False
        assert info.pipeline_executions == 0

    def test_custom(self) -> None:
        info = RuntimeInfo(
            status="Running",
            uptime="02:14:51",
            is_running=True,
            pipeline_executions=42,
            broker_status="Connected",
            stream_status="Connected",
        )
        assert info.is_running is True
        assert info.pipeline_executions == 42


class TestMarketInfo:
    def test_defaults(self) -> None:
        info = MarketInfo()
        assert info.broker_connected is False
        assert info.stream_connected is False
        assert info.symbols_tracked == 0

    def test_connected(self) -> None:
        info = MarketInfo(
            broker_connected=True,
            broker_provider="AngelOne",
            stream_connected=True,
            symbols_tracked=24,
        )
        assert info.broker_provider == "AngelOne"
        assert info.symbols_tracked == 24


class TestTradingInfo:
    def test_defaults(self) -> None:
        info = TradingInfo()
        assert info.live_status == "Stopped"
        assert info.paper_status == "Stopped"
        assert info.backtests_today == 0


class TestHealthInfo:
    def test_defaults(self) -> None:
        info = HealthInfo()
        assert info.monitoring_status == "Unknown"
        assert info.critical_alerts == 0
        assert info.recovery_status == "Idle"


class TestSystemInfo:
    def test_defaults(self) -> None:
        info = SystemInfo()
        assert info.version == "1.0.0"
        assert info.environment == "Development"


# ──────────────────────────────────────────────────
# Widget rendering tests
# ──────────────────────────────────────────────────


class TestRuntimeCard:
    def test_update_data_running(self) -> None:
        card = RuntimeCard()
        card._title = MagicMock()
        card._status = MagicMock()
        card._uptime = MagicMock()
        card._pipeline = MagicMock()
        info = RuntimeInfo(status="Running", uptime="01:00:00", pipeline_executions=10)
        card.update_data(info)
        card._status.update.assert_called_once()
        card._uptime.update.assert_called_once()
        card._pipeline.update.assert_called_once()

    def test_update_data_stopped(self) -> None:
        card = RuntimeCard()
        card._title = MagicMock()
        card._status = MagicMock()
        card._uptime = MagicMock()
        card._pipeline = MagicMock()
        info = RuntimeInfo(status="Stopped")
        card.update_data(info)
        assert "Stopped" in str(card._status.update.call_args)

    def test_status_class_running(self) -> None:
        assert _status_class("Running") == "value-running"

    def test_status_class_stopped(self) -> None:
        assert _status_class("Stopped") == "value-stopped"

    def test_status_class_paused(self) -> None:
        assert _status_class("Paused") == "value-paused"

    def test_status_class_unknown(self) -> None:
        assert _status_class("Unknown") == "value-default"


class TestMarketCard:
    def test_update_data_connected(self) -> None:
        card = MarketCard()
        card._title = MagicMock()
        card._broker = MagicMock()
        card._stream = MagicMock()
        card._symbols = MagicMock()
        info = MarketInfo(
            broker_connected=True,
            broker_provider="Paper",
            stream_connected=True,
            symbols_tracked=24,
        )
        card.update_data(info)
        card._broker.update.assert_called_once()
        card._stream.update.assert_called_once()
        card._symbols.update.assert_called_once()

    def test_update_data_disconnected(self) -> None:
        card = MarketCard()
        card._title = MagicMock()
        card._broker = MagicMock()
        card._stream = MagicMock()
        card._symbols = MagicMock()
        info = MarketInfo(broker_connected=False, stream_connected=False)
        card.update_data(info)
        broker_call = str(card._broker.update.call_args)
        assert "Disconnected" in broker_call


class TestTradingCard:
    def test_update_data(self) -> None:
        card = TradingCard()
        card._title = MagicMock()
        card._live = MagicMock()
        card._paper = MagicMock()
        card._backtests = MagicMock()
        info = TradingInfo(
            live_status="Running", paper_status="Stopped", backtests_today=4
        )
        card.update_data(info)
        card._live.update.assert_called_once()
        card._paper.update.assert_called_once()
        card._backtests.update.assert_called_once()

    def test_trading_status_class_running(self) -> None:
        assert _trading_status_class("Running") == "value-active"

    def test_trading_status_class_stopped(self) -> None:
        assert _trading_status_class("Stopped") == "value-inactive"

    def test_trading_status_class_unknown(self) -> None:
        assert _trading_status_class("Unknown") == "value-default"


class TestHealthCard:
    def test_update_data_healthy(self) -> None:
        card = HealthCard()
        card._title = MagicMock()
        card._monitoring = MagicMock()
        card._alerts = MagicMock()
        card._recovery = MagicMock()
        info = HealthInfo(
            monitoring_status="Healthy",
            critical_alerts=0,
            total_alerts=0,
            recovery_status="Idle",
        )
        card.update_data(info)
        card._monitoring.update.assert_called_once()
        card._alerts.update.assert_called_once()
        card._recovery.update.assert_called_once()

    def test_update_data_critical_alerts(self) -> None:
        card = HealthCard()
        card._title = MagicMock()
        card._monitoring = MagicMock()
        card._alerts = MagicMock()
        card._recovery = MagicMock()
        info = HealthInfo(critical_alerts=3, total_alerts=10)
        card.update_data(info)
        alert_call = str(card._alerts.update.call_args)
        assert "Critical" in alert_call


class TestSystemCard:
    def test_update_data(self) -> None:
        card = SystemCard()
        card._title = MagicMock()
        card._version = MagicMock()
        card._environment = MagicMock()
        card._deployment = MagicMock()
        info = SystemInfo(
            version="2.0.0", environment="Production", deployment_status="Running"
        )
        card.update_data(info)
        card._version.update.assert_called_once()
        card._environment.update.assert_called_once()
        card._deployment.update.assert_called_once()


# ──────────────────────────────────────────────────
# Format helper tests
# ──────────────────────────────────────────────────


class TestFormatUptime:
    def test_zero(self) -> None:
        assert _format_uptime(0) == "00:00:00"

    def test_seconds_only(self) -> None:
        assert _format_uptime(45) == "00:00:45"

    def test_minutes_and_seconds(self) -> None:
        assert _format_uptime(125) == "00:02:05"

    def test_hours_minutes_seconds(self) -> None:
        assert _format_uptime(8091) == "02:14:51"

    def test_large_uptime(self) -> None:
        assert _format_uptime(3661) == "01:01:01"


# ──────────────────────────────────────────────────
# Screen tests (using textual.testing)
# ──────────────────────────────────────────────────


class TestDashboardScreenUnit:
    def test_screen_creation(self) -> None:
        screen = DashboardScreen()
        assert screen is not None

    def test_default_state(self) -> None:
        screen = DashboardScreen()
        assert screen.state.runtime.status == "Unknown"

    def test_set_state_builder(self) -> None:
        screen = DashboardScreen()

        def builder() -> DashboardState:
            return DashboardState(runtime=RuntimeInfo(status="Running"))

        screen.set_state_builder(builder)
        assert screen._state_builder is builder

    def test_refresh_state_with_builder(self) -> None:
        screen = DashboardScreen()
        custom_state = DashboardState(
            runtime=RuntimeInfo(status="Running", uptime="01:00:00"),
            market=MarketInfo(broker_connected=True, symbols_tracked=10),
            trading=TradingInfo(live_status="Running", backtests_today=3),
            health=HealthInfo(monitoring_status="Healthy", critical_alerts=0),
            system=SystemInfo(version="2.0.0", environment="Production"),
        )
        screen.set_state_builder(lambda: custom_state)
        screen._refresh_state()
        assert screen.state.runtime.status == "Running"
        assert screen.state.market.symbols_tracked == 10

    def test_refresh_state_without_builder(self) -> None:
        screen = DashboardScreen()
        screen._refresh_state()
        assert screen.state.runtime.status == "Unknown"

    def test_refresh_state_builder_exception(self) -> None:
        screen = DashboardScreen()
        screen.set_state_builder(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        screen._refresh_state()
        assert screen.state.runtime.status == "Unknown"


# ──────────────────────────────────────────────────
# App tests (using textual.testing)
# ──────────────────────────────────────────────────


class TestTITANApp:
    def test_app_creation(self) -> None:
        app = TITANApp()
        assert app is not None

    def test_set_state_builder(self) -> None:
        app = TITANApp()

        def builder() -> DashboardState:
            return DashboardState()

        app.set_state_builder(builder)
        assert app._state_builder is builder


# ──────────────────────────────────────────────────
# Async integration tests (textual.testing)
# ──────────────────────────────────────────────────


class TestDashboardAsync:
    """Async tests using textual.testing.AppTest."""

    @pytest.mark.asyncio
    async def test_app_mounts(self) -> None:
        app = TITANApp()
        async with app.run_test():
            assert app.screen is not None

    @pytest.mark.asyncio
    async def test_dashboard_screen_is_default(self) -> None:
        app = TITANApp()
        async with app.run_test():
            assert isinstance(app.screen, DashboardScreen)

    @pytest.mark.asyncio
    async def test_cards_are_mounted(self) -> None:
        app = TITANApp()
        async with app.run_test():
            screen = app.screen
            assert screen.query_one("#runtime-card") is not None
            assert screen.query_one("#market-card") is not None
            assert screen.query_one("#trading-card") is not None
            assert screen.query_one("#health-card") is not None
            assert screen.query_one("#system-card") is not None

    @pytest.mark.asyncio
    async def test_title_is_shown(self) -> None:
        app = TITANApp()
        async with app.run_test():
            from textual.widgets import Static

            title = app.screen.query_one("#dashboard-title", Static)
            assert "TITAN Dashboard" in str(title.render())

    @pytest.mark.asyncio
    async def test_refresh_indicator_exists(self) -> None:
        app = TITANApp()
        async with app.run_test():
            from textual.widgets import Static

            indicator = app.screen.query_one("#refresh-indicator", Static)
            assert indicator is not None

    @pytest.mark.asyncio
    async def test_manual_refresh(self) -> None:
        app = TITANApp()
        async with app.run_test():
            screen = app.screen
            assert isinstance(screen, DashboardScreen)
            screen.action_refresh()
            from textual.widgets import Static

            indicator = screen.query_one("#refresh-indicator", Static)
            assert "Last refresh:" in str(indicator.render())

    @pytest.mark.asyncio
    async def test_state_builder_is_called(self) -> None:
        call_count = 0

        def counting_builder() -> DashboardState:
            nonlocal call_count
            call_count += 1
            return DashboardState()

        app = TITANApp()
        app.set_state_builder(counting_builder)
        async with app.run_test():
            screen = app.screen
            assert isinstance(screen, DashboardScreen)
            screen.set_state_builder(counting_builder)
            screen._refresh_state()
            assert call_count >= 1

    @pytest.mark.asyncio
    async def test_widget_data_updates_on_refresh(self) -> None:
        def custom_builder() -> DashboardState:
            return DashboardState(
                runtime=RuntimeInfo(
                    status="Running", uptime="05:00:00", pipeline_executions=100
                ),
                market=MarketInfo(broker_connected=True, symbols_tracked=42),
                trading=TradingInfo(live_status="Running", backtests_today=7),
                health=HealthInfo(
                    monitoring_status="Healthy",
                    critical_alerts=0,
                    recovery_status="Idle",
                ),
                system=SystemInfo(version="3.0.0", environment="Production"),
            )

        app = TITANApp()
        app.set_state_builder(custom_builder)
        async with app.run_test():
            screen = app.screen
            assert isinstance(screen, DashboardScreen)
            screen.set_state_builder(custom_builder)
            screen._refresh_state()
            assert screen.state.runtime.status == "Running"
            assert screen.state.market.symbols_tracked == 42
            assert screen.state.trading.backtests_today == 7
            assert screen.state.system.version == "3.0.0"

    @pytest.mark.asyncio
    async def test_keyboard_q_quits(self) -> None:
        app = TITANApp()
        async with app.run_test() as pilot:
            await pilot.press("q")
            assert app.is_running is False


# ──────────────────────────────────────────────────
# State builder integration tests
# ──────────────────────────────────────────────────


class TestStateBuilder:
    def test_format_uptime_various(self) -> None:
        cases = [
            (0, "00:00:00"),
            (59, "00:00:59"),
            (60, "00:01:00"),
            (3600, "01:00:00"),
            (3661, "01:01:01"),
            (86400, "24:00:00"),
        ]
        for seconds, expected in cases:
            assert _format_uptime(seconds) == expected

    def test_dashboard_state_composition(self) -> None:
        state = DashboardState(
            runtime=RuntimeInfo(status="Running"),
            market=MarketInfo(broker_connected=True),
            trading=TradingInfo(live_status="Running"),
            health=HealthInfo(monitoring_status="Healthy"),
            system=SystemInfo(version="1.0.0"),
            last_refresh="12:00:00",
        )
        assert state.runtime.status == "Running"
        assert state.market.broker_connected is True
        assert state.trading.live_status == "Running"
        assert state.health.monitoring_status == "Healthy"
        assert state.system.version == "1.0.0"
        assert state.last_refresh == "12:00:00"
