"""Audit, Logs & Recovery screen — read-only visualization of operational state."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, ClassVar

from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Static

from titan.tui.models import AuditScreenState
from titan.tui.widgets.audit import (
    AuditSummaryWidget,
    BackupStatusWidget,
    CheckpointWidget,
    CircuitBreakerWidget,
    LogSummaryWidget,
    RecentAuditWidget,
    RecentLogsWidget,
    RecoveryHistoryWidget,
)

if TYPE_CHECKING:
    from collections.abc import Callable

REFRESH_INTERVAL = 1.0


class AuditScreen(Screen):
    """Audit, Logs & Recovery screen with eight operational widgets.

    Refreshes automatically every REFRESH_INTERVAL seconds.
    Data is read-only from all managers.
    """

    DEFAULT_CSS: ClassVar[str] = """
    AuditScreen {
        layout: vertical;
        padding: 1 2;
    }
    #audit-title {
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
    #audit-row-1 {
        height: auto;
    }
    #audit-row-1 > * {
        width: 1fr;
    }
    """

    BINDINGS: ClassVar[list] = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("escape", "back", "Back"),
        ("up", "scroll_up_line", "Scroll Up"),
        ("down", "scroll_down_line", "Scroll Down"),
        ("page_up", "scroll_up", "Scroll Up"),
        ("page_down", "scroll_down", "Scroll Down"),
        ("home", "scroll_top", "Scroll Top"),
        ("end", "scroll_bottom", "Scroll Bottom"),
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._state = AuditScreenState()
        self._state_builder: Callable[[], AuditScreenState] | None = None
        self._audit_summary_widget: AuditSummaryWidget | None = None
        self._log_summary_widget: LogSummaryWidget | None = None
        self._backup_status_widget: BackupStatusWidget | None = None
        self._circuit_breaker_widget: CircuitBreakerWidget | None = None
        self._recent_audit_widget: RecentAuditWidget | None = None
        self._recent_logs_widget: RecentLogsWidget | None = None
        self._recovery_history_widget: RecoveryHistoryWidget | None = None
        self._checkpoint_widget: CheckpointWidget | None = None

    def compose(self):  # type: ignore[override]
        yield Static("Audit, Logs & Recovery", id="audit-title")
        yield Static("", id="refresh-indicator")
        with VerticalScroll(id="widgets-container"):
            with Horizontal(id="audit-row-1"):
                self._audit_summary_widget = AuditSummaryWidget(id="audit-summary")
                self._log_summary_widget = LogSummaryWidget(id="log-summary")
                self._backup_status_widget = BackupStatusWidget(id="backup-status")
                yield self._audit_summary_widget
                yield self._log_summary_widget
                yield self._backup_status_widget
            self._circuit_breaker_widget = CircuitBreakerWidget(id="circuit-breakers")
            yield self._circuit_breaker_widget
            self._recent_audit_widget = RecentAuditWidget(id="recent-audit")
            yield self._recent_audit_widget
            self._recent_logs_widget = RecentLogsWidget(id="recent-logs")
            yield self._recent_logs_widget
            self._recovery_history_widget = RecoveryHistoryWidget(id="recovery-history")
            yield self._recovery_history_widget
            self._checkpoint_widget = CheckpointWidget(id="checkpoints")
            yield self._checkpoint_widget

    def on_mount(self) -> None:
        self.set_interval(REFRESH_INTERVAL, self._tick_refresh)

    def set_state_builder(self, builder: Callable[[], AuditScreenState]) -> None:
        self._state_builder = builder

    def _tick_refresh(self) -> None:
        self._refresh_state()

    def _refresh_state(self) -> None:
        if self._state_builder is not None:
            try:
                self._state = self._state_builder()
            except Exception:
                self._state = AuditScreenState()
        self._update_widgets()
        self._update_refresh_indicator()

    def _update_widgets(self) -> None:
        if self._audit_summary_widget is not None:
            self._audit_summary_widget.update_data(self._state.audit_summary)
        if self._log_summary_widget is not None:
            self._log_summary_widget.update_data(self._state.log_summary)
        if self._backup_status_widget is not None:
            self._backup_status_widget.update_data(self._state.backup_status)
        if self._circuit_breaker_widget is not None:
            self._circuit_breaker_widget.update_data(self._state.circuit_breakers)
        if self._recent_audit_widget is not None:
            self._recent_audit_widget.update_data(self._state.recent_audit)
        if self._recent_logs_widget is not None:
            self._recent_logs_widget.update_data(self._state.recent_logs)
        if self._recovery_history_widget is not None:
            self._recovery_history_widget.update_data(self._state.recovery_history)
        if self._checkpoint_widget is not None:
            self._checkpoint_widget.update_data(self._state.checkpoints)

    def _update_refresh_indicator(self) -> None:
        try:
            indicator = self.query_one("#refresh-indicator", Static)
            now = datetime.now(UTC).strftime("%H:%M:%S")
            indicator.update(f"Last refresh: {now}")
        except Exception:
            pass

    def action_refresh(self) -> None:
        self._refresh_state()

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_scroll_up_line(self) -> None:
        try:
            container = self.query_one("#widgets-container", VerticalScroll)
            container.scroll_up(animate=False)
        except Exception:
            pass

    def action_scroll_down_line(self) -> None:
        try:
            container = self.query_one("#widgets-container", VerticalScroll)
            container.scroll_down(animate=False)
        except Exception:
            pass

    def action_scroll_up(self) -> None:
        try:
            container = self.query_one("#widgets-container", VerticalScroll)
            container.scroll_home(animate=False)
        except Exception:
            pass

    def action_scroll_down(self) -> None:
        try:
            container = self.query_one("#widgets-container", VerticalScroll)
            container.scroll_end(animate=False)
        except Exception:
            pass

    def action_scroll_top(self) -> None:
        try:
            container = self.query_one("#widgets-container", VerticalScroll)
            container.scroll_home(animate=False)
        except Exception:
            pass

    def action_scroll_bottom(self) -> None:
        try:
            container = self.query_one("#widgets-container", VerticalScroll)
            container.scroll_end(animate=False)
        except Exception:
            pass

    @property
    def state(self) -> AuditScreenState:
        return self._state
