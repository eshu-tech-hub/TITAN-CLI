"""Reusable widgets for the Audit, Logs & Recovery screen."""

from __future__ import annotations

from typing import Any

from textual.widget import Widget
from textual.widgets import Static

from titan.tui.models import (
    AuditEntry,
    AuditSummaryInfo,
    BackupStatusInfo,
    CheckpointInfo,
    CircuitBreakerInfo,
    LogEntry,
    LogSummaryInfo,
    RecoveryHistoryEntry,
)


class AuditSummaryWidget(Widget):
    """Displays audit trail summary."""

    DEFAULT_CSS = """
    AuditSummaryWidget {
        height: auto;
        min-height: 7;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    AuditSummaryWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    AuditSummaryWidget .card-row {
        height: 1;
    }
    AuditSummaryWidget .value-valid {
        color: $success;
    }
    AuditSummaryWidget .value-invalid {
        color: $error;
    }
    AuditSummaryWidget .value-unknown {
        color: $text-muted;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = AuditSummaryInfo()

    def compose(self):  # type: ignore[override]
        self._title = Static("Audit Summary", classes="section-title")
        self._total = Static("", classes="card-row")
        self._source = Static("", classes="card-row")
        self._severity = Static("", classes="card-row")
        self._integrity = Static("", classes="card-row")
        self._first_time = Static("", classes="card-row")
        self._last_time = Static("", classes="card-row")
        yield self._title
        yield self._total
        yield self._source
        yield self._severity
        yield self._integrity
        yield self._first_time
        yield self._last_time

    def update_data(self, info: AuditSummaryInfo) -> None:
        self._info = info
        if not hasattr(self, "_total"):
            return
        self._total.update(f"[bold]Total Events:[/bold] {info.total_events}")
        self._source.update(f"[bold]By Source:[/bold] {info.events_by_source or 'N/A'}")
        self._severity.update(
            f"[bold]By Severity:[/bold] {info.events_by_severity or 'N/A'}"
        )
        integrity_cls = _integrity_class(info.integrity_status)
        self._integrity.update(
            f'[bold]Integrity:[/bold] <span class="{integrity_cls}">'
            f"{info.integrity_status}</span>"
            f" ({info.verification_failures} failures)"
        )
        self._first_time.update(
            f"[bold]First Event:[/bold] {info.first_event_time or 'N/A'}"
        )
        self._last_time.update(
            f"[bold]Last Event:[/bold] {info.last_event_time or 'N/A'}"
        )

    def render(self) -> str:
        return ""


class RecentAuditWidget(Widget):
    """Displays recent audit events as a dynamic list."""

    DEFAULT_CSS = """
    RecentAuditWidget {
        height: auto;
        min-height: 4;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    RecentAuditWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    RecentAuditWidget .card-row {
        height: 1;
    }
    RecentAuditWidget .audit-error {
        color: $error;
    }
    RecentAuditWidget .audit-warning {
        color: $warning;
    }
    RecentAuditWidget .audit-info {
        color: $text;
    }
    RecentAuditWidget .audit-success {
        color: $success;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._entries: tuple[AuditEntry, ...] = ()
        self._rows: list[Static] = []

    def compose(self):  # type: ignore[override]
        self._title = Static("Recent Audit Events", classes="section-title")
        yield self._title

    def update_data(self, entries: tuple[AuditEntry, ...]) -> None:
        self._entries = entries
        if not self._has_composed:
            return
        for row in self._rows:
            row.remove()
        self._rows.clear()
        if not entries:
            empty = Static("  No audit events", classes="card-row")
            self._rows.append(empty)
            self.mount(empty)
        else:
            for entry in entries:
                sev_cls = _audit_severity_class(entry.severity)
                res_cls = _audit_result_class(entry.result)
                row = Static(
                    f'  <span class="{sev_cls}">[{entry.severity.upper()}]</span> '
                    f"[{entry.source}] {entry.action} "
                    f'<span class="{res_cls}">{entry.result}</span> '
                    f"({entry.timestamp_str})",
                    classes="card-row",
                )
                self._rows.append(row)
                self.mount(row)

    @property
    def _has_composed(self) -> bool:
        return hasattr(self, "_title") and self._title is not None

    def render(self) -> str:
        return ""


class LogSummaryWidget(Widget):
    """Displays logging framework summary."""

    DEFAULT_CSS = """
    LogSummaryWidget {
        height: auto;
        min-height: 6;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    LogSummaryWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    LogSummaryWidget .card-row {
        height: 1;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = LogSummaryInfo()

    def compose(self):  # type: ignore[override]
        self._title = Static("Log Summary", classes="section-title")
        self._level = Static("", classes="card-row")
        self._handlers = Static("", classes="card-row")
        self._components = Static("", classes="card-row")
        self._dropped = Static("", classes="card-row")
        self._warnings = Static("", classes="card-row")
        yield self._title
        yield self._level
        yield self._handlers
        yield self._components
        yield self._dropped
        yield self._warnings

    def update_data(self, info: LogSummaryInfo) -> None:
        self._info = info
        if not hasattr(self, "_level"):
            return
        self._level.update(f"[bold]Log Level:[/bold] {info.level}")
        self._handlers.update(f"[bold]Handlers:[/bold] {info.handler_count}")
        self._components.update(f"[bold]Components:[/bold] {info.component_count}")
        self._dropped.update(f"[bold]Dropped Messages:[/bold] {info.dropped_messages}")
        self._warnings.update(
            f"[bold]Warnings:[/bold] {info.warning_count} "
            f"([bold]Errors:[/bold] {info.error_count})"
        )

    def render(self) -> str:
        return ""


class RecentLogsWidget(Widget):
    """Displays recent log lines as a dynamic list."""

    DEFAULT_CSS = """
    RecentLogsWidget {
        height: auto;
        min-height: 4;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    RecentLogsWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    RecentLogsWidget .card-row {
        height: 1;
    }
    RecentLogsWidget .log-error {
        color: $error;
    }
    RecentLogsWidget .log-warning {
        color: $warning;
    }
    RecentLogsWidget .log-info {
        color: $text;
    }
    RecentLogsWidget .log-debug {
        color: $text-muted;
    }
    RecentLogsWidget .log-critical {
        color: $error;
        text-style: bold;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._logs: tuple[LogEntry, ...] = ()
        self._rows: list[Static] = []

    def compose(self):  # type: ignore[override]
        self._title = Static("Recent Logs", classes="section-title")
        yield self._title

    def update_data(self, logs: tuple[LogEntry, ...]) -> None:
        self._logs = logs
        if not self._has_composed:
            return
        for row in self._rows:
            row.remove()
        self._rows.clear()
        if not logs:
            empty = Static("  No log entries", classes="card-row")
            self._rows.append(empty)
            self.mount(empty)
        else:
            for log in logs:
                level_cls = _log_level_class(log.level)
                row = Static(
                    f'  <span class="{level_cls}">[{log.level.upper():>8}]</span> '
                    f"{log.timestamp_str} {log.module}/{log.component}: {log.message}",
                    classes="card-row",
                )
                self._rows.append(row)
                self.mount(row)

    @property
    def _has_composed(self) -> bool:
        return hasattr(self, "_title") and self._title is not None

    def render(self) -> str:
        return ""


class RecoveryHistoryWidget(Widget):
    """Displays recovery history as a dynamic list."""

    DEFAULT_CSS = """
    RecoveryHistoryWidget {
        height: auto;
        min-height: 4;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    RecoveryHistoryWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    RecoveryHistoryWidget .card-row {
        height: 1;
    }
    RecoveryHistoryWidget .recovery-success {
        color: $success;
    }
    RecoveryHistoryWidget .recovery-failed {
        color: $error;
    }
    RecoveryHistoryWidget .recovery-pending {
        color: $warning;
    }
    RecoveryHistoryWidget .recovery-idle {
        color: $text-muted;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._entries: tuple[RecoveryHistoryEntry, ...] = ()
        self._rows: list[Static] = []

    def compose(self):  # type: ignore[override]
        self._title = Static("Recovery History", classes="section-title")
        yield self._title

    def update_data(self, entries: tuple[RecoveryHistoryEntry, ...]) -> None:
        self._entries = entries
        if not self._has_composed:
            return
        for row in self._rows:
            row.remove()
        self._rows.clear()
        if not entries:
            empty = Static("  No recovery history", classes="card-row")
            self._rows.append(empty)
            self.mount(empty)
        else:
            for entry in entries:
                status_cls = _recovery_status_class(entry.status)
                row = Static(
                    f'  <span class="{status_cls}">[{entry.status.upper()}]</span> '
                    f"{entry.component} — {entry.strategy} "
                    f"({entry.attempts} attempts) "
                    f"{entry.failure_reason or ''} "
                    f"({entry.timestamp_str})",
                    classes="card-row",
                )
                self._rows.append(row)
                self.mount(row)

    @property
    def _has_composed(self) -> bool:
        return hasattr(self, "_title") and self._title is not None

    def render(self) -> str:
        return ""


class CircuitBreakerWidget(Widget):
    """Displays circuit breaker status as a dynamic list."""

    DEFAULT_CSS = """
    CircuitBreakerWidget {
        height: auto;
        min-height: 4;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    CircuitBreakerWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    CircuitBreakerWidget .card-row {
        height: 1;
    }
    CircuitBreakerWidget .cb-closed {
        color: $success;
    }
    CircuitBreakerWidget .cb-open {
        color: $error;
    }
    CircuitBreakerWidget .cb-half-open {
        color: $warning;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._breakers: tuple[CircuitBreakerInfo, ...] = ()
        self._rows: list[Static] = []

    def compose(self):  # type: ignore[override]
        self._title = Static("Circuit Breakers", classes="section-title")
        yield self._title

    def update_data(self, breakers: tuple[CircuitBreakerInfo, ...]) -> None:
        self._breakers = breakers
        if not self._has_composed:
            return
        for row in self._rows:
            row.remove()
        self._rows.clear()
        if not breakers:
            empty = Static("  No circuit breakers registered", classes="card-row")
            self._rows.append(empty)
            self.mount(empty)
        else:
            for cb in breakers:
                state_cls = _cb_state_class(cb.state)
                row = Static(
                    f'  <span class="{state_cls}">[{cb.state}]</span> '
                    f"{cb.name}: failures={cb.failure_count}/{cb.failure_threshold} "
                    f"successes={cb.success_count} "
                    f"timeout={cb.recovery_timeout}",
                    classes="card-row",
                )
                self._rows.append(row)
                self.mount(row)

    @property
    def _has_composed(self) -> bool:
        return hasattr(self, "_title") and self._title is not None

    def render(self) -> str:
        return ""


class CheckpointWidget(Widget):
    """Displays checkpoint list as a dynamic list."""

    DEFAULT_CSS = """
    CheckpointWidget {
        height: auto;
        min-height: 4;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    CheckpointWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    CheckpointWidget .card-row {
        height: 1;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._checkpoints: tuple[CheckpointInfo, ...] = ()
        self._rows: list[Static] = []

    def compose(self):  # type: ignore[override]
        self._title = Static("Checkpoints", classes="section-title")
        yield self._title

    def update_data(self, checkpoints: tuple[CheckpointInfo, ...]) -> None:
        self._checkpoints = checkpoints
        if not self._has_composed:
            return
        for row in self._rows:
            row.remove()
        self._rows.clear()
        if not checkpoints:
            empty = Static("  No checkpoints saved", classes="card-row")
            self._rows.append(empty)
            self.mount(empty)
        else:
            for cp in checkpoints:
                meta = " [meta]" if cp.has_metadata else ""
                row = Static(
                    f"  {cp.checkpoint_id}: {cp.component} "
                    f"v{cp.version} ({cp.created_at_str}){meta}",
                    classes="card-row",
                )
                self._rows.append(row)
                self.mount(row)

    @property
    def _has_composed(self) -> bool:
        return hasattr(self, "_title") and self._title is not None

    def render(self) -> str:
        return ""


class BackupStatusWidget(Widget):
    """Displays backup/restore status."""

    DEFAULT_CSS = """
    BackupStatusWidget {
        height: auto;
        min-height: 6;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary;
    }
    BackupStatusWidget .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    BackupStatusWidget .card-row {
        height: 1;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._info = BackupStatusInfo()

    def compose(self):  # type: ignore[override]
        self._title = Static("Backup Status", classes="section-title")
        self._total = Static("", classes="card-row")
        self._components = Static("", classes="card-row")
        self._last = Static("", classes="card-row")
        self._storage_type = Static("", classes="card-row")
        self._storage_path = Static("", classes="card-row")
        yield self._title
        yield self._total
        yield self._components
        yield self._last
        yield self._storage_type
        yield self._storage_path

    def update_data(self, info: BackupStatusInfo) -> None:
        self._info = info
        if not hasattr(self, "_total"):
            return
        self._total.update(f"[bold]Total Checkpoints:[/bold] {info.total_checkpoints}")
        self._components.update(
            f"[bold]Components:[/bold] {info.components_with_checkpoints or 'None'}"
        )
        self._last.update(
            f"[bold]Last Checkpoint:[/bold] {info.last_checkpoint_time or 'N/A'}"
        )
        self._storage_type.update(
            f"[bold]Storage Type:[/bold] {info.storage_type or 'N/A'}"
        )
        self._storage_path.update(
            f"[bold]Storage Path:[/bold] {info.storage_path or 'N/A'}"
        )

    def render(self) -> str:
        return ""


# ─── CSS class helpers ───────────────────────────────────────────


def _integrity_class(status: str) -> str:
    lower = status.lower()
    if lower in ("valid", "passed", "ok"):
        return "value-valid"
    if lower in ("invalid", "failed", "violations"):
        return "value-invalid"
    return "value-unknown"


def _audit_severity_class(severity: str) -> str:
    lower = severity.lower()
    if lower in ("critical", "emergency"):
        return "audit-error"
    if lower in ("error",):
        return "audit-error"
    if lower in ("warning",):
        return "audit-warning"
    return "audit-info"


def _audit_result_class(result: str) -> str:
    lower = result.lower()
    if lower in ("success",):
        return "audit-success"
    if lower in ("failure", "failed"):
        return "audit-error"
    return "audit-info"


def _log_level_class(level: str) -> str:
    lower = level.lower()
    if lower in ("critical",):
        return "log-critical"
    if lower in ("error",):
        return "log-error"
    if lower in ("warning",):
        return "log-warning"
    if lower in ("debug", "trace"):
        return "log-debug"
    return "log-info"


def _recovery_status_class(status: str) -> str:
    lower = status.lower()
    if lower in ("success", "recovered"):
        return "recovery-success"
    if lower in ("failed", "error"):
        return "recovery-failed"
    if lower in ("pending", "in_progress"):
        return "recovery-pending"
    return "recovery-idle"


def _cb_state_class(state: str) -> str:
    lower = state.lower()
    if lower in ("closed",):
        return "cb-closed"
    if lower in ("open",):
        return "cb-open"
    if lower in ("half_open", "half-open"):
        return "cb-half-open"
    return "cb-closed"
