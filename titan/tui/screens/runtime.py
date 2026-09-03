"""Runtime screen — detailed runtime status with auto-refresh."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar

from textual import work
from textual.containers import VerticalScroll
from textual.widgets import Static

from titan.cli.common import get_runtime_engine
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


class RuntimeScreen(VerticalScroll):
    """Detailed runtime view with six status widgets.

    Refreshes automatically every REFRESH_INTERVAL seconds.
    Data is read-only from all managers.
    """

    DEFAULT_CSS: ClassVar[str] = """
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

    BINDINGS: ClassVar[list] = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("s", "start_engine", "Start Engine"),
        ("x", "stop_engine", "Stop Engine"),
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
            except Exception:  # noqa: BLE001
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
            now = datetime.now().strftime("%H:%M:%S")  # noqa: DTZ005 - local time for display
            indicator.update(f"Last refresh: {now}")
        except Exception:  # noqa: BLE001, S110 - silent pass for UI resilience
            pass

    def action_refresh(self) -> None:
        self._refresh_state()

    # ─── Engine control ────────────────────────────────────────

    @work(exclusive=True, thread=True)
    def _start_engine_worker(self) -> None:
        """Start the runtime engine off the asyncio event loop.

        engine.start() performs blocking broker/stream I/O; running it in a
        Textual thread worker keeps the TUI responsive. Failures are surfaced
        via app.notify instead of dying silently in the worker thread.
        """
        try:
            engine = get_runtime_engine()
            engine.start()
        except Exception as exc:  # noqa: BLE001
            self.app.call_from_thread(
                self.app.notify,
                f"Engine Error: {exc!s}",
                title="Failure",
                severity="error",
            )
            self.app.call_from_thread(self._on_engine_start_failed, exc)
        else:
            self.app.call_from_thread(self._on_engine_started)

    @work(exclusive=True, thread=True)
    def _stop_engine_worker(self) -> None:
        """Stop the runtime engine off the asyncio event loop.

        Failures are surfaced via app.notify instead of dying silently in the
        worker thread.
        """
        try:
            engine = get_runtime_engine()
            engine.stop()
        except Exception as exc:  # noqa: BLE001
            self.app.call_from_thread(
                self.app.notify,
                f"Engine Error: {exc!s}",
                title="Failure",
                severity="error",
            )
            self.app.call_from_thread(self._on_engine_stop_failed, exc)
        else:
            self.app.call_from_thread(self._on_engine_stopped)

    def action_start_engine(self) -> None:
        """Start the runtime engine as the primary control node."""
        engine = get_runtime_engine()
        if engine.is_running:
            self.notify("Runtime engine is already running.", severity="warning")
            return
        self.notify("Starting runtime engine...")
        self._start_engine_worker()

    def action_stop_engine(self) -> None:
        """Stop the runtime engine gracefully."""
        engine = get_runtime_engine()
        if not engine.is_running:
            self.notify("Runtime engine is not running.", severity="warning")
            return
        self.notify("Stopping runtime engine...")
        self._stop_engine_worker()

    def _on_engine_started(self) -> None:
        self._refresh_state()
        self._update_engine_status_bar("Running")
        self.notify("Runtime engine started.", severity="information")

    def _on_engine_start_failed(self, exc: Exception) -> None:
        self._refresh_state()
        self.notify(f"Failed to start runtime engine: {exc}", severity="error")

    def _on_engine_stopped(self) -> None:
        self._refresh_state()
        self._update_engine_status_bar("Stopped")
        self.notify("Runtime engine stopped.", severity="information")

    def _on_engine_stop_failed(self, exc: Exception) -> None:
        self._refresh_state()
        self.notify(f"Failed to stop runtime engine: {exc}", severity="error")

    def _update_engine_status_bar(self, runtime_status: str) -> None:
        try:
            status_bar = getattr(self.app, "status_bar", None)
        except Exception:  # noqa: BLE001
            return
        if status_bar is not None:
            status_bar.update_data(runtime_status=runtime_status)

    def action_back(self) -> None:
        """Return to the previous view via the shell router."""
        try:
            self.app.action_go_back()
        except Exception:  # noqa: BLE001
            pass

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
