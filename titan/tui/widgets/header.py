"""Reusable header widget for the TITAN TUI application shell."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from textual.widget import Widget
from textual.widgets import Static

from titan.tui.theme import get_theme


class HeaderWidget(Widget):
    """Persistent header bar displaying TITAN version, hostname, uptime, and runtime indicator."""

    DEFAULT_CSS = """
    HeaderWidget {
        height: 1;
        dock: top;
        background: $primary;
        color: $text;
        padding: 0 1;
        layout: horizontal;
    }
    #header-version {
        width: auto;
        padding: 0 1;
    }
    #header-spacer {
        width: 1fr;
    }
    #header-hostname {
        width: auto;
        padding: 0 1;
    }
    #header-profile {
        width: auto;
        padding: 0 1;
    }
    #header-uptime {
        width: auto;
        padding: 0 1;
    }
    #header-runtime {
        width: auto;
        padding: 0 1;
    }
    #header-clock {
        width: auto;
        padding: 0 1;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._version: str = "TITAN"
        self._hostname: str = ""
        self._profile: str = "default"
        self._uptime: str = "00:00:00"
        self._runtime_status: str = "Stopped"
        self._clock: str = ""

    def compose(self):  # type: ignore[override]
        self._version_widget = Static("TITAN", id="header-version")
        self._spacer = Static("", id="header-spacer")
        self._hostname_widget = Static("", id="header-hostname")
        self._profile_widget = Static("", id="header-profile")
        self._uptime_widget = Static("", id="header-uptime")
        self._runtime_widget = Static("", id="header-runtime")
        self._clock_widget = Static("", id="header-clock")
        yield self._version_widget
        yield self._spacer
        yield self._hostname_widget
        yield self._profile_widget
        yield self._uptime_widget
        yield self._runtime_widget
        yield self._clock_widget

    def update_data(
        self,
        *,
        version: str | None = None,
        hostname: str | None = None,
        profile: str | None = None,
        uptime: str | None = None,
        runtime_status: str | None = None,
    ) -> None:
        """Update header fields. Only provided fields are updated."""
        if version is not None:
            self._version = version
        if hostname is not None:
            self._hostname = hostname
        if profile is not None:
            self._profile = profile
        if uptime is not None:
            self._uptime = uptime
        if runtime_status is not None:
            self._runtime_status = runtime_status
        self._render_all()

    def update_clock(self) -> None:
        """Update the clock display. Called every second."""
        self._clock = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
        if hasattr(self, "_clock_widget"):
            self._clock_widget.update(f"[bold]{self._clock}[/bold]")

    def _render_all(self) -> None:
        if not hasattr(self, "_version_widget"):
            return
        theme = get_theme()
        self._version_widget.update(f"[bold]TITAN {self._version}[/bold]")
        if self._hostname:
            self._hostname_widget.update(f"H: {self._hostname}")
        else:
            self._hostname_widget.update("")
        self._profile_widget.update(f"P: {self._profile}")
        self._uptime_widget.update(f"U: {self._uptime}")
        status = self._runtime_status
        if status.lower() in ("running", "connected"):
            indicator = f"[{theme.success}]●[/]"
        elif status.lower() in ("paused",):
            indicator = f"[{theme.warning}]●[/]"
        else:
            indicator = f"[{theme.text_muted}]○[/]"
        self._runtime_widget.update(f"{indicator} {status}")
        self.update_clock()

    def render(self) -> str:
        return ""
