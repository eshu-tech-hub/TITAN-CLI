"""Runtime status card widget."""

from __future__ import annotations

from typing import Any

from textual.widget import Widget
from textual.widgets import Static

from titan.tui.models import RuntimeInfo


class RuntimeCard(Widget):
    """Displays runtime engine status, uptime, and pipeline info."""

    DEFAULT_CSS = """
    RuntimeCard {
        height: auto;
        min-height: 7;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    RuntimeCard .card-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    RuntimeCard .card-row {
        height: 1;
    }
    RuntimeCard .label {
        color: $text-muted;
    }
    RuntimeCard .value-running {
        color: $success;
    }
    RuntimeCard .value-stopped {
        color: $error;
    }
    RuntimeCard .value-paused {
        color: $warning;
    }
    RuntimeCard .value-default {
        color: $text;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = RuntimeInfo()

    def compose(self):  # type: ignore[override]
        self._title = Static("Runtime", classes="card-title")
        self._status = Static("", classes="card-row")
        self._uptime = Static("", classes="card-row")
        self._pipeline = Static("", classes="card-row")
        yield self._title
        yield self._status
        yield self._uptime
        yield self._pipeline

    def update_data(self, info: RuntimeInfo) -> None:
        """Update card with new runtime info."""
        self._info = info
        status_cls = _status_class(info.status)
        self._status.update(
            f'[bold]Status:[/bold] <span class="{status_cls}">{info.status}</span>'
        )
        self._uptime.update(f"[bold]Uptime:[/bold] {info.uptime}")
        self._pipeline.update(
            f"[bold]Pipeline:[/bold] {info.pipeline_executions} executions"
        )

    def render(self) -> str:  # type: ignore[override]
        return ""


def _status_class(status: str) -> str:
    lower = status.lower()
    if lower in ("running", "connected", "healthy"):
        return "value-running"
    if lower in ("stopped", "error", "disconnected"):
        return "value-stopped"
    if lower in ("paused", "starting", "stopping"):
        return "value-paused"
    return "value-default"
