"""Reusable status bar widget for the TITAN TUI application shell."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from textual.widget import Widget
from textual.widgets import Static

from titan.tui.theme import get_theme


class StatusBarWidget(Widget):
    """Persistent status bar showing environment, runtime, broker, mode, refresh, and time."""

    DEFAULT_CSS = """
    StatusBarWidget {
        height: 1;
        dock: bottom;
        background: $surface;
        color: $text-muted;
        border-top: solid $primary;
        padding: 0 1;
        layout: horizontal;
    }
    #status-env {
        width: auto;
        padding: 0 1;
    }
    #status-runtime {
        width: auto;
        padding: 0 1;
    }
    #status-broker {
        width: auto;
        padding: 0 1;
    }
    #status-mode {
        width: auto;
        padding: 0 1;
    }
    #status-refresh {
        width: auto;
        padding: 0 1;
    }
    #status-spacer {
        width: 1fr;
    }
    #status-help {
        width: auto;
        padding: 0 1;
        color: $primary;
    }
    #status-time {
        width: auto;
        padding: 0 1;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._environment: str = "Development"
        self._runtime_status: str = "Stopped"
        self._broker_status: str = "Disconnected"
        self._mode: str = "Paper"
        self._refresh_interval: float = 1.0
        self._time: str = ""

    def compose(self):  # type: ignore[override]
        self._env_widget = Static("Development", id="status-env")
        self._runtime_widget = Static("○ Stopped", id="status-runtime")
        self._broker_widget = Static("Broker: --", id="status-broker")
        self._mode_widget = Static("Mode: Paper", id="status-mode")
        self._refresh_widget = Static("Refresh: 1s", id="status-refresh")
        self._spacer = Static("", id="status-spacer")
        self._help_widget = Static("F1 Help", id="status-help")
        self._time_widget = Static("", id="status-time")
        yield self._env_widget
        yield self._runtime_widget
        yield self._broker_widget
        yield self._mode_widget
        yield self._refresh_widget
        yield self._spacer
        yield self._help_widget
        yield self._time_widget

    def update_data(
        self,
        *,
        environment: str | None = None,
        runtime_status: str | None = None,
        broker_status: str | None = None,
        mode: str | None = None,
        refresh_interval: float | None = None,
    ) -> None:
        """Update status bar fields."""
        if environment is not None:
            self._environment = environment
        if runtime_status is not None:
            self._runtime_status = runtime_status
        if broker_status is not None:
            self._broker_status = broker_status
        if mode is not None:
            self._mode = mode
        if refresh_interval is not None:
            self._refresh_interval = refresh_interval
        self._render_all()

    def update_time(self) -> None:
        """Update the clock. Called every second."""
        self._time = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
        if hasattr(self, "_time_widget"):
            self._time_widget.update(self._time)

    def _render_all(self) -> None:
        if not hasattr(self, "_env_widget"):
            return
        theme = get_theme()
        self._env_widget.update(self._environment)
        status = self._runtime_status
        if status.lower() in ("running", "connected"):
            indicator = f"[{theme.success}]●[/]"
        elif status.lower() in ("paused",):
            indicator = f"[{theme.warning}]●[/]"
        else:
            indicator = f"[{theme.text_muted}]○[/]"
        self._runtime_widget.update(f"{indicator} {status}")
        self._broker_widget.update(f"Broker: {self._broker_status}")
        self._mode_widget.update(f"Mode: {self._mode}")
        self._refresh_widget.update(f"Refresh: {self._refresh_interval:.0f}s")
        self.update_time()

    def render(self) -> str:
        return ""
