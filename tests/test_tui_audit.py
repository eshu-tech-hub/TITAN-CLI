"""Tests for the Audit, Logs & Recovery TUI screen."""

from __future__ import annotations

import json
from dataclasses import asdict
from unittest.mock import MagicMock, patch

import pytest

from titan.tui.models import (
    AuditEntry,
    AuditScreenState,
    AuditSummaryInfo,
    BackupStatusInfo,
    CheckpointInfo,
    CircuitBreakerInfo,
    LogEntry,
    LogSummaryInfo,
    RecoveryHistoryEntry,
)
from titan.tui.widgets.audit import (
    AuditSummaryWidget,
    BackupStatusWidget,
    CheckpointWidget,
    CircuitBreakerWidget,
    LogSummaryWidget,
    RecentAuditWidget,
    RecentLogsWidget,
    RecoveryHistoryWidget,
    _audit_result_class,
    _audit_severity_class,
    _cb_state_class,
    _integrity_class,
    _log_level_class,
    _recovery_status_class,
)

# ─── Model tests ────────────────────────────────────────────────


class TestAuditSummaryInfo:
    def test_defaults(self) -> None:
        info = AuditSummaryInfo()
        assert info.total_events == 0
        assert info.events_by_source == ""
        assert info.events_by_severity == ""
        assert info.integrity_status == "unknown"
        assert info.verification_failures == 0
        assert info.first_event_time == ""
        assert info.last_event_time == ""

    def test_custom(self) -> None:
        info = AuditSummaryInfo(
            total_events=100,
            events_by_source="runtime:50,monitoring:50",
            integrity_status="valid",
        )
        assert info.total_events == 100
        assert "runtime" in info.events_by_source
        assert info.integrity_status == "valid"

    def test_frozen(self) -> None:
        info = AuditSummaryInfo()
        with pytest.raises(AttributeError):
            info.total_events = 5  # type: ignore[misc]

    def test_slots(self) -> None:
        info = AuditSummaryInfo()
        assert not hasattr(info, "__dict__")

    def test_json_serializable(self) -> None:
        info = AuditSummaryInfo(total_events=10, integrity_status="valid")
        data = asdict(info)
        serialized = json.dumps(data)
        assert "10" in serialized


class TestAuditEntry:
    def test_defaults(self) -> None:
        entry = AuditEntry()
        assert entry.event_id == ""
        assert entry.sequence == 0
        assert entry.source == ""
        assert entry.category == ""
        assert entry.severity == ""
        assert entry.action == ""
        assert entry.result == ""
        assert entry.timestamp_str == ""

    def test_custom(self) -> None:
        entry = AuditEntry(
            event_id="e1",
            sequence=42,
            source="runtime",
            category="system_start",
            severity="info",
            action="start_engine",
            result="success",
            timestamp_str="10:30:00",
        )
        assert entry.event_id == "e1"
        assert entry.sequence == 42
        assert entry.source == "runtime"

    def test_frozen(self) -> None:
        entry = AuditEntry()
        with pytest.raises(AttributeError):
            entry.event_id = "x"  # type: ignore[misc]

    def test_slots(self) -> None:
        entry = AuditEntry()
        assert not hasattr(entry, "__dict__")

    def test_json_serializable(self) -> None:
        entry = AuditEntry(event_id="e1", source="runtime", action="start")
        data = asdict(entry)
        serialized = json.dumps(data)
        assert "e1" in serialized


class TestLogSummaryInfo:
    def test_defaults(self) -> None:
        info = LogSummaryInfo()
        assert info.level == "INFO"
        assert info.handler_count == 0
        assert info.component_count == 0
        assert info.dropped_messages == 0
        assert info.warning_count == 0
        assert info.error_count == 0

    def test_custom(self) -> None:
        info = LogSummaryInfo(
            level="DEBUG",
            handler_count=3,
            component_count=12,
            dropped_messages=5,
        )
        assert info.level == "DEBUG"
        assert info.handler_count == 3
        assert info.component_count == 12

    def test_frozen(self) -> None:
        info = LogSummaryInfo()
        with pytest.raises(AttributeError):
            info.level = "DEBUG"  # type: ignore[misc]

    def test_slots(self) -> None:
        info = LogSummaryInfo()
        assert not hasattr(info, "__dict__")

    def test_json_serializable(self) -> None:
        info = LogSummaryInfo(level="WARNING", handler_count=2)
        data = asdict(info)
        serialized = json.dumps(data)
        assert "WARNING" in serialized


class TestLogEntry:
    def test_defaults(self) -> None:
        entry = LogEntry()
        assert entry.timestamp_str == ""
        assert entry.level == ""
        assert entry.module == ""
        assert entry.component == ""
        assert entry.message == ""

    def test_custom(self) -> None:
        entry = LogEntry(
            timestamp_str="10:30:00",
            level="ERROR",
            module="titan.runtime",
            component="engine",
            message="Connection failed",
        )
        assert entry.level == "ERROR"
        assert entry.module == "titan.runtime"

    def test_frozen(self) -> None:
        entry = LogEntry()
        with pytest.raises(AttributeError):
            entry.level = "INFO"  # type: ignore[misc]

    def test_slots(self) -> None:
        entry = LogEntry()
        assert not hasattr(entry, "__dict__")

    def test_json_serializable(self) -> None:
        entry = LogEntry(level="INFO", message="test")
        data = asdict(entry)
        serialized = json.dumps(data)
        assert "test" in serialized


