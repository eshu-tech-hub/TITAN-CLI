"""Reusable widgets for the Runtime screen."""

from __future__ import annotations

from typing import Any

from textual.widget import Widget
from textual.widgets import Static

from titan.tui.models import (
    RuntimeComponentInfo,
    RuntimeEngineInfo,
    RuntimeEventBusInfo,
    RuntimeEventEntry,
    RuntimePipelineInfo,
    RuntimeStreamInfo,
)
from titan.tui.widgets import markup_color


class RuntimeStatusWidget(Widget):
    """Displays engine status, uptime, and scheduler state."""

    DEFAULT_CSS = """
    RuntimeStatusWidget {
        height: auto;
        min-height: 5;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    RuntimeStatusWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    RuntimeStatusWidget .card-row {
        height: 1;
    }
    RuntimeStatusWidget .value-running {
        color: $success;
    }
    RuntimeStatusWidget .value-stopped {
        color: $error;
    }
    RuntimeStatusWidget .value-paused {
        color: $warning;
    }
    RuntimeStatusWidget .value-active {
        color: $success;
    }
    RuntimeStatusWidget .value-inactive {
        color: $text-muted;
    }
    RuntimeStatusWidget .value-default {
        color: $text;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = RuntimeEngineInfo()

    def compose(self):  # type: ignore[override]
        self._title = Static("Engine", classes="section-title")
        self._status = Static("", classes="card-row")
        self._uptime = Static("", classes="card-row")
        self._scheduler = Static("", classes="card-row")
        yield self._title
        yield self._status
        yield self._uptime
        yield self._scheduler

    def update_data(self, info: RuntimeEngineInfo) -> None:
        self._info = info
        if not hasattr(self, "_status"):
            return
        status_cls = _status_class(info.status)
        self._status.update(
            f"[bold]Status:[/bold] [{markup_color(status_cls)}]{info.status}[/]"
        )
        self._uptime.update(f"[bold]Uptime:[/bold] {info.uptime}")
        sched_cls = "value-active" if info.scheduler_active else "value-inactive"
        sched_text = "Active" if info.scheduler_active else "Inactive"
        self._scheduler.update(
            f"[bold]Scheduler:[/bold] [{markup_color(sched_cls)}]{sched_text}[/]"
        )

    def render(self) -> str:
        return ""


class StreamWidget(Widget):
    """Displays market stream connectivity and subscription count."""

    DEFAULT_CSS = """
    StreamWidget {
        height: auto;
        min-height: 5;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    StreamWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    StreamWidget .card-row {
        height: 1;
    }
    StreamWidget .value-connected {
        color: $success;
    }
    StreamWidget .value-disconnected {
        color: $error;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = RuntimeStreamInfo()

    def compose(self):  # type: ignore[override]
        self._title = Static("Market Stream", classes="section-title")
        self._connected = Static("", classes="card-row")
        self._symbols = Static("", classes="card-row")
        self._tick_rate = Static("", classes="card-row")
        yield self._title
        yield self._connected
        yield self._symbols
        yield self._tick_rate

    def update_data(self, info: RuntimeStreamInfo) -> None:
        self._info = info
        if not hasattr(self, "_connected"):
            return
        conn_cls = "value-connected" if info.connected else "value-disconnected"
        conn_text = "Yes" if info.connected else "No"
        self._connected.update(
            f"[bold]Connected:[/bold] [{markup_color(conn_cls)}]{conn_text}[/]"
        )
        self._symbols.update(f"[bold]Symbols:[/bold] {info.symbols_tracked}")
        self._tick_rate.update(f"[bold]Tick Rate:[/bold] {info.tick_rate}")

    def render(self) -> str:
        return ""


class PipelineWidget(Widget):
    """Displays pipeline execution count, average runtime, and last run time."""

    DEFAULT_CSS = """
    PipelineWidget {
        height: auto;
        min-height: 5;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    PipelineWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    PipelineWidget .card-row {
        height: 1;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = RuntimePipelineInfo()

    def compose(self):  # type: ignore[override]
        self._title = Static("Pipeline", classes="section-title")
        self._executions = Static("", classes="card-row")
        self._avg_runtime = Static("", classes="card-row")
        self._last_run = Static("", classes="card-row")
        yield self._title
        yield self._executions
        yield self._avg_runtime
        yield self._last_run

    def update_data(self, info: RuntimePipelineInfo) -> None:
        self._info = info
        if not hasattr(self, "_executions"):
            return
        self._executions.update(f"[bold]Executions:[/bold] {info.executions}")
        self._avg_runtime.update(f"[bold]Avg Runtime:[/bold] {info.avg_runtime}")
        self._last_run.update(f"[bold]Last Run:[/bold] {info.last_run}")

    def render(self) -> str:
        return ""


class EventBusWidget(Widget):
    """Displays event bus published and subscriber counts."""

    DEFAULT_CSS = """
    EventBusWidget {
        height: auto;
        min-height: 4;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    EventBusWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    EventBusWidget .card-row {
        height: 1;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = RuntimeEventBusInfo()

    def compose(self):  # type: ignore[override]
        self._title = Static("Event Bus", classes="section-title")
        self._published = Static("", classes="card-row")
        self._subscribers = Static("", classes="card-row")
        yield self._title
        yield self._published
        yield self._subscribers

    def update_data(self, info: RuntimeEventBusInfo) -> None:
        self._info = info
        if not hasattr(self, "_published"):
            return
        self._published.update(f"[bold]Published:[/bold] {info.published}")
        self._subscribers.update(f"[bold]Subscribers:[/bold] {info.subscribers}")

    def render(self) -> str:
        return ""


class HealthWidget(Widget):
    """Displays component health status grid."""

    DEFAULT_CSS = """
    HealthWidget {
        height: auto;
        min-height: 4;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    HealthWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    HealthWidget .card-row {
        height: 1;
    }
    HealthWidget .value-healthy {
        color: $success;
    }
    HealthWidget .value-degraded {
        color: $warning;
    }
    HealthWidget .value-unhealthy {
        color: $error;
    }
    HealthWidget .value-unknown {
        color: $text-muted;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._components: tuple[RuntimeComponentInfo, ...] = ()
        self._rows: list[Static] = []

    def compose(self):  # type: ignore[override]
        self._title = Static("Component Health", classes="section-title")
        yield self._title

    def update_data(self, components: tuple[RuntimeComponentInfo, ...]) -> None:
        self._components = components
        if not self._has_composed:
            return
        for row in self._rows:
            row.remove()
        self._rows.clear()
        if not components:
            empty = Static("  No components reported", classes="card-row")
            self._rows.append(empty)
            self._add_child(empty)
        else:
            for comp in components:
                cls = _health_class(comp.status)
                row = Static(
                    f"  {comp.name}: [{markup_color(cls)}]{comp.status}[/]",
                    classes="card-row",
                )
                self._rows.append(row)
                self._add_child(row)

    @property
    def _has_composed(self) -> bool:
        return hasattr(self, "_title") and self._title is not None

    def _add_child(self, widget: Widget) -> None:
        self.mount(widget)

    def render(self) -> str:
        return ""


class RuntimeEventsWidget(Widget):
    """Displays recent runtime event history."""

    DEFAULT_CSS = """
    RuntimeEventsWidget {
        height: auto;
        min-height: 4;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    RuntimeEventsWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    RuntimeEventsWidget .card-row {
        height: 1;
    }
    RuntimeEventsWidget .event-warning {
        color: $warning;
    }
    RuntimeEventsWidget .event-error {
        color: $error;
    }
    RuntimeEventsWidget .event-info {
        color: $text-muted;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._events: tuple[RuntimeEventEntry, ...] = ()
        self._rows: list[Static] = []

    def compose(self):  # type: ignore[override]
        self._title = Static("Recent Runtime Events", classes="section-title")
        yield self._title

    def update_data(self, events: tuple[RuntimeEventEntry, ...]) -> None:
        self._events = events
        if not self._has_composed:
            return
        for row in self._rows:
            row.remove()
        self._rows.clear()
        if not events:
            empty = Static("  No recent events", classes="card-row")
            self._rows.append(empty)
            self._add_child(empty)
        else:
            for ev in events:
                level_cls = _event_level_class(ev.level)
                prefix = f"[{ev.level.upper()}]" if ev.level else ""
                src = f" {ev.source} |" if ev.source else ""
                row = Static(
                    f"  [{markup_color(level_cls)}]{prefix}[/]{src} {ev.message}",
                    classes="card-row",
                )
                self._rows.append(row)
                self._add_child(row)

    @property
    def _has_composed(self) -> bool:
        return hasattr(self, "_title") and self._title is not None

    def _add_child(self, widget: Widget) -> None:
        self.mount(widget)

    def render(self) -> str:
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


def _health_class(status: str) -> str:
    lower = status.lower()
    if lower in ("healthy", "ok"):
        return "value-healthy"
    if lower in ("degraded", "warning"):
        return "value-degraded"
    if lower in ("unhealthy", "error", "critical"):
        return "value-unhealthy"
    return "value-unknown"


def _event_level_class(level: str) -> str:
    lower = level.lower()
    if lower in ("error", "critical"):
        return "event-error"
    if lower in ("warning", "warn"):
        return "event-warning"
    return "event-info"
