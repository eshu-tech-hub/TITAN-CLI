"""Reusable widgets for the Monitoring & Alerting screen."""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.widgets import Static
from textual.widget import Widget

from titan.tui.models import (
    AlertEntry,
    AlertHistoryEntry,
    AlertSummaryInfo,
    MonitoringEventEntry,
    RecoveryStatusInfo,
    ResourceMetricsInfo,
    ResourceMetricEntry,
    SystemHealthInfo,
    TelemetryInfo,
)


class SystemHealthWidget(Widget):
    """Displays overall system health and subsystem statuses."""

    DEFAULT_CSS = """
    SystemHealthWidget {
        height: auto;
        min-height: 7;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    SystemHealthWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    SystemHealthWidget .card-row {
        height: 1;
    }
    SystemHealthWidget .value-healthy {
        color: $success;
    }
    SystemHealthWidget .value-warning {
        color: $warning;
    }
    SystemHealthWidget .value-critical {
        color: $error;
    }
    SystemHealthWidget .value-offline {
        color: $text-muted;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = SystemHealthInfo()

    def compose(self) -> ComposeResult:
        self._title = Static("System Health", classes="section-title")
        self._overall = Static("", classes="card-row")
        self._counts = Static("", classes="card-row")
        self._subsystem_rows: list[Static] = []
        yield self._title
        yield self._overall
        yield self._counts

    def update_data(self, info: SystemHealthInfo) -> None:
        self._info = info
        if not hasattr(self, "_overall"):
            return
        overall_cls = _health_class(info.overall_status)
        self._overall.update(
            f'[bold]Overall:[/bold] <span class="{overall_cls}">{info.overall_status}</span>'
        )
        self._counts.update(
            f"[bold]Subsystems:[/bold] "
            f'<span class="value-healthy">{info.healthy_count}H</span> '
            f'<span class="value-warning">{info.warning_count}W</span> '
            f'<span class="value-critical">{info.critical_count}C</span> '
            f'<span class="value-offline">{info.offline_count}O</span>'
        )
        for row in self._subsystem_rows:
            row.remove()
        self._subsystem_rows.clear()
        for sub in info.subsystems[:6]:
            sub_cls = _health_class(sub.status)
            row = Static(
                f'  <span class="{sub_cls}">{sub.name}</span>: {sub.status}'
                f" ({sub.latency_ms}ms, {sub.failures} failures)",
                classes="card-row",
            )
            self._subsystem_rows.append(row)
            self.mount(row)

    def render(self) -> str:
        return ""


class TelemetryWidget(Widget):
    """Displays telemetry collection state."""

    DEFAULT_CSS = """
    TelemetryWidget {
        height: auto;
        min-height: 6;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    TelemetryWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    TelemetryWidget .card-row {
        height: 1;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = TelemetryInfo()

    def compose(self):  # type: ignore[override]
        self._title = Static("Telemetry", classes="section-title")
        self._metrics = Static("", classes="card-row")
        self._collectors = Static("", classes="card-row")
        self._collections = Static("", classes="card-row")
        self._uptime = Static("", classes="card-row")
        yield self._title
        yield self._metrics
        yield self._collectors
        yield self._collections
        yield self._uptime

    def update_data(self, info: TelemetryInfo) -> None:
        self._info = info
        if not hasattr(self, "_metrics"):
            return
        self._metrics.update(f"[bold]Total Metrics:[/bold] {info.total_metrics}")
        self._collectors.update(
            f"[bold]Active Collectors:[/bold] {info.active_collectors}"
        )
        self._collections.update(
            f"[bold]Collections:[/bold] {info.total_collections} "
            f"({info.failed_collections} failed)"
        )
        self._uptime.update(f"[bold]Uptime:[/bold] {info.uptime}")

    def render(self) -> str:
        return ""


class AlertSummaryWidget(Widget):
    """Displays alert counts summary."""

    DEFAULT_CSS = """
    AlertSummaryWidget {
        height: auto;
        min-height: 7;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    AlertSummaryWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    AlertSummaryWidget .card-row {
        height: 1;
    }
    AlertSummaryWidget .value-critical {
        color: $error;
    }
    AlertSummaryWidget .value-active {
        color: $warning;
    }
    AlertSummaryWidget .value-resolved {
        color: $success;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = AlertSummaryInfo()

    def compose(self):  # type: ignore[override]
        self._title = Static("Alert Summary", classes="section-title")
        self._total = Static("", classes="card-row")
        self._active = Static("", classes="card-row")
        self._critical = Static("", classes="card-row")
        self._ack = Static("", classes="card-row")
        self._resolved = Static("", classes="card-row")
        yield self._title
        yield self._total
        yield self._active
        yield self._critical
        yield self._ack
        yield self._resolved

    def update_data(self, info: AlertSummaryInfo) -> None:
        self._info = info
        if not hasattr(self, "_total"):
            return
        self._total.update(f"[bold]Total:[/bold] {info.total}")
        self._active.update(
            f'[bold]Active:[/bold] <span class="value-active">{info.active}</span>'
        )
        self._critical.update(
            f'[bold]Critical:[/bold] <span class="value-critical">{info.critical}</span>'
        )
        self._ack.update(f"[bold]Acknowledged:[/bold] {info.acknowledged}")
        self._resolved.update(
            f'[bold]Resolved:[/bold] <span class="value-resolved">{info.resolved}</span>'
        )

    def render(self) -> str:
        return ""


class RecoveryStatusWidget(Widget):
    """Displays recovery framework status."""

    DEFAULT_CSS = """
    RecoveryStatusWidget {
        height: auto;
        min-height: 6;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    RecoveryStatusWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    RecoveryStatusWidget .card-row {
        height: 1;
    }
    RecoveryStatusWidget .value-success {
        color: $success;
    }
    RecoveryStatusWidget .value-failed {
        color: $error;
    }
    RecoveryStatusWidget .value-idle {
        color: $text-muted;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = RecoveryStatusInfo()

    def compose(self):  # type: ignore[override]
        self._title = Static("Recovery Status", classes="section-title")
        self._status = Static("", classes="card-row")
        self._attempts = Static("", classes="card-row")
        self._strategy = Static("", classes="card-row")
        self._components = Static("", classes="card-row")
        yield self._title
        yield self._status
        yield self._attempts
        yield self._strategy
        yield self._components

    def update_data(self, info: RecoveryStatusInfo) -> None:
        self._info = info
        if not hasattr(self, "_status"):
            return
        status_cls = _recovery_class(info.status)
        self._status.update(
            f'[bold]Status:[/bold] <span class="{status_cls}">{info.status}</span>'
        )
        self._attempts.update(
            f"[bold]Attempts:[/bold] {info.total_attempts} "
            f"({info.successful} ok, {info.failed} failed)"
        )
        self._strategy.update(
            f"[bold]Last Strategy:[/bold] {info.last_strategy or 'None'}"
        )
        self._components.update(
            f"[bold]Recovered:[/bold] {info.recovered_components or 'None'}"
        )

    def render(self) -> str:
        return ""


class MetricsWidget(Widget):
    """Displays resource metrics as a dynamic list."""

    DEFAULT_CSS = """
    MetricsWidget {
        height: auto;
        min-height: 4;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    MetricsWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    MetricsWidget .card-row {
        height: 1;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._metrics: tuple[ResourceMetricEntry, ...] = ()
        self._rows: list[Static] = []

    def compose(self):  # type: ignore[override]
        self._title = Static("Resource Metrics", classes="section-title")
        yield self._title

    def update_data(self, info: ResourceMetricsInfo) -> None:
        self._metrics = info.metrics
        if not self._has_composed:
            return
        for row in self._rows:
            row.remove()
        self._rows.clear()
        if not info.metrics:
            empty = Static("  No metrics available", classes="card-row")
            self._rows.append(empty)
            self.mount(empty)
        else:
            for m in info.metrics:
                trend_cls = _trend_class(m.trend)
                row = Static(
                    f"  {m.name}: {m.value} {m.unit} "
                    f'<span class="{trend_cls}">{m.trend}</span>',
                    classes="card-row",
                )
                self._rows.append(row)
                self.mount(row)

    @property
    def _has_composed(self) -> bool:
        return hasattr(self, "_title") and self._title is not None

    def render(self) -> str:
        return ""


class ActiveAlertsWidget(Widget):
    """Displays active alerts as a dynamic list."""

    DEFAULT_CSS = """
    ActiveAlertsWidget {
        height: auto;
        min-height: 4;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    ActiveAlertsWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    ActiveAlertsWidget .card-row {
        height: 1;
    }
    ActiveAlertsWidget .alert-critical {
        color: $error;
    }
    ActiveAlertsWidget .alert-warning {
        color: $warning;
    }
    ActiveAlertsWidget .alert-error {
        color: $error;
    }
    ActiveAlertsWidget .alert-info {
        color: $text;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._alerts: tuple[AlertEntry, ...] = ()
        self._rows: list[Static] = []

    def compose(self):  # type: ignore[override]
        self._title = Static("Active Alerts", classes="section-title")
        yield self._title

    def update_data(self, alerts: tuple[AlertEntry, ...]) -> None:
        self._alerts = alerts
        if not self._has_composed:
            return
        for row in self._rows:
            row.remove()
        self._rows.clear()
        if not alerts:
            empty = Static("  No active alerts", classes="card-row")
            self._rows.append(empty)
            self.mount(empty)
        else:
            for alert in alerts:
                level_cls = _alert_level_class(alert.level)
                row = Static(
                    f'  <span class="{level_cls}">[{alert.level.upper()}]</span> '
                    f"{alert.title} — {alert.source} ({alert.timestamp_str})",
                    classes="card-row",
                )
                self._rows.append(row)
                self.mount(row)

    @property
    def _has_composed(self) -> bool:
        return hasattr(self, "_title") and self._title is not None

    def render(self) -> str:
        return ""


class AlertHistoryWidget(Widget):
    """Displays alert history as a dynamic list."""

    DEFAULT_CSS = """
    AlertHistoryWidget {
        height: auto;
        min-height: 4;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    AlertHistoryWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    AlertHistoryWidget .card-row {
        height: 1;
    }
    AlertHistoryWidget .history-resolved {
        color: $success;
    }
    AlertHistoryWidget .history-acknowledged {
        color: $warning;
    }
    AlertHistoryWidget .history-new {
        color: $error;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._entries: tuple[AlertHistoryEntry, ...] = ()
        self._rows: list[Static] = []

    def compose(self):  # type: ignore[override]
        self._title = Static("Alert History", classes="section-title")
        yield self._title

    def update_data(self, entries: tuple[AlertHistoryEntry, ...]) -> None:
        self._entries = entries
        if not self._has_composed:
            return
        for row in self._rows:
            row.remove()
        self._rows.clear()
        if not entries:
            empty = Static("  No alert history", classes="card-row")
            self._rows.append(empty)
            self.mount(empty)
        else:
            for entry in entries:
                status_cls = _history_status_class(entry.status)
                row = Static(
                    f'  <span class="{status_cls}">[{entry.status.upper()}]</span> '
                    f"{entry.title} — {entry.level} | {entry.duration}",
                    classes="card-row",
                )
                self._rows.append(row)
                self.mount(row)

    @property
    def _has_composed(self) -> bool:
        return hasattr(self, "_title") and self._title is not None

    def render(self) -> str:
        return ""


class MonitoringEventsWidget(Widget):
    """Displays monitoring events as a dynamic list."""

    DEFAULT_CSS = """
    MonitoringEventsWidget {
        height: auto;
        min-height: 4;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    MonitoringEventsWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    MonitoringEventsWidget .card-row {
        height: 1;
    }
    MonitoringEventsWidget .event-error {
        color: $error;
    }
    MonitoringEventsWidget .event-warning {
        color: $warning;
    }
    MonitoringEventsWidget .event-info {
        color: $text;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._events: tuple[MonitoringEventEntry, ...] = ()
        self._rows: list[Static] = []

    def compose(self):  # type: ignore[override]
        self._title = Static("Monitoring Events", classes="section-title")
        yield self._title

    def update_data(self, events: tuple[MonitoringEventEntry, ...]) -> None:
        self._events = events
        if not self._has_composed:
            return
        for row in self._rows:
            row.remove()
        self._rows.clear()
        if not events:
            empty = Static("  No monitoring events", classes="card-row")
            self._rows.append(empty)
            self.mount(empty)
        else:
            for event in events:
                level_cls = _event_level_class(event.level)
                row = Static(
                    f'  <span class="{level_cls}">[{event.level.upper()}]</span> '
                    f"{event.source}: {event.message} ({event.timestamp_str})",
                    classes="card-row",
                )
                self._rows.append(row)
                self.mount(row)

    @property
    def _has_composed(self) -> bool:
        return hasattr(self, "_title") and self._title is not None

    def render(self) -> str:
        return ""


def _health_class(status: str) -> str:
    """Map a health status string to a CSS class."""
    lower = status.lower()
    if lower in ("healthy", "ok"):
        return "value-healthy"
    if lower in ("degraded", "warning"):
        return "value-warning"
    if lower in ("unhealthy", "error", "critical"):
        return "value-critical"
    if lower in ("offline",):
        return "value-offline"
    return "value-offline"


def _recovery_class(status: str) -> str:
    """Map a recovery status string to a CSS class."""
    lower = status.lower()
    if lower in ("idle", "success", "recovered"):
        return "value-success"
    if lower in ("failed", "error"):
        return "value-failed"
    return "value-idle"


def _alert_level_class(level: str) -> str:
    """Map an alert level string to a CSS class."""
    lower = level.lower()
    if lower in ("critical", "emergency"):
        return "alert-critical"
    if lower in ("error",):
        return "alert-error"
    if lower in ("warning",):
        return "alert-warning"
    return "alert-info"


def _event_level_class(level: str) -> str:
    """Map an event level string to a CSS class."""
    lower = level.lower()
    if lower in ("error", "critical"):
        return "event-error"
    if lower in ("warning",):
        return "event-warning"
    return "event-info"


def _trend_class(trend: str) -> str:
    """Map a trend string to a CSS class."""
    lower = trend.lower()
    if lower in ("up", "increasing", "rising"):
        return "event-warning"
    if lower in ("down", "decreasing", "falling"):
        return "event-info"
    return "event-info"


def _history_status_class(status: str) -> str:
    """Map an alert history status to a CSS class."""
    lower = status.lower()
    if lower in ("resolved",):
        return "history-resolved"
    if lower in ("acknowledged",):
        return "history-acknowledged"
    return "history-new"