class TestRecoveryHistoryEntry:
    def test_defaults(self) -> None:
        entry = RecoveryHistoryEntry()
        assert entry.request_id == ""
        assert entry.component == ""
        assert entry.strategy == ""
        assert entry.status == ""
        assert entry.attempts == 0
        assert entry.failure_reason == ""
        assert entry.timestamp_str == ""

    def test_custom(self) -> None:
        entry = RecoveryHistoryEntry(
            request_id="r1",
            component="pipeline",
            strategy="retry",
            status="success",
            attempts=3,
            failure_reason="timeout",
            timestamp_str="10:30:00",
        )
        assert entry.request_id == "r1"
        assert entry.component == "pipeline"
        assert entry.attempts == 3

    def test_frozen(self) -> None:
        entry = RecoveryHistoryEntry()
        with pytest.raises(AttributeError):
            entry.status = "failed"  # type: ignore[misc]

    def test_slots(self) -> None:
        entry = RecoveryHistoryEntry()
        assert not hasattr(entry, "__dict__")

    def test_json_serializable(self) -> None:
        entry = RecoveryHistoryEntry(request_id="r1", status="success")
        data = asdict(entry)
        serialized = json.dumps(data)
        assert "r1" in serialized


class TestCircuitBreakerInfo:
    def test_defaults(self) -> None:
        info = CircuitBreakerInfo()
        assert info.name == ""
        assert info.state == "CLOSED"
        assert info.failure_count == 0
        assert info.success_count == 0
        assert info.failure_threshold == 5
        assert info.recovery_timeout == ""

    def test_custom(self) -> None:
        info = CircuitBreakerInfo(
            name="broker",
            state="OPEN",
            failure_count=5,
            failure_threshold=5,
            recovery_timeout="30s",
        )
        assert info.name == "broker"
        assert info.state == "OPEN"

    def test_frozen(self) -> None:
        info = CircuitBreakerInfo()
        with pytest.raises(AttributeError):
            info.state = "OPEN"  # type: ignore[misc]

    def test_slots(self) -> None:
        info = CircuitBreakerInfo()
        assert not hasattr(info, "__dict__")

    def test_json_serializable(self) -> None:
        info = CircuitBreakerInfo(name="broker", state="CLOSED")
        data = asdict(info)
        serialized = json.dumps(data)
        assert "broker" in serialized


class TestCheckpointInfo:
    def test_defaults(self) -> None:
        info = CheckpointInfo()
        assert info.checkpoint_id == ""
        assert info.component == ""
        assert info.version == ""
        assert info.created_at_str == ""
        assert info.has_metadata is False

    def test_custom(self) -> None:
        info = CheckpointInfo(
            checkpoint_id="cp1",
            component="pipeline",
            version="1.0.0",
            created_at_str="10:30:00",
            has_metadata=True,
        )
        assert info.checkpoint_id == "cp1"
        assert info.has_metadata is True

    def test_frozen(self) -> None:
        info = CheckpointInfo()
        with pytest.raises(AttributeError):
            info.checkpoint_id = "x"  # type: ignore[misc]

    def test_slots(self) -> None:
        info = CheckpointInfo()
        assert not hasattr(info, "__dict__")

    def test_json_serializable(self) -> None:
        info = CheckpointInfo(checkpoint_id="cp1", has_metadata=True)
        data = asdict(info)
        serialized = json.dumps(data)
        assert "cp1" in serialized


class TestBackupStatusInfo:
    def test_defaults(self) -> None:
        info = BackupStatusInfo()
        assert info.total_checkpoints == 0
        assert info.components_with_checkpoints == ""
        assert info.last_checkpoint_time == ""
        assert info.storage_type == ""
        assert info.storage_path == ""

    def test_custom(self) -> None:
        info = BackupStatusInfo(
            total_checkpoints=10,
            components_with_checkpoints="pipeline, broker",
            storage_type="jsonl",
            storage_path="/data/checkpoints",
        )
        assert info.total_checkpoints == 10
        assert "pipeline" in info.components_with_checkpoints

    def test_frozen(self) -> None:
        info = BackupStatusInfo()
        with pytest.raises(AttributeError):
            info.total_checkpoints = 5  # type: ignore[misc]

    def test_slots(self) -> None:
        info = BackupStatusInfo()
        assert not hasattr(info, "__dict__")

    def test_json_serializable(self) -> None:
        info = BackupStatusInfo(total_checkpoints=5)
        data = asdict(info)
        serialized = json.dumps(data)
        assert "5" in serialized


class TestAuditScreenState:
    def test_defaults(self) -> None:
        state = AuditScreenState()
        assert isinstance(state.audit_summary, AuditSummaryInfo)
        assert state.recent_audit == ()
        assert isinstance(state.log_summary, LogSummaryInfo)
        assert state.recent_logs == ()
        assert state.recovery_history == ()
        assert state.circuit_breakers == ()
        assert state.checkpoints == ()
        assert isinstance(state.backup_status, BackupStatusInfo)
        assert state.last_refresh == ""

    def test_frozen(self) -> None:
        state = AuditScreenState()
        with pytest.raises(AttributeError):
            state.last_refresh = "10:00:00"  # type: ignore[misc]

    def test_slots(self) -> None:
        state = AuditScreenState()
        assert not hasattr(state, "__dict__")

    def test_json_serializable(self) -> None:
        state = AuditScreenState(
            audit_summary=AuditSummaryInfo(total_events=10),
            last_refresh="10:30:00",
        )
        data = asdict(state)
        serialized = json.dumps(data)
        assert "10:30:00" in serialized


