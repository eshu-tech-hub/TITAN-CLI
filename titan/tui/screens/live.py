"""Live Trading screen — read-only visualization of live trading state."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar

from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Static

from titan.tui.models import LiveScreenState
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

if TYPE_CHECKING:
    from collections.abc import Callable

REFRESH_INTERVAL = 1.0


class LiveScreen(VerticalScroll):
    """Live Trading view with eight monitoring widgets.

    Refreshes automatically every REFRESH_INTERVAL seconds.
    Data is read-only from all managers.
    """

    DEFAULT_CSS: ClassVar[str] = """
    LiveScreen {
        layout: vertical;
        padding: 1 2;
    }
    #live-title {
        text-style: bold;
        color: $primary;
        text-align: center;
        height: 1;
        margin-bottom: 1;
    }
    #refresh-indicator {
        text-align: right;
        height: 1;
        color: $text-muted;
        dock: top;
    }
    #widgets-container {
        height: 1fr;
    }
    #live-row-1, #live-row-2, #live-row-3 {
        height: auto;
    }
    #live-row-1 > *, #live-row-2 > *, #live-row-3 > * {
        width: 1fr;
    }
    """

    BINDINGS: ClassVar[list] = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("escape", "back", "Back"),
        ("up", "scroll_up_line", "Scroll Up"),
        ("down", "scroll_down_line", "Scroll Down"),
        ("page_up", "scroll_up", "Scroll Up"),
        ("page_down", "scroll_down", "Scroll Down"),
        ("home", "scroll_top", "Scroll Top"),
        ("end", "scroll_bottom", "Scroll Bottom"),
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._state = LiveScreenState()
        self._state_builder: Callable[[], LiveScreenState] | None = None
        self._live_status_widget: LiveStatusWidget | None = None
        self._broker_status_widget: BrokerStatusWidget | None = None
        self._account_widget: AccountWidget | None = None
        self._exposure_widget: ExposureWidget | None = None
        self._health_widget: LiveHealthWidget | None = None
        self._positions_widget: LivePositionsWidget | None = None
        self._orders_widget: LiveOrdersWidget | None = None
        self._executions_widget: ExecutionsWidget | None = None

    def compose(self):  # type: ignore[override]
        yield Static("Live Trading", id="live-title")
        yield Static("", id="refresh-indicator")
        with VerticalScroll(id="widgets-container"):
            with Horizontal(id="live-row-1"):
                self._live_status_widget = LiveStatusWidget(id="live-status")
                self._broker_status_widget = BrokerStatusWidget(id="broker-status")
                self._account_widget = AccountWidget(id="live-account")
                yield self._live_status_widget
                yield self._broker_status_widget
                yield self._account_widget
            with Horizontal(id="live-row-2"):
                self._exposure_widget = ExposureWidget(id="live-exposure")
                self._health_widget = LiveHealthWidget(id="live-health")
                self._positions_widget = LivePositionsWidget(id="live-positions")
                yield self._exposure_widget
                yield self._health_widget
                yield self._positions_widget
            with Horizontal(id="live-row-3"):
                self._orders_widget = LiveOrdersWidget(id="live-orders")
                self._executions_widget = ExecutionsWidget(id="live-executions")
                yield self._orders_widget
                yield self._executions_widget

    def on_mount(self) -> None:
        self.set_interval(REFRESH_INTERVAL, self._tick_refresh)

    def set_state_builder(self, builder: Callable[[], LiveScreenState]) -> None:
        self._state_builder = builder

    def _tick_refresh(self) -> None:
        self._refresh_state()

    def _refresh_state(self) -> None:
        try:
            if self._state_builder is not None:
                try:
                    self._state = self._state_builder()
                except Exception:  # noqa: BLE001
                    self._state = LiveScreenState()
            self._update_widgets()
            self._update_refresh_indicator()
        except Exception as e:
            import traceback
            with open("tui_ui_crash.log", "a") as f:
                f.write(f"UI RENDER CRASH: {e}\n{traceback.format_exc()}\n")

    def _update_widgets(self) -> None:
        if self._live_status_widget is not None:
            self._live_status_widget.update_data(self._state.live_status)
        if self._broker_status_widget is not None:
            self._broker_status_widget.update_data(self._state.broker_status)
        if self._account_widget is not None:
            self._account_widget.update_data(self._state.account)
        if self._exposure_widget is not None:
            self._exposure_widget.update_data(self._state.exposure)
        if self._health_widget is not None:
            self._update_health_widget()
        if self._positions_widget is not None:
            self._positions_widget.update_data(self._state.positions)
        if self._orders_widget is not None:
            self._orders_widget.update_data(self._state.orders)
        if self._executions_widget is not None:
            self._executions_widget.update_data(self._state.executions)

    def _update_health_widget(self) -> None:
        try:
            from titan.cli.common import (
                get_alert_manager,
                get_monitoring_manager,
                get_recovery_manager,
            )

            mon = get_monitoring_manager()
            mon_report = mon.generate_report()
            monitoring_status = (
                str(mon_report.system_health) if mon_report.system_health else "Unknown"
            )
        except Exception:  # noqa: BLE001
            monitoring_status = "Unknown"
        try:
            al = get_alert_manager()
            al_report = al.generate_report()
            critical = al_report.critical_alerts
            total = al_report.total_alerts
        except Exception:  # noqa: BLE001
            critical = 0
            total = 0
        try:
            rm = get_recovery_manager()
            rm_report = rm.generate_report()
            recovery_status = (
                rm_report.status.value
                if hasattr(rm_report.status, "value")
                else str(rm_report.status)
            )
            recovery_attempts = rm_report.total_attempts
        except Exception:  # noqa: BLE001
            recovery_status = "Idle"
            recovery_attempts = 0
        if self._health_widget is not None:
            self._health_widget.update_data(
                monitoring_status=monitoring_status,
                critical_alerts=critical,
                total_alerts=total,
                recovery_status=recovery_status,
                recovery_attempts=recovery_attempts,
            )

    def _update_refresh_indicator(self) -> None:
        try:
            indicator = self.query_one("#refresh-indicator", Static)
            now = datetime.now().strftime("%H:%M:%S")  # noqa: DTZ005 - local time for display
            indicator.update(f"Last refresh: {now}")
        except Exception:  # noqa: BLE001, S110 - silent pass for UI resilience
            pass

    def action_refresh(self) -> None:
        self._refresh_state()

    def action_back(self) -> None:
        """Return to the previous view via the shell router."""
        try:
            self.app.action_go_back()
        except Exception:  # noqa: BLE001, S110
            pass

    def action_scroll_up_line(self) -> None:
        try:
            container = self.query_one("#widgets-container", VerticalScroll)
            container.scroll_up(animate=False)
        except Exception:  # noqa: BLE001, S110
            pass

    def action_scroll_down_line(self) -> None:
        try:
            container = self.query_one("#widgets-container", VerticalScroll)
            container.scroll_down(animate=False)
        except Exception:  # noqa: BLE001, S110
            pass

    def action_scroll_up(self) -> None:
        try:
            container = self.query_one("#widgets-container", VerticalScroll)
            container.scroll_home(animate=False)
        except Exception:  # noqa: BLE001, S110
            pass

    def action_scroll_down(self) -> None:
        try:
            container = self.query_one("#widgets-container", VerticalScroll)
            container.scroll_end(animate=False)
        except Exception:  # noqa: BLE001, S110
            pass

    def action_scroll_top(self) -> None:
        try:
            container = self.query_one("#widgets-container", VerticalScroll)
            container.scroll_home(animate=False)
        except Exception:  # noqa: BLE001, S110
            pass

    def action_scroll_bottom(self) -> None:
        try:
            container = self.query_one("#widgets-container", VerticalScroll)
            container.scroll_end(animate=False)
        except Exception:  # noqa: BLE001, S110
            pass

    @property
    def state(self) -> LiveScreenState:
        return self._state
