"""Reusable widgets for the Configuration & Deployment screen."""

from __future__ import annotations

from typing import Any

from textual.widget import Widget
from textual.widgets import Static

from titan.tui.models import (
    BackupInfo,
    ConfigurationInfo,
    DeploymentHistoryEntry,
    DeploymentInfo,
    EnvironmentInfo,
    ServiceStatusEntry,
    VersionInfo,
)
from titan.tui.widgets import markup_color


class ConfigurationWidget(Widget):
    """Displays current configuration state."""

    DEFAULT_CSS = """
    ConfigurationWidget {
        height: auto;
        min-height: 7;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    ConfigurationWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    ConfigurationWidget .card-row {
        height: 1;
    }
    ConfigurationWidget .value-valid { color: $success; }
    ConfigurationWidget .value-invalid { color: $error; }
    ConfigurationWidget .value-warnings { color: $warning; }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = ConfigurationInfo()

    def compose(self):  # type: ignore[override]
        self._title = Static("Configuration", classes="section-title")
        self._profile = Static("", classes="card-row")
        self._status = Static("", classes="card-row")
        self._log_level = Static("", classes="card-row")
        self._pipeline = Static("", classes="card-row")
        yield self._title
        yield self._profile
        yield self._status
        yield self._log_level
        yield self._pipeline

    def update_data(self, info: ConfigurationInfo) -> None:
        self._info = info
        if not hasattr(self, "_profile"):
            return
        self._profile.update(f"[bold]Profile:[/bold] {info.profile}")
        status_cls = _validation_class(info.validation_status)
        self._status.update(
            f'[bold]Status:[/bold] [{markup_color(status_cls)}]{info.validation_status.upper() or "UNKNOWN"}[/]'
        )
        self._log_level.update(f"[bold]Log Level:[/bold] {info.log_level}")
        self._pipeline.update(
            f"[bold]Pipeline Interval:[/bold] {info.pipeline_interval}"
        )

    def render(self) -> str:
        return ""


class ValidationDetailsWidget(Widget):
    """Displays detailed validation errors, warnings, and recommendations."""

    DEFAULT_CSS = """
    ValidationDetailsWidget {
        height: auto;
        min-height: 5;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    ValidationDetailsWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    ValidationDetailsWidget .error-text { color: $error; }
    ValidationDetailsWidget .warning-text { color: $warning; }
    ValidationDetailsWidget .info-text { color: $accent; }
    ValidationDetailsWidget .empty-text { color: $success; }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = ConfigurationInfo()

    def compose(self):  # type: ignore[override]
        self._title = Static("Validation Details", classes="section-title")
        self._details = Static("No configuration data loaded.", classes="empty-text")
        yield self._title
        yield self._details

    def update_data(self, info: ConfigurationInfo) -> None:
        self._info = info
        if not hasattr(self, "_details"):
            return

        lines = []
        if info.blocking_errors:
            lines.append("[bold red]Blocking Errors:[/bold red]")
            for err in info.blocking_errors:
                lines.append(f"  [red]![/red] {err}")

        if info.warnings:
            if lines:
                lines.append("")
            lines.append("[bold yellow]Warnings:[/bold yellow]")
            for w in info.warnings:
                lines.append(f"  [yellow]~[/yellow] {w}")

        if info.recommendations:
            if lines:
                lines.append("")
            lines.append("[bold cyan]Recommendations:[/bold cyan]")
            for r in info.recommendations:
                lines.append(f"  [cyan]i[/cyan] {r}")

        if not lines:
            self._details.update(
                "[bold green]Configuration is fully valid and production-ready. No issues found.[/bold green]"
            )
        else:
            self._details.update("\n".join(lines))


class EnvironmentWidget(Widget):
    """Displays active deployment environment."""

    DEFAULT_CSS = """
    EnvironmentWidget {
        height: auto;
        min-height: 7;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    EnvironmentWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    EnvironmentWidget .card-row {
        height: 1;
    }
    EnvironmentWidget .value-valid { color: $success; }
    EnvironmentWidget .value-invalid { color: $error; }
    EnvironmentWidget .value-warnings { color: $warning; }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = EnvironmentInfo()

    def compose(self):  # type: ignore[override]
        self._title = Static("Environment", classes="section-title")
        self._env_name = Static("", classes="card-row")
        self._validation = Static("", classes="card-row")
        self._dirs = Static("", classes="card-row")
        self._secrets = Static("", classes="card-row")
        yield self._title
        yield self._env_name
        yield self._validation
        yield self._dirs
        yield self._secrets

    def update_data(self, info: EnvironmentInfo) -> None:
        self._info = info
        if not hasattr(self, "_env_name"):
            return
        self._env_name.update(f"[bold]Name:[/bold] {info.name}")
        val_cls = _validation_class(info.validation_status)
        self._validation.update(
            f'[bold]Validation:[/bold] [{markup_color(val_cls)}]{info.validation_status.upper() or "UNKNOWN"}[/]'
        )
        dirs_str = "Verified" if info.directories_verified else "Pending"
        self._dirs.update(f"[bold]Directories:[/bold] {dirs_str}")
        sec_str = "Available" if info.secrets_available else "Missing"
        self._secrets.update(f"[bold]Secrets:[/bold] {sec_str}")

    def render(self) -> str:
        return ""


class DeploymentWidget(Widget):
    """Displays overall runtime deployment status."""

    DEFAULT_CSS = """
    DeploymentWidget {
        height: auto;
        min-height: 7;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    DeploymentWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    DeploymentWidget .card-row {
        height: 1;
    }
    DeploymentWidget .value-running { color: $success; }
    DeploymentWidget .value-stopped { color: $text-muted; }
    DeploymentWidget .value-error { color: $error; }
    DeploymentWidget .value-healthy { color: $success; }
    DeploymentWidget .value-unhealthy { color: $error; }
    DeploymentWidget .value-degraded { color: $warning; }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = DeploymentInfo()

    def compose(self):  # type: ignore[override]
        self._title = Static("Deployment Status", classes="section-title")
        self._status = Static("", classes="card-row")
        self._health = Static("", classes="card-row")
        self._uptime = Static("", classes="card-row")
        self._started = Static("", classes="card-row")
        yield self._title
        yield self._status
        yield self._health
        yield self._uptime
        yield self._started

    def update_data(self, info: DeploymentInfo) -> None:
        self._info = info
        if not hasattr(self, "_status"):
            return
        status_cls = _deployment_status_class(info.status)
        self._status.update(
            f'[bold]Status:[/bold] [{markup_color(status_cls)}]{info.status.upper() or "UNKNOWN"}[/]'
        )
        health_cls = _health_class(info.health_status)
        self._health.update(
            f'[bold]Health:[/bold] [{markup_color(health_cls)}]{info.health_status.upper() or "UNKNOWN"}[/]'
        )
        self._uptime.update(f"[bold]Uptime:[/bold] {info.uptime}")
        self._started.update(f"[bold]Started:[/bold] {info.start_time}")

    def render(self) -> str:
        return ""


class VersionWidget(Widget):
    """Displays version and build information."""

    DEFAULT_CSS = """
    VersionWidget {
        height: auto;
        min-height: 7;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    VersionWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    VersionWidget .card-row {
        height: 1;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = VersionInfo()

    def compose(self):  # type: ignore[override]
        self._title = Static("Version Info", classes="section-title")
        self._version = Static("", classes="card-row")
        self._build = Static("", classes="card-row")
        self._commit = Static("", classes="card-row")
        self._python = Static("", classes="card-row")
        yield self._title
        yield self._version
        yield self._build
        yield self._commit
        yield self._python

    def update_data(self, info: VersionInfo) -> None:
        self._info = info
        if not hasattr(self, "_version"):
            return
        self._version.update(f"[bold]Version:[/bold] {info.version}")
        self._build.update(f"[bold]Build:[/bold] {info.build_number}")
        self._commit.update(
            f"[bold]Commit:[/bold] {info.git_commit[:8]} ({info.git_branch})"
        )
        self._python.update(f"[bold]Python:[/bold] {info.python_version}")

    def render(self) -> str:
        return ""


class BackupWidget(Widget):
    """Displays backup status information."""

    DEFAULT_CSS = """
    BackupWidget {
        height: auto;
        min-height: 6;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    BackupWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    BackupWidget .card-row {
        height: 1;
    }
    BackupWidget .value-success { color: $success; }
    BackupWidget .value-failed { color: $error; }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = BackupInfo()

    def compose(self):  # type: ignore[override]
        self._title = Static("Backup Status", classes="section-title")
        self._last_run = Static("", classes="card-row")
        self._components = Static("", classes="card-row")
        self._status = Static("", classes="card-row")
        yield self._title
        yield self._last_run
        yield self._components
        yield self._status

    def update_data(self, info: BackupInfo) -> None:
        self._info = info
        if not hasattr(self, "_last_run"):
            return
        self._last_run.update(
            f"[bold]Last Backup:[/bold] {info.last_backup_time or 'Never'}"
        )
        self._components.update(
            f"[bold]Components:[/bold] {info.components_backed_up} ({info.total_files} files)"
        )
        status_cls = (
            "value-success" if str(info.status).lower() == "success" else "value-failed"
        )
        self._status.update(
            f'[bold]Status:[/bold] [{markup_color(status_cls)}]{info.status.upper() if info.status else "N/A"}[/]'
        )

    def render(self) -> str:
        return ""


class ServicesWidget(Widget):
    """Displays dynamic list of service statuses."""

    DEFAULT_CSS = """
    ServicesWidget {
        height: auto;
        min-height: 4;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    ServicesWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    ServicesWidget .card-row {
        height: 1;
    }
    ServicesWidget .value-healthy { color: $success; }
    ServicesWidget .value-degraded { color: $warning; }
    ServicesWidget .value-unhealthy { color: $error; }
    ServicesWidget .value-offline { color: $text-muted; }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._entries: tuple[ServiceStatusEntry, ...] = ()
        self._rows: list[Static] = []

    def compose(self):  # type: ignore[override]
        self._title = Static("Subsystem Services", classes="section-title")
        yield self._title

    def update_data(self, entries: tuple[ServiceStatusEntry, ...]) -> None:
        self._entries = entries
        if not self._has_composed:
            return
        for row in self._rows:
            row.remove()
        self._rows.clear()
        if not entries:
            empty = Static("  No services registered", classes="card-row")
            self._rows.append(empty)
            self.mount(empty)
        else:
            for entry in entries:
                h_cls = _health_class(entry.status)
                msg = f" - {entry.message}" if entry.message else ""
                row = Static(
                    f"  [bold]{entry.name.ljust(15)}[/bold] : "
                    f"[{markup_color(h_cls)}]{entry.status.upper()}[/] "
                    f"({entry.latency_ms}ms){msg}",
                    classes="card-row",
                )
                self._rows.append(row)
                self.mount(row)

    @property
    def _has_composed(self) -> bool:
        return hasattr(self, "_title") and self._title is not None

    def render(self) -> str:
        return ""


class DeploymentHistoryWidget(Widget):
    """Displays dynamic list of deployment history events."""

    DEFAULT_CSS = """
    DeploymentHistoryWidget {
        height: auto;
        min-height: 4;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    DeploymentHistoryWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    DeploymentHistoryWidget .card-row {
        height: 1;
    }
    DeploymentHistoryWidget .value-success { color: $success; }
    DeploymentHistoryWidget .value-failed { color: $error; }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._entries: tuple[DeploymentHistoryEntry, ...] = ()
        self._rows: list[Static] = []

    def compose(self):  # type: ignore[override]
        self._title = Static("Deployment History", classes="section-title")
        yield self._title

    def update_data(self, entries: tuple[DeploymentHistoryEntry, ...]) -> None:
        self._entries = entries
        if not self._has_composed:
            return
        for row in self._rows:
            row.remove()
        self._rows.clear()
        if not entries:
            empty = Static("  No deployment history", classes="card-row")
            self._rows.append(empty)
            self.mount(empty)
        else:
            for entry in entries:
                s_cls = (
                    "value-success"
                    if str(entry.status).lower() == "success"
                    else "value-failed"
                )
                row = Static(
                    f"  {entry.timestamp_str} | [bold]{entry.action.upper()}[/bold] | "
                    f"[{markup_color(s_cls)}]{entry.status.upper()}[/] | "
                    f"v{entry.version} ({entry.duration})",
                    classes="card-row",
                )
                self._rows.append(row)
                self.mount(row)

    @property
    def _has_composed(self) -> bool:
        return hasattr(self, "_title") and self._title is not None

    def render(self) -> str:
        return ""


# ─── Private CSS Helpers ──────────────────────────────────────────


def _validation_class(status: str) -> str:
    lower = status.lower()
    if lower == "valid":
        return "value-valid"
    if lower == "invalid":
        return "value-invalid"
    if lower == "warnings":
        return "value-warnings"
    return "default-class"


def _deployment_status_class(status: str) -> str:
    lower = status.lower()
    if lower == "running":
        return "value-running"
    if lower in ("error", "failed"):
        return "value-error"
    if lower == "stopped":
        return "value-stopped"
    return "default-class"


def _health_class(status: str) -> str:
    lower = status.lower()
    if lower == "healthy":
        return "value-healthy"
    if lower == "degraded":
        return "value-degraded"
    if lower == "unhealthy":
        return "value-unhealthy"
    if lower == "offline":
        return "value-offline"
    return "default-class"