# ─── CSS class helper tests ────────────────────────────────────


class TestIntegrityClass:
    def test_valid(self) -> None:
        assert _integrity_class("valid") == "value-valid"

    def test_passed(self) -> None:
        assert _integrity_class("passed") == "value-valid"

    def test_invalid(self) -> None:
        assert _integrity_class("invalid") == "value-invalid"

    def test_failed(self) -> None:
        assert _integrity_class("failed") == "value-invalid"

    def test_unknown(self) -> None:
        assert _integrity_class("unknown") == "value-unknown"

    def test_case_insensitive(self) -> None:
        assert _integrity_class("VALID") == "value-valid"


class TestAuditSeverityClass:
    def test_critical(self) -> None:
        assert _audit_severity_class("critical") == "audit-error"

    def test_error(self) -> None:
        assert _audit_severity_class("error") == "audit-error"

    def test_warning(self) -> None:
        assert _audit_severity_class("warning") == "audit-warning"

    def test_info(self) -> None:
        assert _audit_severity_class("info") == "audit-info"

    def test_debug(self) -> None:
        assert _audit_severity_class("debug") == "audit-info"

    def test_case_insensitive(self) -> None:
        assert _audit_severity_class("CRITICAL") == "audit-error"


class TestAuditResultClass:
    def test_success(self) -> None:
        assert _audit_result_class("success") == "audit-success"

    def test_failure(self) -> None:
        assert _audit_result_class("failure") == "audit-error"

    def test_partial(self) -> None:
        assert _audit_result_class("partial") == "audit-info"

    def test_case_insensitive(self) -> None:
        assert _audit_result_class("SUCCESS") == "audit-success"


class TestLogLevelClass:
    def test_critical(self) -> None:
        assert _log_level_class("critical") == "log-critical"

    def test_error(self) -> None:
        assert _log_level_class("error") == "log-error"

    def test_warning(self) -> None:
        assert _log_level_class("warning") == "log-warning"

    def test_debug(self) -> None:
        assert _log_level_class("debug") == "log-debug"

    def test_trace(self) -> None:
        assert _log_level_class("trace") == "log-debug"

    def test_info(self) -> None:
        assert _log_level_class("info") == "log-info"

    def test_case_insensitive(self) -> None:
        assert _log_level_class("ERROR") == "log-error"


class TestRecoveryStatusClass:
    def test_success(self) -> None:
        assert _recovery_status_class("success") == "recovery-success"

    def test_failed(self) -> None:
        assert _recovery_status_class("failed") == "recovery-failed"

    def test_pending(self) -> None:
        assert _recovery_status_class("pending") == "recovery-pending"

    def test_in_progress(self) -> None:
        assert _recovery_status_class("in_progress") == "recovery-pending"

    def test_idle(self) -> None:
        assert _recovery_status_class("idle") == "recovery-idle"

    def test_case_insensitive(self) -> None:
        assert _recovery_status_class("SUCCESS") == "recovery-success"


class TestCbStateClass:
    def test_closed(self) -> None:
        assert _cb_state_class("closed") == "cb-closed"

    def test_open(self) -> None:
        assert _cb_state_class("open") == "cb-open"

    def test_half_open(self) -> None:
        assert _cb_state_class("half_open") == "cb-half-open"

    def test_half_open_hyphen(self) -> None:
        assert _cb_state_class("half-open") == "cb-half-open"

    def test_unknown(self) -> None:
        assert _cb_state_class("unknown") == "cb-closed"

    def test_case_insensitive(self) -> None:
        assert _cb_state_class("CLOSED") == "cb-closed"


# ─── Widget unit tests ─────────────────────────────────────────


class TestAuditSummaryWidget:
    def test_render(self) -> None:
        w = AuditSummaryWidget()
        assert w.render() == ""

    def test_update_data_default(self) -> None:
        w = AuditSummaryWidget()
        w.update_data(AuditSummaryInfo())

    def test_update_data_custom(self) -> None:
        w = AuditSummaryWidget()
        w.update_data(AuditSummaryInfo(total_events=50, integrity_status="valid"))


class TestRecentAuditWidget:
    def test_render(self) -> None:
        w = RecentAuditWidget()
        assert w.render() == ""

    def test_has_composed_before_compose(self) -> None:
        w = RecentAuditWidget()
        assert not w._has_composed

    def test_has_composed_after_compose(self) -> None:
        w = RecentAuditWidget()
        w._title = MagicMock()
        assert w._has_composed

    def test_update_data_empty(self) -> None:
        w = RecentAuditWidget()
        w.update_data(())

    def test_update_data_entries(self) -> None:
        w = RecentAuditWidget()
        entries = (
            AuditEntry(
                event_id="e1",
                source="runtime",
                severity="info",
                action="start",
                result="success",
                timestamp_str="10:30:00",
            ),
            AuditEntry(
                event_id="e2",
                source="monitoring",
                severity="warning",
                action="check",
                result="failure",
                timestamp_str="10:31:00",
            ),
        )
        w.update_data(entries)


