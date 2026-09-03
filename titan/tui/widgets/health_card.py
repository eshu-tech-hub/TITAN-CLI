"""Health status card widget."""

from __future__ import annotations

from typing import Any

from textual.widget import Widget
from textual.widgets import Static

from titan.tui.models import HealthInfo
from titan.tui.widgets import markup_color


class HealthCard(Widget):
    """Displays monitoring, alerts, and recovery health."""

    DEFAULT_CSS = """
    HealthCard {
        height: auto;
        min-height: 8;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    HealthCard .card-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    HealthCard .card-row {
        height: 1;
    }
    HealthCard .value-healthy {
        color: $success;
    }
    HealthCard .value-unhealthy {
        color: $error;
    }
    HealthCard .value-warning {
        color: $warning;
    }
    HealthCard .value-default {
        color: $text;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = HealthInfo()

    def compose(self):  # type: ignore[override]
        self._title = Static("Health", classes="card-title")
        self._monitoring = Static("", classes="card-row")
        self._alerts = Static("", classes="card-row")
        self._recovery = Static("", classes="card-row")
        yield self._title
        yield self._monitoring
        yield self._alerts
        yield self._recovery

    def update_data(self, info: HealthInfo) -> None:
        """Update card with new health info."""
        self._info = info
        mon_cls = _health_class(info.monitoring_status)
        self._monitoring.update(
            f"[bold]Monitoring:[/bold] [{markup_color(mon_cls)}]{info.monitoring_status}[/]"
        )
        if info.critical_alerts > 0:
            alert_cls = "value-unhealthy"
        elif info.total_alerts > 0:
            alert_cls = "value-warning"
        else:
            alert_cls = "value-healthy"
        alert_text = (
            f"{info.critical_alerts} Critical"
            if info.critical_alerts > 0
            else "0 Critical"
        )
        self._alerts.update(
            f"[bold]Alerts:[/bold] [{markup_color(alert_cls)}]{alert_text}[/]"
            f" ({info.total_alerts} total)"
        )
        rec_cls = _recovery_class(info.recovery_status)
        self._recovery.update(
            f"[bold]Recovery:[/bold] [{markup_color(rec_cls)}]{info.recovery_status}[/]"
            f" ({info.recovery_attempts} attempts)"
        )

    def render(self) -> str:  # type: ignore[override]
        return ""


def _health_class(status: str) -> str:
    lower = status.lower()
    if lower in ("healthy", "ok", "running"):
        return "value-healthy"
    if lower in ("unhealthy", "error", "degraded"):
        return "value-unhealthy"
    if lower in ("warning", "unknown"):
        return "value-warning"
    return "value-default"


def _recovery_class(status: str) -> str:
    lower = status.lower()
    if lower in ("idle", "success", "recovered"):
        return "value-healthy"
    if lower in ("in_progress", "retrying"):
        return "value-warning"
    if lower in ("failed", "error"):
        return "value-unhealthy"
    return "value-default"
