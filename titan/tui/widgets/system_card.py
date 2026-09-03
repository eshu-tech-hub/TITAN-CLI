"""System info card widget."""

from __future__ import annotations

from typing import Any

from textual.widget import Widget
from textual.widgets import Static

from titan.tui.models import SystemInfo
from titan.tui.widgets import markup_color


class SystemCard(Widget):
    """Displays version, environment, and deployment status."""

    DEFAULT_CSS = """
    SystemCard {
        height: auto;
        min-height: 6;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    SystemCard .card-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    SystemCard .card-row {
        height: 1;
    }
    SystemCard .value-running {
        color: $success;
    }
    SystemCard .value-stopped {
        color: $text-muted;
    }
    SystemCard .value-default {
        color: $text;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = SystemInfo()

    def compose(self):  # type: ignore[override]
        self._title = Static("System", classes="card-title")
        self._version = Static("", classes="card-row")
        self._environment = Static("", classes="card-row")
        self._deployment = Static("", classes="card-row")
        yield self._title
        yield self._version
        yield self._environment
        yield self._deployment

    def update_data(self, info: SystemInfo) -> None:
        """Update card with new system info."""
        self._info = info
        self._version.update(f"[bold]Version:[/bold] {info.version}")
        self._environment.update(f"[bold]Environment:[/bold] {info.environment}")
        dep_cls = _deploy_class(info.deployment_status)
        self._deployment.update(
            f"[bold]Deployment:[/bold] [{markup_color(dep_cls)}]{info.deployment_status}[/]"
        )

    def render(self) -> str:  # type: ignore[override]
        return ""


def _deploy_class(status: str) -> str:
    lower = status.lower()
    if lower in ("running",):
        return "value-running"
    if lower in ("stopped", "error"):
        return "value-stopped"
    return "value-default"