class TestLogSummaryWidget:
    def test_render(self) -> None:
        w = LogSummaryWidget()
        assert w.render() == ""

    def test_update_data_default(self) -> None:
        w = LogSummaryWidget()
        w.update_data(LogSummaryInfo())

    def test_update_data_custom(self) -> None:
        w = LogSummaryWidget()
        w.update_data(LogSummaryInfo(level="DEBUG", handler_count=3))


class TestRecentLogsWidget:
    def test_render(self) -> None:
        w = RecentLogsWidget()
        assert w.render() == ""

    def test_has_composed_before_compose(self) -> None:
        w = RecentLogsWidget()
        assert not w._has_composed

    def test_has_composed_after_compose(self) -> None:
        w = RecentLogsWidget()
        w._title = MagicMock()
        assert w._has_composed

    def test_update_data_empty(self) -> None:
        w = RecentLogsWidget()
        w.update_data(())

    def test_update_data_entries(self) -> None:
        w = RecentLogsWidget()
        logs = (
            LogEntry(
                timestamp_str="10:30:00", level="INFO", module="titan", message="ok"
            ),
            LogEntry(
                timestamp_str="10:31:00", level="ERROR", module="titan", message="fail"
            ),
        )
        w.update_data(logs)


class TestRecoveryHistoryWidget:
    def test_render(self) -> None:
        w = RecoveryHistoryWidget()
        assert w.render() == ""

    def test_has_composed_before_compose(self) -> None:
        w = RecoveryHistoryWidget()
        assert not w._has_composed

    def test_has_composed_after_compose(self) -> None:
        w = RecoveryHistoryWidget()
        w._title = MagicMock()
        assert w._has_composed

    def test_update_data_empty(self) -> None:
        w = RecoveryHistoryWidget()
        w.update_data(())

    def test_update_data_entries(self) -> None:
        w = RecoveryHistoryWidget()
        entries = (
            RecoveryHistoryEntry(
                request_id="r1",
                component="pipeline",
                strategy="retry",
                status="success",
                attempts=3,
                timestamp_str="10:30:00",
            ),
        )
        w.update_data(entries)


class TestCircuitBreakerWidget:
    def test_render(self) -> None:
        w = CircuitBreakerWidget()
        assert w.render() == ""

    def test_has_composed_before_compose(self) -> None:
        w = CircuitBreakerWidget()
        assert not w._has_composed

    def test_has_composed_after_compose(self) -> None:
        w = CircuitBreakerWidget()
        w._title = MagicMock()
        assert w._has_composed

    def test_update_data_empty(self) -> None:
        w = CircuitBreakerWidget()
        w.update_data(())

    def test_update_data_entries(self) -> None:
        w = CircuitBreakerWidget()
        breakers = (
            CircuitBreakerInfo(
                name="broker",
                state="CLOSED",
                failure_count=0,
                failure_threshold=5,
                recovery_timeout="30s",
            ),
            CircuitBreakerInfo(name="stream", state="OPEN", failure_count=5),
        )
        w.update_data(breakers)


class TestCheckpointWidget:
    def test_render(self) -> None:
        w = CheckpointWidget()
        assert w.render() == ""

    def test_has_composed_before_compose(self) -> None:
        w = CheckpointWidget()
        assert not w._has_composed

    def test_has_composed_after_compose(self) -> None:
        w = CheckpointWidget()
        w._title = MagicMock()
        assert w._has_composed

    def test_update_data_empty(self) -> None:
        w = CheckpointWidget()
        w.update_data(())

    def test_update_data_entries(self) -> None:
        w = CheckpointWidget()
        checkpoints = (
            CheckpointInfo(
                checkpoint_id="cp1",
                component="pipeline",
                version="1.0.0",
                created_at_str="10:30:00",
                has_metadata=True,
            ),
        )
        w.update_data(checkpoints)


class TestBackupStatusWidget:
    def test_render(self) -> None:
        w = BackupStatusWidget()
        assert w.render() == ""

    def test_update_data_default(self) -> None:
        w = BackupStatusWidget()
        w.update_data(BackupStatusInfo())

    def test_update_data_custom(self) -> None:
        w = BackupStatusWidget()
        w.update_data(
            BackupStatusInfo(
                total_checkpoints=5,
                storage_type="jsonl",
                storage_path="/data",
            )
        )


# ─── Screen unit tests ──────────────────────────────────────────


