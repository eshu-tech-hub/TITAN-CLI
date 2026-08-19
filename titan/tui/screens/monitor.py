"""Monitoring & Alerting screen — read-only visualization of operational state."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, ClassVar

from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Static

from titan.tui.models import MonitoringScreenState
from titan.tui.widgets.monitor import (
    ActiveAlertsWidget,
    AlertHistoryWidget,
    AlertSummaryWidget,
    MetricsWidget,
    MonitoringEventsWidget,
    RecoveryStatusWidget,
    SystemHealthWidget,
    TelemetryWidget,
)

if TYPE_CHECKING:
    from collections.abc import Callable

REFRESH_INTERVAL = 1.0


class MonitoringScreen(Screen):
    """Monitoring & Alerting screen with eight operational widgets.

    Refreshes automatically every REFRESH_INTERVAL seconds.
    Data is read-only from all managers.
    """

    DEFAULT_CSS: ClassVar[str] = """
    MonitoringScreen {
        layout: vertical;
        padding: 1 2;
    }
    #monitor-title {
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
    #monitor-row-1 {
        height: auto;
    }
    #monitor-row-1 > * {
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
        self._state = MonitoringScreenState()
        self._state_builder: Callable[[], MonitoringScreenState] | None = None
        self._system_health_widget: SystemHealthWidget | None = None
        self._telemetry_widget: TelemetryWidget | None = None
        self._alert_summary_widget: AlertSummaryWidget | None = None
        self._recovery_status_widget: RecoveryStatusWidget | None = None
        self._metrics_widget: MetricsWidget | None = None
        self._active_alerts_widget: ActiveAlertsWidget | None = None
        self._alert_history_widget: AlertHistoryWidget | None = None
        self._monitoring_events_widget: MonitoringEventsWidget | None = None

    def compose(self):  # type: ignore[override]
        yield Static("Monitoring & Alerting", id="monitor-title")
        yield Static("", id="refresh-indicator")
        with VerticalScroll(id="widgets-container"):
            with Horizontal(id="monitor-row-1"):
                self._system_health_widget = SystemHealthWidget(id="system-health")
                self._telemetry_widget = TelemetryWidget(id="telemetry")
                self._alert_summary_widget = AlertSummaryWidget(id="alert-summary")
                self._recovery_status_widget = RecoveryStatusWidget(
                    id="recovery-status"
                )
                yield self._system_health_widget
                yield self._telemetry_widget
                yield self._alert_summary_widget
                yield self._recovery_status_widget
            self._metrics_widget = MetricsWidget(id="resource-metrics")
            yield self._metrics_widget
            self._active_alerts_widget = ActiveAlertsWidget(id="active-alerts")
            yield self._active_alerts_widget
            self._alert_history_widget = AlertHistoryWidget(id="alert-history")
            yield self._alert_history_widget
            self._monitoring_events_widget = MonitoringEventsWidget(
                id="monitoring-events"
            )
            yield self._monitoring_events_widget

    def on_mount(self) -> None:
        self.set_interval(REFRESH_INTERVAL, self._tick_refresh)

    def set_state_builder(self, builder: Callable[[], MonitoringScreenState]) -> None:
        self._state_builder = builder

    def _tick_refresh(self) -> None:
        self._refresh_state()

    def _refresh_state(self) -> None:
        if self._state_builder is not None:
            try:
                self._state = self._state_builder()
            except Exception:
                self._state = MonitoringScreenState()
        self._update_widgets()
        self._update_refresh_indicator()

    def _update_widgets(self) -> None:
        if self._system_health_widget is not None:
            self._system_health_widget.update_data(self._state.system_health)
        if self._telemetry_widget is not None:
            self._telemetry_widget.update_data(self._state.telemetry)
        if self._alert_summary_widget is not None:
            self._alert_summary_widget.update_data(self._state.alert_summary)
        if self._recovery_status_widget is not None:
            self._recovery_status_widget.update_data(self._state.recovery_status)
        if self._metrics_widget is not None:
            self._metrics_widget.update_data(self._state.resource_metrics)
        if self._active_alerts_widget is not None:
            self._active_alerts_widget.update_data(self._state.active_alerts)
        if self._alert_history_widget is not None:
            self._alert_history_widget.update_data(self._state.alert_history)
        if self._monitoring_events_widget is not None:
            self._monitoring_events_widget.update_data(self._state.monitoring_events)

    def _update_refresh_indicator(self) -> None:
        try:
            indicator = self.query_one("#refresh-indicator", Static)
            now = datetime.now(UTC).strftime("%H:%M:%S")
            indicator.update(f"Last refresh: {now}")
        except Exception:
            pass

    def action_refresh(self) -> None:
        self._refresh_state()

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_scroll_up_line(self) -> None:
        try:
            container = self.query_one("#widgets-container", VerticalScroll)
            container.scroll_up(animate=False)
        except Exception:
            pass

    def action_scroll_down_line(self) -> None:
        try:
            container = self.query_one("#widgets-container", VerticalScroll)
            container.scroll_down(animate=False)
        except Exception:
            pass

    def action_scroll_up(self) -> None:
        try:
            container = self.query_one("#widgets-container", VerticalScroll)
            container.scroll_home(animate=False)
        except Exception:
            pass

    def action_scroll_down(self) -> None:
        try:
            container = self.query_one("#widgets-container", VerticalScroll)
            container.scroll_end(animate=False)
        except Exception:
            pass

    def action_scroll_top(self) -> None:
        try:
            container = self.query_one("#widgets-container", VerticalScroll)
            container.scroll_home(animate=False)
        except Exception:
            pass

    def action_scroll_bottom(self) -> None:
        try:
            container = self.query_one("#widgets-container", VerticalScroll)
            container.scroll_end(animate=False)
        except Exception:
            pass

    @property
    def state(self) -> MonitoringScreenState:
        return self._state
