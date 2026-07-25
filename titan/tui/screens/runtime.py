"""Runtime screen — detailed runtime status with auto-refresh."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Static

from titan.tui.models import RuntimeScreenState
from titan.tui.widgets.runtime import (
    EventBusWidget,
    HealthWidget,
    PipelineWidget,
    RuntimeEventsWidget,
    RuntimeStatusWidget,
    StreamWidget,
)

if TYPE_CHECKING:
    from collections.abc import Callable

REFRESH_INTERVAL = 1.0


class RuntimeScreen(Screen):
    """Detailed runtime screen with six status widgets.

    Refreshes automatically every REFRESH_INTERVAL seconds.
    Data is read-only from all managers.
    """

    DEFAULT_CSS = """
    RuntimeScreen {
        layout: vertical;
        padding: 1 2;
    }
    #runtime-title {
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
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("escape", "back", "Back"),
        ("page_up", "scroll_up", "Scroll Up"),
        ("page_down", "scroll_down", "Scroll Down"),
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._state = RuntimeScreenState()
        self._state_builder: Callable[[], RuntimeScreenState] | None = None
        self._engine_widget: RuntimeStatusWidget | None = None
        self._stream_widget: StreamWidget | None = None
        self._pipeline_widget: PipelineWidget | None = None
        self._event_bus_widget: EventBusWidget | None = None
        self._health_widget: HealthWidget | None = None
        self._events_widget: RuntimeEventsWidget | None = None

    def compose(self):  # type: ignore[override]
        yield Static("Runtime", id="runtime-title")
        yield Static("", id="refresh-indicator")
        with VerticalScroll(id="widgets-container"):
            self._engine_widget = RuntimeStatusWidget(id="engine-widget")
            self._stream_widget = StreamWidget(id="stream-widget")
            self._pipeline_widget = PipelineWidget(id="pipeline-widget")
            self._event_bus_widget = EventBusWidget(id="eventbus-widget")
            self._health_widget = HealthWidget(id="health-widget")
            self._events_widget = RuntimeEventsWidget(id="events-widget")
            yield self._engine_widget
            yield self._stream_widget
            yield self._pipeline_widget
            yield self._event_bus_widget
            yield self._health_widget
            yield self._events_widget

    def on_mount(self) -> None:
        self.set_interval(REFRESH_INTERVAL, self._tick_refresh)

    def set_state_builder(self, builder: Callable[[], RuntimeScreenState]) -> None:
        self._state_builder = builder

    def _tick_refresh(self) -> None:
        self._refresh_state()

    def _refresh_state(self) -> None:
        if self._state_builder is not None:
            try:
                self._state = self._state_builder()
            except Exception:
                self._state = RuntimeScreenState()
        self._update_widgets()
        self._update_refresh_indicator()

    def _update_widgets(self) -> None:
        if self._engine_widget is not None:
            self._engine_widget.update_data(self._state.engine)
        if self._stream_widget is not None:
            self._stream_widget.update_data(self._state.stream)
        if self._pipeline_widget is not None:
            self._pipeline_widget.update_data(self._state.pipeline)
        if self._event_bus_widget is not None:
            self._event_bus_widget.update_data(self._state.event_bus)
        if self._health_widget is not None:
            self._health_widget.update_data(self._state.components)
        if self._events_widget is not None:
            self._events_widget.update_data(self._state.events)

    def _update_refresh_indicator(self) -> None:
        try:
            indicator = self.query_one("#refresh-indicator", Static)
            now = datetime.now(timezone.utc).strftime("%H:%M:%S")
            indicator.update(f"Last refresh: {now}")
        except Exception:
            pass

    def action_refresh(self) -> None:
        self._refresh_state()

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_scroll_up(self) -> None:
        """Scroll the events widget up by one page."""
        if self._events_widget is not None:
            self._events_widget.scroll_home(animate=False)

    def action_scroll_down(self) -> None:
        """Scroll the events widget down by one page."""
        if self._events_widget is not None:
            self._events_widget.scroll_end(animate=False)

    @property
    def state(self) -> RuntimeScreenState:
        return self._state