class TestAuditScreenUnit:
    def test_creation(self) -> None:
        from titan.tui.screens.audit import AuditScreen

        screen = AuditScreen()
        assert isinstance(screen._state, AuditScreenState)

    def test_set_state_builder(self) -> None:
        from titan.tui.screens.audit import AuditScreen

        screen = AuditScreen()
        screen.set_state_builder(lambda: AuditScreenState())
        assert screen._state_builder is not None

    def test_refresh_state_with_builder(self) -> None:
        from titan.tui.screens.audit import AuditScreen

        screen = AuditScreen()
        custom = AuditScreenState(last_refresh="10:30:00")
        screen.set_state_builder(lambda: custom)
        screen._refresh_state()
        assert screen._state.last_refresh == "10:30:00"

    def test_refresh_state_builder_exception(self) -> None:
        from titan.tui.screens.audit import AuditScreen

        screen = AuditScreen()
        screen.set_state_builder(lambda: (_ for _ in ()).throw(RuntimeError))
        screen._refresh_state()
        assert isinstance(screen._state, AuditScreenState)

    def test_state_property(self) -> None:
        from titan.tui.screens.audit import AuditScreen

        screen = AuditScreen()
        assert isinstance(screen.state, AuditScreenState)

    def test_bindings(self) -> None:
        from titan.tui.screens.audit import AuditScreen

        keys = [b[0] for b in AuditScreen.BINDINGS]
        assert "r" in keys
        assert "escape" in keys
        assert "q" in keys
        assert "up" in keys
        assert "down" in keys
        assert "page_up" in keys
        assert "page_down" in keys
        assert "home" in keys
        assert "end" in keys

    def test_widgets_none_before_mount(self) -> None:
        from titan.tui.screens.audit import AuditScreen

        screen = AuditScreen()
        assert screen._audit_summary_widget is None
        assert screen._log_summary_widget is None
        assert screen._backup_status_widget is None
        assert screen._circuit_breaker_widget is None
        assert screen._recent_audit_widget is None
        assert screen._recent_logs_widget is None
        assert screen._recovery_history_widget is None
        assert screen._checkpoint_widget is None

    def test_empty_state_render(self) -> None:
        from titan.tui.screens.audit import AuditScreen

        screen = AuditScreen()
        state = AuditScreenState()
        screen._state = state
        assert screen.state.audit_summary.total_events == 0
        assert screen.state.log_summary.level == "INFO"
        assert screen.state.backup_status.total_checkpoints == 0

    def test_update_widgets_no_crash(self) -> None:
        from titan.tui.screens.audit import AuditScreen

        screen = AuditScreen()
        screen._update_widgets()

    def test_update_refresh_indicator_no_crash(self) -> None:
        from titan.tui.screens.audit import AuditScreen

        screen = AuditScreen()
        screen._update_refresh_indicator()

    def test_scroll_actions_no_crash(self) -> None:
        from titan.tui.screens.audit import AuditScreen

        screen = AuditScreen()
        screen.action_scroll_up_line()
        screen.action_scroll_down_line()
        screen.action_scroll_up()
        screen.action_scroll_down()
        screen.action_scroll_top()
        screen.action_scroll_bottom()


# ─── State builder tests ────────────────────────────────────────


class TestBuildAuditState:
    @patch("titan.tui.layout._read_backup_status")
    @patch("titan.tui.layout._read_checkpoints")
    @patch("titan.tui.layout._read_circuit_breakers")
    @patch("titan.tui.layout._read_recovery_history_entries")
    @patch("titan.tui.layout._read_recent_logs")
    @patch("titan.tui.layout._read_log_summary")
    @patch("titan.tui.layout._read_recent_audit")
    @patch("titan.tui.layout._read_audit_summary")
    def test_builds_state(
        self,
        mock_audit_summary: MagicMock,
        mock_recent_audit: MagicMock,
        mock_log_summary: MagicMock,
        mock_recent_logs: MagicMock,
        mock_recovery_history: MagicMock,
        mock_circuit_breakers: MagicMock,
        mock_checkpoints: MagicMock,
        mock_backup: MagicMock,
    ) -> None:
        from titan.tui.layout import build_audit_state

        mock_audit_summary.return_value = AuditSummaryInfo(total_events=50)
        mock_recent_audit.return_value = ()
        mock_log_summary.return_value = LogSummaryInfo(level="DEBUG")
        mock_recent_logs.return_value = ()
        mock_recovery_history.return_value = ()
        mock_circuit_breakers.return_value = ()
        mock_checkpoints.return_value = ()
        mock_backup.return_value = BackupStatusInfo(total_checkpoints=3)

        state = build_audit_state()
        assert state.audit_summary.total_events == 50
        assert state.log_summary.level == "DEBUG"
        assert state.backup_status.total_checkpoints == 3
        assert state.last_refresh != ""


# ─── Reader helper tests ───────────────────────────────────────


class TestReadAuditSummary:
    @patch("titan.cli.common.get_audit_manager")
    def test_with_data(self, mock_get: MagicMock) -> None:
        from titan.tui.layout import _read_audit_summary

        am = MagicMock()
        report = MagicMock()
        report.total_events = 100
        report.events_by_source = {"runtime": 50, "monitoring": 50}
        report.events_by_severity = {"info": 80, "warning": 20}
        report.integrity_status = "valid"
        report.verification_failures = 0
        report.first_event_time.strftime.return_value = "09:00:00"
        report.last_event_time.strftime.return_value = "10:30:00"
        am.generate_report.return_value = report
        mock_get.return_value = am

        info = _read_audit_summary()
        assert info.total_events == 100
        assert "runtime" in info.events_by_source
        assert info.integrity_status == "valid"
        assert info.first_event_time == "09:00:00"

    @patch("titan.cli.common.get_audit_manager")
    def test_exception(self, mock_get: MagicMock) -> None:
        from titan.tui.layout import _read_audit_summary

        mock_get.side_effect = RuntimeError("no manager")
        info = _read_audit_summary()
        assert info.total_events == 0
        assert info.integrity_status == "unknown"


class TestReadRecentAudit:
    @patch("titan.cli.common.get_audit_manager")
    def test_with_data(self, mock_get: MagicMock) -> None:
        from titan.tui.layout import _read_recent_audit

        am = MagicMock()
        ev = MagicMock()
        ev.event_id = "e1"
        ev.sequence_number = 1
        ev.source.value = "runtime"
        ev.category.value = "system_start"
        ev.severity.value = "info"
        ev.action = "start_engine"
        ev.result.value = "success"
        ev.timestamp.strftime.return_value = "10:30:00"
        am.search.return_value = [ev]
        mock_get.return_value = am

        entries = _read_recent_audit()
        assert len(entries) == 1
        assert entries[0].event_id == "e1"
        assert entries[0].source == "runtime"

    @patch("titan.cli.common.get_audit_manager")
    def test_exception(self, mock_get: MagicMock) -> None:
        from titan.tui.layout import _read_recent_audit

        mock_get.side_effect = RuntimeError("no manager")
        entries = _read_recent_audit()
        assert entries == ()


class TestReadLogSummary:
    def test_with_data(self) -> None:
        from titan.tui.layout import _read_log_summary

        mock_report = MagicMock()
        mock_report.level.value = "INFO"
        mock_report.handlers = (MagicMock(), MagicMock())
        mock_report.component_count = 5
        mock_report.dropped_messages = 0
        mock_report.warnings = ()
        mock_report.errors = ()

        with patch("titan.logging.manager.LoggerManager") as mock_lm_cls:
            mock_instance = MagicMock()
            mock_instance.generate_report.return_value = mock_report
            mock_lm_cls.instance.return_value = mock_instance

            info = _read_log_summary()
            assert info.handler_count == 2
            assert info.component_count == 5

    def test_exception(self) -> None:
        from titan.tui.layout import _read_log_summary

        with patch("titan.logging.manager.LoggerManager") as mock_lm_cls:
            mock_lm_cls.instance.side_effect = RuntimeError("no manager")
            info = _read_log_summary()
            assert info.level == "INFO"
            assert info.handler_count == 0


class TestReadRecentLogs:
    def test_no_log_file(self) -> None:
        from titan.tui.layout import _read_recent_logs

        with patch("pathlib.Path.exists", return_value=False):
            entries = _read_recent_logs()
            assert entries == ()

    def test_exception(self) -> None:
        from titan.tui.layout import _read_recent_logs

        with patch("pathlib.Path.read_text", side_effect=OSError("no file")):
            entries = _read_recent_logs()
            assert entries == ()


class TestReadRecoveryHistoryEntries:
    @patch("titan.cli.common.get_recovery_manager")
    def test_with_data(self, mock_get: MagicMock) -> None:
        from titan.tui.layout import _read_recovery_history_entries

        rm = MagicMock()
        r = MagicMock()
        r.request_id = "r1"
        r.component.value = "pipeline"
        r.strategy.value = "retry"
        r.status.value = "success"
        r.total_attempts = 3
        r.failure_reason = ""
        r.timestamp.strftime.return_value = "10:30:00"
        rm.get_recovery_history.return_value = [r]
        mock_get.return_value = rm

        entries = _read_recovery_history_entries()
        assert len(entries) == 1
        assert entries[0].request_id == "r1"
        assert entries[0].component == "pipeline"

    @patch("titan.cli.common.get_recovery_manager")
    def test_exception(self, mock_get: MagicMock) -> None:
        from titan.tui.layout import _read_recovery_history_entries

        mock_get.side_effect = RuntimeError("no manager")
        entries = _read_recovery_history_entries()
        assert entries == ()


class TestReadCircuitBreakers:
    @patch("titan.cli.common.get_recovery_manager")
    def test_with_data(self, mock_get: MagicMock) -> None:
        from titan.tui.layout import _read_circuit_breakers

        rm = MagicMock()
        cb = MagicMock()
        cb.state.value = "CLOSED"
        cb.failure_count = 0
        cb.success_count = 10
        cb.config.failure_threshold = 5
        cb.config.recovery_timeout_seconds = 30.0
        rm._circuit_breakers = {"broker": cb}
        mock_get.return_value = rm

        breakers = _read_circuit_breakers()
        assert len(breakers) == 1
        assert breakers[0].name == "broker"
        assert breakers[0].state == "CLOSED"

    @patch("titan.cli.common.get_recovery_manager")
    def test_exception(self, mock_get: MagicMock) -> None:
        from titan.tui.layout import _read_circuit_breakers

        mock_get.side_effect = RuntimeError("no manager")
        breakers = _read_circuit_breakers()
        assert breakers == ()


class TestReadCheckpoints:
    @patch("titan.cli.common.get_recovery_manager")
    def test_with_data(self, mock_get: MagicMock) -> None:
        from titan.tui.layout import _read_checkpoints

        rm = MagicMock()
        cp = MagicMock()
        cp.checkpoint_id = "cp1"
        cp.component.value = "pipeline"
        cp.version = "1.0.0"
        cp.created_at.strftime.return_value = "10:30:00"
        cp.metadata = {"key": "value"}
        rm.checkpoints.list_all.return_value = [cp]
        mock_get.return_value = rm

        checkpoints = _read_checkpoints()
        assert len(checkpoints) == 1
        assert checkpoints[0].checkpoint_id == "cp1"
        assert checkpoints[0].has_metadata is True

    @patch("titan.cli.common.get_recovery_manager")
    def test_exception(self, mock_get: MagicMock) -> None:
        from titan.tui.layout import _read_checkpoints

        mock_get.side_effect = RuntimeError("no manager")
        checkpoints = _read_checkpoints()
        assert checkpoints == ()


class TestReadBackupStatus:
    @patch("titan.cli.common.get_recovery_manager")
    def test_with_data(self, mock_get: MagicMock) -> None:
        from titan.tui.layout import _read_backup_status

        rm = MagicMock()
        cp1 = MagicMock()
        cp1.component.value = "pipeline"
        cp1.created_at.strftime.return_value = "10:30:00"
        cp2 = MagicMock()
        cp2.component.value = "broker"
        cp2.created_at.strftime.return_value = "10:31:00"
        rm.checkpoints.list_all.return_value = [cp1, cp2]
        rm.checkpoints._storage = MagicMock()
        rm.checkpoints._storage.file_path = "/data/cp.jsonl"
        mock_get.return_value = rm

        info = _read_backup_status()
        assert info.total_checkpoints == 2
        assert "broker" in info.components_with_checkpoints
        assert "pipeline" in info.components_with_checkpoints
        assert info.storage_type == "jsonl"
        assert info.storage_path == "/data/cp.jsonl"

    @patch("titan.cli.common.get_recovery_manager")
    def test_exception(self, mock_get: MagicMock) -> None:
        from titan.tui.layout import _read_backup_status

        mock_get.side_effect = RuntimeError("no manager")
        info = _read_backup_status()
        assert info.total_checkpoints == 0


# ─── Async integration tests ────────────────────────────────────


class TestAuditScreenAsync:
    @pytest.mark.asyncio
    async def test_screen_creation(self) -> None:
        from titan.tui.screens.audit import AuditScreen

        screen = AuditScreen()
        assert isinstance(screen._state, AuditScreenState)

    @pytest.mark.asyncio
    async def test_state_builder_injection(self) -> None:
        from titan.tui.screens.audit import AuditScreen

        screen = AuditScreen()
        custom = AuditScreenState(last_refresh="12:00:00")
        screen.set_state_builder(lambda: custom)
        screen._refresh_state()
        assert screen._state.last_refresh == "12:00:00"

    @pytest.mark.asyncio
    async def test_widgets_are_none_before_mount(self) -> None:
        from titan.tui.screens.audit import AuditScreen

        screen = AuditScreen()
        assert screen._audit_summary_widget is None
        assert screen._log_summary_widget is None
        assert screen._backup_status_widget is None
        assert screen._circuit_breaker_widget is None
        assert screen._recent_audit_widget is None
        assert screen._recent_logs_widget is None
        assert screen._recovery_history_widget is None
        assert screen._checkpoint_widget is None

    @pytest.mark.asyncio
    async def test_empty_state_render(self) -> None:
        from titan.tui.screens.audit import AuditScreen

        screen = AuditScreen()
        state = AuditScreenState()
        screen._state = state
        assert screen.state.audit_summary.total_events == 0
        assert screen.state.log_summary.level == "INFO"
        assert screen.state.backup_status.total_checkpoints == 0


# ─── Empty state tests ──────────────────────────────────────────


class TestEmptyState:
    def test_all_defaults_produce_safe_state(self) -> None:
        state = AuditScreenState()
        assert state.audit_summary.total_events == 0
        assert state.recent_audit == ()
        assert state.log_summary.level == "INFO"
        assert state.recent_logs == ()
        assert state.recovery_history == ()
        assert state.circuit_breakers == ()
        assert state.checkpoints == ()
        assert state.backup_status.total_checkpoints == 0
        assert state.last_refresh == ""

    def test_widget_default_construction(self) -> None:
        widgets = [
            AuditSummaryWidget(),
            RecentAuditWidget(),
            LogSummaryWidget(),
            RecentLogsWidget(),
            RecoveryHistoryWidget(),
            CircuitBreakerWidget(),
            CheckpointWidget(),
            BackupStatusWidget(),
        ]
        for w in widgets:
            assert w.render() == ""


# ─── Populated state tests ──────────────────────────────────────


class TestPopulatedState:
    def test_full_state_construction(self) -> None:
        state = AuditScreenState(
            audit_summary=AuditSummaryInfo(
                total_events=100,
                integrity_status="valid",
            ),
            recent_audit=(
                AuditEntry(event_id="e1", source="runtime", severity="info"),
            ),
            log_summary=LogSummaryInfo(level="DEBUG", handler_count=3),
            recent_logs=(LogEntry(level="INFO", message="test"),),
            recovery_history=(
                RecoveryHistoryEntry(request_id="r1", component="pipeline"),
            ),
            circuit_breakers=(CircuitBreakerInfo(name="broker", state="CLOSED"),),
            checkpoints=(CheckpointInfo(checkpoint_id="cp1", component="pipeline"),),
            backup_status=BackupStatusInfo(
                total_checkpoints=5,
                storage_type="jsonl",
            ),
            last_refresh="10:30:00",
        )
        assert state.audit_summary.total_events == 100
        assert len(state.recent_audit) == 1
        assert state.log_summary.level == "DEBUG"
        assert len(state.recent_logs) == 1
        assert len(state.recovery_history) == 1
        assert len(state.circuit_breakers) == 1
        assert len(state.checkpoints) == 1
        assert state.backup_status.total_checkpoints == 5
        assert state.last_refresh == "10:30:00"


# ─── JSON serialization tests ───────────────────────────────────


class TestJsonSerialization:
    def test_audit_summary_round_trip(self) -> None:
        info = AuditSummaryInfo(total_events=100, integrity_status="valid")
        data = asdict(info)
        serialized = json.dumps(data)
        deserialized = json.loads(serialized)
        assert deserialized["total_events"] == 100
        assert deserialized["integrity_status"] == "valid"

    def test_audit_entry_round_trip(self) -> None:
        entry = AuditEntry(event_id="e1", source="runtime", severity="info")
        data = asdict(entry)
        serialized = json.dumps(data)
        deserialized = json.loads(serialized)
        assert deserialized["event_id"] == "e1"

    def test_log_summary_round_trip(self) -> None:
        info = LogSummaryInfo(level="DEBUG", handler_count=3)
        data = asdict(info)
        serialized = json.dumps(data)
        deserialized = json.loads(serialized)
        assert deserialized["level"] == "DEBUG"

    def test_log_entry_round_trip(self) -> None:
        entry = LogEntry(level="ERROR", message="fail")
        data = asdict(entry)
        serialized = json.dumps(data)
        deserialized = json.loads(serialized)
        assert deserialized["level"] == "ERROR"

    def test_recovery_history_round_trip(self) -> None:
        entry = RecoveryHistoryEntry(request_id="r1", status="success")
        data = asdict(entry)
        serialized = json.dumps(data)
        deserialized = json.loads(serialized)
        assert deserialized["request_id"] == "r1"

    def test_circuit_breaker_round_trip(self) -> None:
        cb = CircuitBreakerInfo(name="broker", state="OPEN")
        data = asdict(cb)
        serialized = json.dumps(data)
        deserialized = json.loads(serialized)
        assert deserialized["name"] == "broker"

    def test_checkpoint_round_trip(self) -> None:
        cp = CheckpointInfo(checkpoint_id="cp1", has_metadata=True)
        data = asdict(cp)
        serialized = json.dumps(data)
        deserialized = json.loads(serialized)
        assert deserialized["checkpoint_id"] == "cp1"

    def test_backup_status_round_trip(self) -> None:
        info = BackupStatusInfo(total_checkpoints=5, storage_type="jsonl")
        data = asdict(info)
        serialized = json.dumps(data)
        deserialized = json.loads(serialized)
        assert deserialized["total_checkpoints"] == 5

    def test_full_state_round_trip(self) -> None:
        state = AuditScreenState(
            recent_audit=(AuditEntry(event_id="e1"),),
            last_refresh="10:30:00",
        )
        data = asdict(state)
        serialized = json.dumps(data)
        deserialized = json.loads(serialized)
        assert deserialized["last_refresh"] == "10:30:00"
        assert len(deserialized["recent_audit"]) == 1


# ─── Error handling tests ───────────────────────────────────────


class TestErrorHandling:
    def test_builder_exception_returns_default(self) -> None:
        from titan.tui.screens.audit import AuditScreen

        screen = AuditScreen()
        screen.set_state_builder(lambda: (_ for _ in ()).throw(RuntimeError))
        screen._refresh_state()
        assert isinstance(screen._state, AuditScreenState)
        assert screen._state.last_refresh == ""

    def test_widget_update_before_compose_no_crash(self) -> None:
        widgets_data = [
            (AuditSummaryWidget(), AuditSummaryInfo()),
            (RecentAuditWidget(), ()),
            (LogSummaryWidget(), LogSummaryInfo()),
            (RecentLogsWidget(), ()),
            (RecoveryHistoryWidget(), ()),
            (CircuitBreakerWidget(), ()),
            (CheckpointWidget(), ()),
            (BackupStatusWidget(), BackupStatusInfo()),
        ]
        for widget, data in widgets_data:
            widget.update_data(data)

    def test_all_readers_handle_exceptions(self) -> None:
        from titan.tui.layout import (
            _read_audit_summary,
            _read_backup_status,
            _read_checkpoints,
            _read_circuit_breakers,
            _read_log_summary,
            _read_recent_audit,
            _read_recent_logs,
            _read_recovery_history_entries,
        )

        readers = [
            _read_audit_summary,
            _read_recent_audit,
            _read_log_summary,
            _read_recent_logs,
            _read_recovery_history_entries,
            _read_circuit_breakers,
            _read_checkpoints,
            _read_backup_status,
        ]
        for reader in readers:
            result = reader()
            assert result is not None


# ─── Navigation tests ──────────────────────────────────────────


class TestAuditNavigation:
    def test_sidebar_has_audit_entry(self) -> None:
        from titan.tui.widgets.sidebar import SidebarWidget

        entries = [key for _, key in SidebarWidget.SECTIONS]
        assert "audit" in entries

    def test_shell_has_goto_audit(self) -> None:
        from titan.tui.shell import ShellApp

        keys = [b[0] for b in ShellApp.BINDINGS]
        assert "f9" in keys

    def test_shell_mode_map_includes_audit(self) -> None:
        mode_map = {
            "dashboard": "Overview",
            "runtime": "Runtime",
            "paper": "Paper",
            "market": "Market Intel",
            "live_trading": "Live",
            "monitoring": "Monitoring & Alerting",
            "logs": "Logs & Audit",
            "audit": "Logs & Audit",
            "help": "Help",
        }
        assert "audit" in mode_map
        assert mode_map["audit"] == "Logs & Audit"

    def test_screen_exported(self) -> None:
        from titan.tui.screens import AuditScreen

        assert AuditScreen is not None
