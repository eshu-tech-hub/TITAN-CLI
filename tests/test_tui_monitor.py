"""Tests for the Monitoring & Alerting TUI screen."""

from __future__ import annotations

import json
from dataclasses import asdict
from unittest.mock import MagicMock, patch

import pytest

from titan.tui.models import (
    AlertEntry,
    AlertHistoryEntry,
    AlertSummaryInfo,
    MonitoringEventEntry,
    MonitoringScreenState,
    RecoveryStatusInfo,
    ResourceMetricEntry,
    ResourceMetricsInfo,
    SubsystemHealthEntry,
    SystemHealthInfo,
    TelemetryInfo,
)
from titan.tui.widgets.monitor import (
    ActiveAlertsWidget,
    AlertHistoryWidget,
    AlertSummaryWidget,
    MetricsWidget,
    MonitoringEventsWidget,
    RecoveryStatusWidget,
    SystemHealthWidget,
    TelemetryWidget,
    _alert_level_class,
    _event_level_class,
    _health_class,
    _history_status_class,
    _recovery_class,
    _trend_class,
)

# ─── Model tests ────────────────────────────────────────────────


class TestSubsystemHealthEntry:
    def test_defaults(self) -> None:
        entry = SubsystemHealthEntry()
        assert entry.name == ""
        assert entry.status == "Unknown"
        assert entry.message == ""
        assert entry.latency_ms == "0"
        assert entry.failures == 0

    def test_custom(self) -> None:
        entry = SubsystemHealthEntry(
            name="market",
            status="healthy",
            message="OK",
            latency_ms="1.5",
            failures=0,
        )
        assert entry.name == "market"
        assert entry.status == "healthy"

    def test_frozen(self) -> None:
        entry = SubsystemHealthEntry()
        with pytest.raises(AttributeError):
            entry.name = "test"  # type: ignore[misc]

    def test_slots(self) -> None:
        entry = SubsystemHealthEntry()
        assert not hasattr(entry, "__dict__")


class TestSystemHealthInfo:
    def test_defaults(self) -> None:
        info = SystemHealthInfo()
        assert info.overall_status == "Unknown"
        assert info.healthy_count == 0
        assert info.warning_count == 0
        assert info.critical_count == 0
        assert info.offline_count == 0
        assert info.subsystems == ()

    def test_custom(self) -> None:
        subs = (SubsystemHealthEntry(name="market", status="healthy"),)
        info = SystemHealthInfo(
            overall_status="healthy",
            healthy_count=1,
            subsystems=subs,
        )
        assert info.overall_status == "healthy"
        assert len(info.subsystems) == 1

    def test_frozen(self) -> None:
        info = SystemHealthInfo()
        with pytest.raises(AttributeError):
            info.overall_status = "test"  # type: ignore[misc]

    def test_slots(self) -> None:
        info = SystemHealthInfo()
        assert not hasattr(info, "__dict__")

    def test_json_serializable(self) -> None:
        info = SystemHealthInfo(
            overall_status="healthy",
            healthy_count=3,
            subsystems=(SubsystemHealthEntry(name="market"),),
        )
        data = asdict(info)
        serialized = json.dumps(data)
        assert "healthy" in serialized


class TestTelemetryInfo:
    def test_defaults(self) -> None:
        info = TelemetryInfo()
        assert info.total_metrics == 0
        assert info.active_collectors == 0
        assert info.failed_collections == 0
        assert info.total_collections == 0
        assert info.uptime == "00:00:00"

    def test_custom(self) -> None:
        info = TelemetryInfo(
            total_metrics=10,
            active_collectors=3,
            uptime="01:30:00",
        )
        assert info.total_metrics == 10
        assert info.uptime == "01:30:00"

    def test_frozen(self) -> None:
        info = TelemetryInfo()
        with pytest.raises(AttributeError):
            info.total_metrics = 5  # type: ignore[misc]

    def test_slots(self) -> None:
        info = TelemetryInfo()
        assert not hasattr(info, "__dict__")

    def test_json_serializable(self) -> None:
        info = TelemetryInfo(total_metrics=10)
        data = asdict(info)
        serialized = json.dumps(data)
        assert "10" in serialized


class TestResourceMetricEntry:
    def test_defaults(self) -> None:
        entry = ResourceMetricEntry()
        assert entry.name == ""
        assert entry.value == "0"
        assert entry.unit == ""
        assert entry.trend == "stable"

    def test_custom(self) -> None:
        entry = ResourceMetricEntry(
            name="cpu",
            value="45.2",
            unit="%",
            trend="up",
        )
        assert entry.name == "cpu"
        assert entry.trend == "up"

    def test_frozen(self) -> None:
        entry = ResourceMetricEntry()
        with pytest.raises(AttributeError):
            entry.name = "test"  # type: ignore[misc]

    def test_slots(self) -> None:
        entry = ResourceMetricEntry()
        assert not hasattr(entry, "__dict__")


class TestResourceMetricsInfo:
    def test_defaults(self) -> None:
        info = ResourceMetricsInfo()
        assert info.metrics == ()

    def test_custom(self) -> None:
        metrics = (ResourceMetricEntry(name="cpu"),)
        info = ResourceMetricsInfo(metrics=metrics)
        assert len(info.metrics) == 1

    def test_frozen(self) -> None:
        info = ResourceMetricsInfo()
        with pytest.raises(AttributeError):
            info.metrics = ()  # type: ignore[misc]

    def test_slots(self) -> None:
        info = ResourceMetricsInfo()
        assert not hasattr(info, "__dict__")


class TestAlertSummaryInfo:
    def test_defaults(self) -> None:
        info = AlertSummaryInfo()
        assert info.total == 0
        assert info.active == 0
        assert info.critical == 0
        assert info.acknowledged == 0
        assert info.resolved == 0
        assert info.escalated == 0

    def test_custom(self) -> None:
        info = AlertSummaryInfo(total=10, active=3, critical=1)
        assert info.total == 10
        assert info.critical == 1

    def test_frozen(self) -> None:
        info = AlertSummaryInfo()
        with pytest.raises(AttributeError):
            info.total = 5  # type: ignore[misc]

    def test_slots(self) -> None:
        info = AlertSummaryInfo()
        assert not hasattr(info, "__dict__")

    def test_json_serializable(self) -> None:
        info = AlertSummaryInfo(total=10, active=3)
        data = asdict(info)
        serialized = json.dumps(data)
        assert "10" in serialized


class TestAlertEntry:
    def test_defaults(self) -> None:
        entry = AlertEntry()
        assert entry.alert_id == ""
        assert entry.level == ""
        assert entry.source == ""
        assert entry.title == ""
        assert entry.message == ""
        assert entry.status == ""
        assert entry.timestamp_str == ""

    def test_custom(self) -> None:
        entry = AlertEntry(
            alert_id="a1",
            level="critical",
            source="monitoring",
            title="High CPU",
            message="CPU at 95%",
            status="new",
            timestamp_str="10:30:00",
        )
        assert entry.alert_id == "a1"
        assert entry.level == "critical"

    def test_frozen(self) -> None:
        entry = AlertEntry()
        with pytest.raises(AttributeError):
            entry.alert_id = "test"  # type: ignore[misc]

    def test_slots(self) -> None:
        entry = AlertEntry()
        assert not hasattr(entry, "__dict__")


class TestAlertHistoryEntry:
    def test_defaults(self) -> None:
        entry = AlertHistoryEntry()
        assert entry.alert_id == ""
        assert entry.level == ""
        assert entry.source == ""
        assert entry.title == ""
        assert entry.status == ""
        assert entry.timestamp_str == ""
        assert entry.duration == ""

    def test_custom(self) -> None:
        entry = AlertHistoryEntry(
            alert_id="a1",
            level="warning",
            source="runtime",
            title="Slow pipeline",
            status="resolved",
            timestamp_str="10:30:00",
            duration="00:05:00",
        )
        assert entry.duration == "00:05:00"

    def test_frozen(self) -> None:
        entry = AlertHistoryEntry()
        with pytest.raises(AttributeError):
            entry.duration = "test"  # type: ignore[misc]

    def test_slots(self) -> None:
        entry = AlertHistoryEntry()
        assert not hasattr(entry, "__dict__")


class TestRecoveryStatusInfo:
    def test_defaults(self) -> None:
        info = RecoveryStatusInfo()
        assert info.status == "Idle"
        assert info.total_attempts == 0
        assert info.successful == 0
        assert info.failed == 0
        assert info.last_strategy == ""
        assert info.recovered_components == ""

    def test_custom(self) -> None:
        info = RecoveryStatusInfo(
            status="success",
            total_attempts=3,
            successful=2,
            failed=1,
            last_strategy="retry",
            recovered_components="pipeline, broker",
        )
        assert info.status == "success"
        assert info.recovered_components == "pipeline, broker"

    def test_frozen(self) -> None:
        info = RecoveryStatusInfo()
        with pytest.raises(AttributeError):
            info.status = "test"  # type: ignore[misc]

    def test_slots(self) -> None:
        info = RecoveryStatusInfo()
        assert not hasattr(info, "__dict__")


class TestMonitoringEventEntry:
    def test_defaults(self) -> None:
        entry = MonitoringEventEntry()
        assert entry.level == "info"
        assert entry.source == ""
        assert entry.message == ""
        assert entry.timestamp_str == ""

    def test_custom(self) -> None:
        entry = MonitoringEventEntry(
            level="warning",
            source="monitoring",
            message="High latency",
            timestamp_str="10:30:00",
        )
        assert entry.level == "warning"

    def test_frozen(self) -> None:
        entry = MonitoringEventEntry()
        with pytest.raises(AttributeError):
            entry.level = "test"  # type: ignore[misc]

    def test_slots(self) -> None:
        entry = MonitoringEventEntry()
        assert not hasattr(entry, "__dict__")


class TestMonitoringScreenState:
    def test_defaults(self) -> None:
        state = MonitoringScreenState()
        assert isinstance(state.system_health, SystemHealthInfo)
        assert isinstance(state.telemetry, TelemetryInfo)
        assert isinstance(state.resource_metrics, ResourceMetricsInfo)
        assert isinstance(state.alert_summary, AlertSummaryInfo)
        assert state.active_alerts == ()
        assert state.alert_history == ()
        assert isinstance(state.recovery_status, RecoveryStatusInfo)
        assert state.monitoring_events == ()
        assert state.last_refresh == ""

    def test_custom(self) -> None:
        alerts = (AlertEntry(alert_id="a1"),)
        state = MonitoringScreenState(
            active_alerts=alerts,
            last_refresh="10:30:00",
        )
        assert len(state.active_alerts) == 1
        assert state.last_refresh == "10:30:00"

    def test_frozen(self) -> None:
        state = MonitoringScreenState()
        with pytest.raises(AttributeError):
            state.last_refresh = "test"  # type: ignore[misc]

    def test_slots(self) -> None:
        state = MonitoringScreenState()
        assert not hasattr(state, "__dict__")

    def test_json_serializable(self) -> None:
        state = MonitoringScreenState(
            active_alerts=(AlertEntry(alert_id="a1"),),
            last_refresh="10:30:00",
        )
        data = asdict(state)
        serialized = json.dumps(data)
        assert "a1" in serialized


# ─── Helper function tests ──────────────────────────────────────


class TestHealthClass:
    def test_healthy(self) -> None:
        assert _health_class("healthy") == "value-healthy"

    def test_ok(self) -> None:
        assert _health_class("ok") == "value-healthy"

    def test_warning(self) -> None:
        assert _health_class("warning") == "value-warning"

    def test_degraded(self) -> None:
        assert _health_class("degraded") == "value-warning"

    def test_critical(self) -> None:
        assert _health_class("critical") == "value-critical"

    def test_error(self) -> None:
        assert _health_class("error") == "value-critical"

    def test_offline(self) -> None:
        assert _health_class("offline") == "value-offline"

    def test_unknown(self) -> None:
        assert _health_class("unknown") == "value-offline"


class TestRecoveryClass:
    def test_idle(self) -> None:
        assert _recovery_class("idle") == "value-success"

    def test_success(self) -> None:
        assert _recovery_class("success") == "value-success"

    def test_failed(self) -> None:
        assert _recovery_class("failed") == "value-failed"

    def test_unknown(self) -> None:
        assert _recovery_class("unknown") == "value-idle"


class TestAlertLevelClass:
    def test_critical(self) -> None:
        assert _alert_level_class("critical") == "alert-critical"

    def test_emergency(self) -> None:
        assert _alert_level_class("emergency") == "alert-critical"

    def test_error(self) -> None:
        assert _alert_level_class("error") == "alert-error"

    def test_warning(self) -> None:
        assert _alert_level_class("warning") == "alert-warning"

    def test_info(self) -> None:
        assert _alert_level_class("info") == "alert-info"

    def test_unknown(self) -> None:
        assert _alert_level_class("unknown") == "alert-info"


class TestEventLevelClass:
    def test_error(self) -> None:
        assert _event_level_class("error") == "event-error"

    def test_critical(self) -> None:
        assert _event_level_class("critical") == "event-error"

    def test_warning(self) -> None:
        assert _event_level_class("warning") == "event-warning"

    def test_info(self) -> None:
        assert _event_level_class("info") == "event-info"


class TestTrendClass:
    def test_up(self) -> None:
        assert _trend_class("up") == "event-warning"

    def test_increasing(self) -> None:
        assert _trend_class("increasing") == "event-warning"

    def test_down(self) -> None:
        assert _trend_class("down") == "event-info"

    def test_stable(self) -> None:
        assert _trend_class("stable") == "event-info"


class TestHistoryStatusClass:
    def test_resolved(self) -> None:
        assert _history_status_class("resolved") == "history-resolved"

    def test_acknowledged(self) -> None:
        assert _history_status_class("acknowledged") == "history-acknowledged"

    def test_new(self) -> None:
        assert _history_status_class("new") == "history-new"


# ─── Widget tests ───────────────────────────────────────────────


class TestSystemHealthWidget:
    def test_creation(self) -> None:
        w = SystemHealthWidget()
        assert w._info.overall_status == "Unknown"

    def test_render(self) -> None:
        w = SystemHealthWidget()
        assert w.render() == ""

    def test_update_data_before_compose(self) -> None:
        w = SystemHealthWidget()
        info = SystemHealthInfo(overall_status="healthy")
        w.update_data(info)
        assert w._info.overall_status == "healthy"

    def test_update_data_after_compose(self) -> None:
        w = SystemHealthWidget()
        w._title = MagicMock()
        w._overall = MagicMock()
        w._counts = MagicMock()
        w._subsystem_rows = []
        w.mount = MagicMock()
        info = SystemHealthInfo(
            overall_status="healthy",
            healthy_count=3,
            subsystems=(SubsystemHealthEntry(name="market", status="healthy"),),
        )
        w.update_data(info)
        w._overall.update.assert_called_once()
        w._counts.update.assert_called_once()

    def test_update_data_empty_subsystems(self) -> None:
        w = SystemHealthWidget()
        w._title = MagicMock()
        w._overall = MagicMock()
        w._counts = MagicMock()
        w._subsystem_rows = []
        w.mount = MagicMock()
        info = SystemHealthInfo(overall_status="healthy")
        w.update_data(info)
        w._overall.update.assert_called_once()


class TestTelemetryWidget:
    def test_creation(self) -> None:
        w = TelemetryWidget()
        assert w._info.total_metrics == 0

    def test_render(self) -> None:
        w = TelemetryWidget()
        assert w.render() == ""

    def test_update_data_before_compose(self) -> None:
        w = TelemetryWidget()
        info = TelemetryInfo(total_metrics=10)
        w.update_data(info)
        assert w._info.total_metrics == 10

    def test_update_data_after_compose(self) -> None:
        w = TelemetryWidget()
        w._title = MagicMock()
        w._metrics = MagicMock()
        w._collectors = MagicMock()
        w._collections = MagicMock()
        w._uptime = MagicMock()
        info = TelemetryInfo(
            total_metrics=10,
            active_collectors=3,
            total_collections=100,
            failed_collections=2,
            uptime="01:30:00",
        )
        w.update_data(info)
        w._metrics.update.assert_called_once()
        w._collectors.update.assert_called_once()
        w._collections.update.assert_called_once()
        w._uptime.update.assert_called_once()


class TestAlertSummaryWidget:
    def test_creation(self) -> None:
        w = AlertSummaryWidget()
        assert w._info.total == 0

    def test_render(self) -> None:
        w = AlertSummaryWidget()
        assert w.render() == ""

    def test_update_data_before_compose(self) -> None:
        w = AlertSummaryWidget()
        info = AlertSummaryInfo(total=10)
        w.update_data(info)
        assert w._info.total == 10

    def test_update_data_after_compose(self) -> None:
        w = AlertSummaryWidget()
        w._title = MagicMock()
        w._total = MagicMock()
        w._active = MagicMock()
        w._critical = MagicMock()
        w._ack = MagicMock()
        w._resolved = MagicMock()
        info = AlertSummaryInfo(total=10, active=3, critical=1)
        w.update_data(info)
        w._total.update.assert_called_once()
        w._active.update.assert_called_once()
        w._critical.update.assert_called_once()


class TestRecoveryStatusWidget:
    def test_creation(self) -> None:
        w = RecoveryStatusWidget()
        assert w._info.status == "Idle"

    def test_render(self) -> None:
        w = RecoveryStatusWidget()
        assert w.render() == ""

    def test_update_data_before_compose(self) -> None:
        w = RecoveryStatusWidget()
        info = RecoveryStatusInfo(status="success")
        w.update_data(info)
        assert w._info.status == "success"

    def test_update_data_after_compose(self) -> None:
        w = RecoveryStatusWidget()
        w._title = MagicMock()
        w._status = MagicMock()
        w._attempts = MagicMock()
        w._strategy = MagicMock()
        w._components = MagicMock()
        info = RecoveryStatusInfo(
            status="success",
            total_attempts=3,
            successful=2,
            failed=1,
            last_strategy="retry",
            recovered_components="pipeline",
        )
        w.update_data(info)
        w._status.update.assert_called_once()
        w._attempts.update.assert_called_once()


class TestMetricsWidget:
    def test_creation(self) -> None:
        w = MetricsWidget()
        assert w._metrics == ()

    def test_render(self) -> None:
        w = MetricsWidget()
        assert w.render() == ""

    def test_update_data_before_compose(self) -> None:
        w = MetricsWidget()
        info = ResourceMetricsInfo(
            metrics=(ResourceMetricEntry(name="cpu", value="45"),)
        )
        w.update_data(info)
        assert len(w._metrics) == 1

    def test_update_data_after_compose_empty(self) -> None:
        w = MetricsWidget()
        w._title = MagicMock()
        w._rows = []
        w.mount = MagicMock()
        info = ResourceMetricsInfo()
        w.update_data(info)
        assert len(w._rows) == 1
        w.mount.assert_called_once()

    def test_update_data_after_compose_with_metrics(self) -> None:
        w = MetricsWidget()
        w._title = MagicMock()
        w._rows = []
        w.mount = MagicMock()
        info = ResourceMetricsInfo(
            metrics=(
                ResourceMetricEntry(name="cpu", value="45", unit="%", trend="up"),
                ResourceMetricEntry(name="mem", value="8", unit="gb"),
            )
        )
        w.update_data(info)
        assert len(w._rows) == 2
        assert w.mount.call_count == 2

    def test_has_composed(self) -> None:
        w = MetricsWidget()
        assert not w._has_composed
        w._title = MagicMock()
        assert w._has_composed


class TestActiveAlertsWidget:
    def test_creation(self) -> None:
        w = ActiveAlertsWidget()
        assert w._alerts == ()

    def test_render(self) -> None:
        w = ActiveAlertsWidget()
        assert w.render() == ""

    def test_update_data_before_compose(self) -> None:
        w = ActiveAlertsWidget()
        alerts = (AlertEntry(alert_id="a1", level="critical"),)
        w.update_data(alerts)
        assert len(w._alerts) == 1

    def test_update_data_after_compose_empty(self) -> None:
        w = ActiveAlertsWidget()
        w._title = MagicMock()
        w._rows = []
        w.mount = MagicMock()
        w.update_data(())
        assert len(w._rows) == 1
        w.mount.assert_called_once()

    def test_update_data_after_compose_with_alerts(self) -> None:
        w = ActiveAlertsWidget()
        w._title = MagicMock()
        w._rows = []
        w.mount = MagicMock()
        alerts = (
            AlertEntry(alert_id="a1", level="critical", title="High CPU"),
            AlertEntry(alert_id="a2", level="warning", title="Slow query"),
        )
        w.update_data(alerts)
        assert len(w._rows) == 2

    def test_has_composed(self) -> None:
        w = ActiveAlertsWidget()
        assert not w._has_composed
        w._title = MagicMock()
        assert w._has_composed


class TestAlertHistoryWidget:
    def test_creation(self) -> None:
        w = AlertHistoryWidget()
        assert w._entries == ()

    def test_render(self) -> None:
        w = AlertHistoryWidget()
        assert w.render() == ""

    def test_update_data_before_compose(self) -> None:
        w = AlertHistoryWidget()
        entries = (AlertHistoryEntry(alert_id="a1", status="resolved"),)
        w.update_data(entries)
        assert len(w._entries) == 1

    def test_update_data_after_compose_empty(self) -> None:
        w = AlertHistoryWidget()
        w._title = MagicMock()
        w._rows = []
        w.mount = MagicMock()
        w.update_data(())
        assert len(w._rows) == 1
        w.mount.assert_called_once()

    def test_update_data_after_compose_with_entries(self) -> None:
        w = AlertHistoryWidget()
        w._title = MagicMock()
        w._rows = []
        w.mount = MagicMock()
        entries = (
            AlertHistoryEntry(alert_id="a1", status="resolved", title="Fixed"),
            AlertHistoryEntry(alert_id="a2", status="acknowledged", title="Seen"),
        )
        w.update_data(entries)
        assert len(w._rows) == 2

    def test_has_composed(self) -> None:
        w = AlertHistoryWidget()
        assert not w._has_composed
        w._title = MagicMock()
        assert w._has_composed


class TestMonitoringEventsWidget:
    def test_creation(self) -> None:
        w = MonitoringEventsWidget()
        assert w._events == ()

    def test_render(self) -> None:
        w = MonitoringEventsWidget()
        assert w.render() == ""

    def test_update_data_before_compose(self) -> None:
        w = MonitoringEventsWidget()
        events = (MonitoringEventEntry(level="warning", message="test"),)
        w.update_data(events)
        assert len(w._events) == 1

    def test_update_data_after_compose_empty(self) -> None:
        w = MonitoringEventsWidget()
        w._title = MagicMock()
        w._rows = []
        w.mount = MagicMock()
        w.update_data(())
        assert len(w._rows) == 1
        w.mount.assert_called_once()

    def test_update_data_after_compose_with_events(self) -> None:
        w = MonitoringEventsWidget()
        w._title = MagicMock()
        w._rows = []
        w.mount = MagicMock()
        events = (
            MonitoringEventEntry(
                level="warning", source="monitoring", message="High latency"
            ),
            MonitoringEventEntry(
                level="info", source="recovery", message="Recovery success"
            ),
        )
        w.update_data(events)
        assert len(w._rows) == 2

    def test_has_composed(self) -> None:
        w = MonitoringEventsWidget()
        assert not w._has_composed
        w._title = MagicMock()
        assert w._has_composed


# ─── Screen unit tests ──────────────────────────────────────────


class TestMonitoringScreenUnit:
    def test_creation(self) -> None:
        from titan.tui.screens.monitor import MonitoringScreen

        screen = MonitoringScreen()
        assert isinstance(screen._state, MonitoringScreenState)

    def test_set_state_builder(self) -> None:
        from titan.tui.screens.monitor import MonitoringScreen

        screen = MonitoringScreen()
        screen.set_state_builder(lambda: MonitoringScreenState())
        assert screen._state_builder is not None

    def test_refresh_state_with_builder(self) -> None:
        from titan.tui.screens.monitor import MonitoringScreen

        screen = MonitoringScreen()
        custom = MonitoringScreenState(last_refresh="10:30:00")
        screen.set_state_builder(lambda: custom)
        screen._refresh_state()
        assert screen._state.last_refresh == "10:30:00"

    def test_refresh_state_builder_exception(self) -> None:
        from titan.tui.screens.monitor import MonitoringScreen

        screen = MonitoringScreen()
        screen.set_state_builder(lambda: (_ for _ in ()).throw(RuntimeError))
        screen._refresh_state()
        assert isinstance(screen._state, MonitoringScreenState)

    def test_state_property(self) -> None:
        from titan.tui.screens.monitor import MonitoringScreen

        screen = MonitoringScreen()
        assert isinstance(screen.state, MonitoringScreenState)

    def test_bindings(self) -> None:
        from titan.tui.screens.monitor import MonitoringScreen

        keys = [b[0] for b in MonitoringScreen.BINDINGS]
        assert "r" in keys
        assert "escape" in keys
        assert "q" in keys
        assert "up" in keys
        assert "down" in keys
        assert "page_up" in keys
        assert "page_down" in keys


# ─── State builder tests ────────────────────────────────────────


class TestBuildMonitoringState:
    @patch("titan.tui.layout._read_monitoring_events")
    @patch("titan.tui.layout._read_monitoring_recovery_status")
    @patch("titan.tui.layout._read_monitoring_alert_history")
    @patch("titan.tui.layout._read_monitoring_active_alerts")
    @patch("titan.tui.layout._read_monitoring_alert_summary")
    @patch("titan.tui.layout._read_monitoring_resource_metrics")
    @patch("titan.tui.layout._read_monitoring_telemetry")
    @patch("titan.tui.layout._read_monitoring_system_health")
    def test_builds_state(
        self,
        mock_health: MagicMock,
        mock_telemetry: MagicMock,
        mock_metrics: MagicMock,
        mock_alert_summary: MagicMock,
        mock_active_alerts: MagicMock,
        mock_alert_history: MagicMock,
        mock_recovery: MagicMock,
        mock_events: MagicMock,
    ) -> None:
        from titan.tui.layout import build_monitoring_state

        mock_health.return_value = SystemHealthInfo(overall_status="healthy")
        mock_telemetry.return_value = TelemetryInfo(total_metrics=5)
        mock_metrics.return_value = ResourceMetricsInfo()
        mock_alert_summary.return_value = AlertSummaryInfo(total=3)
        mock_active_alerts.return_value = ()
        mock_alert_history.return_value = ()
        mock_recovery.return_value = RecoveryStatusInfo(status="idle")
        mock_events.return_value = ()

        state = build_monitoring_state()
        assert state.system_health.overall_status == "healthy"
        assert state.telemetry.total_metrics == 5
        assert state.alert_summary.total == 3
        assert state.recovery_status.status == "idle"
        assert state.last_refresh != ""


class TestReadMonitoringSystemHealth:
    @patch("titan.cli.common.get_monitoring_manager")
    def test_healthy(self, mock_get: MagicMock) -> None:
        from titan.tui.layout import _read_monitoring_system_health

        mon = MagicMock()
        health = MagicMock()
        health.overall.value = "healthy"
        health.healthy_count = 3
        health.warning_count = 0
        health.critical_count = 0
        health.offline_count = 0
        sub = MagicMock()
        sub.subsystem.value = "market"
        sub.status.value = "healthy"
        sub.message = "OK"
        sub.latency_ms = 1.5
        sub.failures = 0
        health.subsystems = [sub]
        mon.health.evaluate.return_value = health
        mock_get.return_value = mon

        info = _read_monitoring_system_health()
        assert info.overall_status == "healthy"
        assert info.healthy_count == 3
        assert len(info.subsystems) == 1
        assert info.subsystems[0].name == "market"

    @patch("titan.cli.common.get_monitoring_manager")
    def test_exception(self, mock_get: MagicMock) -> None:
        from titan.tui.layout import _read_monitoring_system_health

        mock_get.side_effect = RuntimeError("no manager")
        info = _read_monitoring_system_health()
        assert info.overall_status == "Unknown"


class TestReadMonitoringTelemetry:
    @patch("titan.cli.common.get_monitoring_manager")
    def test_with_data(self, mock_get: MagicMock) -> None:
        from titan.tui.layout import _read_monitoring_telemetry

        mon = MagicMock()
        mon.metrics.metric_names.return_value = ["cpu", "mem"]
        status = MagicMock()
        status.active_collectors = 3
        status.failed_collections = 1
        status.total_collections = 100
        status.uptime_seconds = 3600.0
        mon.dashboard_status.return_value = status
        mock_get.return_value = mon

        info = _read_monitoring_telemetry()
        assert info.total_metrics == 2
        assert info.active_collectors == 3
        assert info.failed_collections == 1
        assert info.uptime == "01:00:00"

    @patch("titan.cli.common.get_monitoring_manager")
    def test_exception(self, mock_get: MagicMock) -> None:
        from titan.tui.layout import _read_monitoring_telemetry

        mock_get.side_effect = RuntimeError("no manager")
        info = _read_monitoring_telemetry()
        assert info.total_metrics == 0


class TestReadMonitoringAlertSummary:
    @patch("titan.cli.common.get_alert_manager")
    def test_with_data(self, mock_get: MagicMock) -> None:
        from titan.tui.layout import _read_monitoring_alert_summary

        al = MagicMock()
        report = MagicMock()
        report.total_alerts = 10
        report.active_alerts = 3
        report.critical_alerts = 1
        report.acknowledged_alerts = 2
        report.resolved_alerts = 5
        report.escalated_alerts = 0
        al.generate_report.return_value = report
        mock_get.return_value = al

        info = _read_monitoring_alert_summary()
        assert info.total == 10
        assert info.active == 3
        assert info.critical == 1

    @patch("titan.cli.common.get_alert_manager")
    def test_exception(self, mock_get: MagicMock) -> None:
        from titan.tui.layout import _read_monitoring_alert_summary

        mock_get.side_effect = RuntimeError("no manager")
        info = _read_monitoring_alert_summary()
        assert info.total == 0


class TestReadMonitoringActiveAlerts:
    @patch("titan.cli.common.get_alert_manager")
    def test_with_data(self, mock_get: MagicMock) -> None:
        from titan.tui.layout import _read_monitoring_active_alerts

        al = MagicMock()
        alert = MagicMock()
        alert.alert_id = "a1"
        alert.level.value = "critical"
        alert.source.value = "monitoring"
        alert.title = "High CPU"
        alert.message = "CPU at 95%"
        alert.status.value = "new"
        alert.timestamp.strftime.return_value = "10:30:00"
        al.get_active_alerts.return_value = [alert]
        mock_get.return_value = al

        alerts = _read_monitoring_active_alerts()
        assert len(alerts) == 1
        assert alerts[0].alert_id == "a1"
        assert alerts[0].level == "critical"

    @patch("titan.cli.common.get_alert_manager")
    def test_exception(self, mock_get: MagicMock) -> None:
        from titan.tui.layout import _read_monitoring_active_alerts

        mock_get.side_effect = RuntimeError("no manager")
        alerts = _read_monitoring_active_alerts()
        assert alerts == ()


class TestReadMonitoringAlertHistory:
    @patch("titan.cli.common.get_alert_manager")
    def test_with_data(self, mock_get: MagicMock) -> None:
        from titan.tui.layout import _read_monitoring_alert_history

        al = MagicMock()
        entry = MagicMock()
        entry.alert.alert_id = "a1"
        entry.alert.level.value = "warning"
        entry.alert.source.value = "runtime"
        entry.alert.title = "Slow pipeline"
        entry.alert.status.value = "resolved"
        entry.alert.timestamp.strftime.return_value = "10:30:00"
        entry.alert.acknowledged_at = None
        entry.alert.resolved_at = entry.alert.timestamp
        al.history.all_entries.return_value = [entry]
        mock_get.return_value = al

        entries = _read_monitoring_alert_history()
        assert len(entries) == 1
        assert entries[0].alert_id == "a1"

    @patch("titan.cli.common.get_alert_manager")
    def test_exception(self, mock_get: MagicMock) -> None:
        from titan.tui.layout import _read_monitoring_alert_history

        mock_get.side_effect = RuntimeError("no manager")
        entries = _read_monitoring_alert_history()
        assert entries == ()


class TestReadMonitoringRecoveryStatus:
    @patch("titan.cli.common.get_recovery_manager")
    def test_with_data(self, mock_get: MagicMock) -> None:
        from titan.tui.layout import _read_monitoring_recovery_status

        rm = MagicMock()
        report = MagicMock()
        report.status.value = "idle"
        report.total_attempts = 5
        report.successful_attempts = 3
        report.failed_attempts = 2
        report.recovered_components = ("pipeline", "broker")
        rm.generate_report.return_value = report
        history = MagicMock()
        history.strategy.value = "retry"
        rm.get_recovery_history.return_value = [history]
        mock_get.return_value = rm

        info = _read_monitoring_recovery_status()
        assert info.status == "idle"
        assert info.total_attempts == 5
        assert info.last_strategy == "retry"
        assert "pipeline" in info.recovered_components

    @patch("titan.cli.common.get_recovery_manager")
    def test_exception(self, mock_get: MagicMock) -> None:
        from titan.tui.layout import _read_monitoring_recovery_status

        mock_get.side_effect = RuntimeError("no manager")
        info = _read_monitoring_recovery_status()
        assert info.status == "Idle"


class TestReadMonitoringEvents:
    @patch("titan.cli.common.get_alert_manager")
    @patch("titan.cli.common.get_recovery_manager")
    @patch("titan.cli.common.get_monitoring_manager")
    def test_with_data(
        self,
        mock_mon: MagicMock,
        mock_rm: MagicMock,
        mock_al: MagicMock,
    ) -> None:
        from titan.tui.layout import _read_monitoring_events

        mon = MagicMock()
        report = MagicMock()
        report.warnings = ("High latency",)
        report.recommendations = ("Check subsystem",)
        mon.generate_report.return_value = report
        mock_mon.return_value = mon

        rm = MagicMock()
        recovery = MagicMock()
        recovery.status.value = "success"
        recovery.failure_reason = ""
        recovery.timestamp.strftime.return_value = "10:30:00"
        rm.get_recovery_history.return_value = [recovery]
        mock_rm.return_value = rm

        al = MagicMock()
        al_report = MagicMock()
        al_report.warnings = ()
        al.generate_report.return_value = al_report
        mock_al.return_value = al

        events = _read_monitoring_events()
        assert len(events) >= 2

    @patch("titan.cli.common.get_alert_manager")
    @patch("titan.cli.common.get_recovery_manager")
    @patch("titan.cli.common.get_monitoring_manager")
    def test_exception(
        self,
        mock_mon: MagicMock,
        mock_rm: MagicMock,
        mock_al: MagicMock,
    ) -> None:
        from titan.tui.layout import _read_monitoring_events

        mock_mon.side_effect = RuntimeError("no manager")
        mock_rm.side_effect = RuntimeError("no manager")
        mock_al.side_effect = RuntimeError("no manager")
        events = _read_monitoring_events()
        assert events == ()


# ─── Async integration tests ────────────────────────────────────


class TestMonitoringScreenAsync:
    @pytest.mark.asyncio
    async def test_screen_creation(self) -> None:
        from titan.tui.screens.monitor import MonitoringScreen

        screen = MonitoringScreen()
        assert isinstance(screen._state, MonitoringScreenState)

    @pytest.mark.asyncio
    async def test_state_builder_injection(self) -> None:
        from titan.tui.screens.monitor import MonitoringScreen

        screen = MonitoringScreen()
        custom = MonitoringScreenState(last_refresh="12:00:00")
        screen.set_state_builder(lambda: custom)
        screen._refresh_state()
        assert screen._state.last_refresh == "12:00:00"

    @pytest.mark.asyncio
    async def test_widgets_are_none_before_mount(self) -> None:
        from titan.tui.screens.monitor import MonitoringScreen

        screen = MonitoringScreen()
        assert screen._system_health_widget is None
        assert screen._telemetry_widget is None
        assert screen._alert_summary_widget is None
        assert screen._recovery_status_widget is None
        assert screen._metrics_widget is None
        assert screen._active_alerts_widget is None
        assert screen._alert_history_widget is None
        assert screen._monitoring_events_widget is None

    @pytest.mark.asyncio
    async def test_empty_state_render(self) -> None:
        from titan.tui.screens.monitor import MonitoringScreen

        screen = MonitoringScreen()
        state = MonitoringScreenState()
        screen._state = state
        assert screen.state.system_health.overall_status == "Unknown"
        assert screen.state.telemetry.total_metrics == 0
        assert screen.state.alert_summary.total == 0


# ─── Empty state tests ──────────────────────────────────────────


class TestEmptyState:
    def test_all_defaults_produce_safe_state(self) -> None:
        state = MonitoringScreenState()
        assert state.system_health.overall_status == "Unknown"
        assert state.telemetry.total_metrics == 0
        assert state.resource_metrics.metrics == ()
        assert state.alert_summary.total == 0
        assert state.active_alerts == ()
        assert state.alert_history == ()
        assert state.recovery_status.status == "Idle"
        assert state.monitoring_events == ()
        assert state.last_refresh == ""

    def test_widget_default_construction(self) -> None:
        widgets = [
            SystemHealthWidget(),
            TelemetryWidget(),
            AlertSummaryWidget(),
            RecoveryStatusWidget(),
            MetricsWidget(),
            ActiveAlertsWidget(),
            AlertHistoryWidget(),
            MonitoringEventsWidget(),
        ]
        for w in widgets:
            assert w.render() == ""


# ─── Populated state tests ──────────────────────────────────────


class TestPopulatedState:
    def test_full_state_construction(self) -> None:
        state = MonitoringScreenState(
            system_health=SystemHealthInfo(
                overall_status="healthy",
                healthy_count=5,
                subsystems=(
                    SubsystemHealthEntry(name="market", status="healthy"),
                    SubsystemHealthEntry(name="broker", status="warning"),
                ),
            ),
            telemetry=TelemetryInfo(
                total_metrics=10,
                active_collectors=3,
                uptime="02:00:00",
            ),
            resource_metrics=ResourceMetricsInfo(
                metrics=(
                    ResourceMetricEntry(name="cpu", value="45", unit="%"),
                    ResourceMetricEntry(name="mem", value="8", unit="gb"),
                ),
            ),
            alert_summary=AlertSummaryInfo(total=5, active=2, critical=1),
            active_alerts=(
                AlertEntry(alert_id="a1", level="critical", title="High CPU"),
                AlertEntry(alert_id="a2", level="warning", title="Slow query"),
            ),
            alert_history=(
                AlertHistoryEntry(alert_id="a3", status="resolved", title="Fixed"),
            ),
            recovery_status=RecoveryStatusInfo(
                status="success",
                total_attempts=3,
                successful=2,
            ),
            monitoring_events=(
                MonitoringEventEntry(level="warning", message="High latency"),
            ),
            last_refresh="10:30:00",
        )
        assert state.system_health.overall_status == "healthy"
        assert state.telemetry.total_metrics == 10
        assert len(state.resource_metrics.metrics) == 2
        assert state.alert_summary.total == 5
        assert len(state.active_alerts) == 2
        assert len(state.alert_history) == 1
        assert state.recovery_status.status == "success"
        assert len(state.monitoring_events) == 1
        assert state.last_refresh == "10:30:00"


# ─── JSON serialization tests ───────────────────────────────────


class TestJsonSerialization:
    def test_system_health_round_trip(self) -> None:
        info = SystemHealthInfo(
            overall_status="healthy",
            healthy_count=3,
            subsystems=(SubsystemHealthEntry(name="market"),),
        )
        data = asdict(info)
        serialized = json.dumps(data)
        deserialized = json.loads(serialized)
        assert deserialized["overall_status"] == "healthy"
        assert deserialized["healthy_count"] == 3

    def test_alert_summary_round_trip(self) -> None:
        info = AlertSummaryInfo(total=10, active=3, critical=1)
        data = asdict(info)
        serialized = json.dumps(data)
        deserialized = json.loads(serialized)
        assert deserialized["total"] == 10
        assert deserialized["critical"] == 1

    def test_recovery_status_round_trip(self) -> None:
        info = RecoveryStatusInfo(status="success", total_attempts=5)
        data = asdict(info)
        serialized = json.dumps(data)
        deserialized = json.loads(serialized)
        assert deserialized["status"] == "success"

    def test_full_state_round_trip(self) -> None:
        state = MonitoringScreenState(
            active_alerts=(AlertEntry(alert_id="a1"),),
            last_refresh="10:30:00",
        )
        data = asdict(state)
        serialized = json.dumps(data)
        deserialized = json.loads(serialized)
        assert deserialized["last_refresh"] == "10:30:00"
        assert len(deserialized["active_alerts"]) == 1


# ─── Error handling tests ───────────────────────────────────────


class TestErrorHandling:
    def test_builder_exception_returns_default(self) -> None:
        from titan.tui.screens.monitor import MonitoringScreen

        screen = MonitoringScreen()
        screen.set_state_builder(lambda: (_ for _ in ()).throw(RuntimeError))
        screen._refresh_state()
        assert isinstance(screen._state, MonitoringScreenState)
        assert screen._state.last_refresh == ""

    def test_widget_update_before_compose_no_crash(self) -> None:
        widgets_data = [
            (SystemHealthWidget(), SystemHealthInfo()),
            (TelemetryWidget(), TelemetryInfo()),
            (AlertSummaryWidget(), AlertSummaryInfo()),
            (RecoveryStatusWidget(), RecoveryStatusInfo()),
            (MetricsWidget(), ResourceMetricsInfo()),
            (ActiveAlertsWidget(), ()),
            (AlertHistoryWidget(), ()),
            (MonitoringEventsWidget(), ()),
        ]
        for widget, data in widgets_data:
            widget.update_data(data)

    def test_all_readers_handle_exceptions(self) -> None:
        from titan.tui.layout import (
            _read_monitoring_active_alerts,
            _read_monitoring_alert_history,
            _read_monitoring_alert_summary,
            _read_monitoring_events,
            _read_monitoring_recovery_status,
            _read_monitoring_resource_metrics,
            _read_monitoring_system_health,
            _read_monitoring_telemetry,
        )

        readers = [
            _read_monitoring_system_health,
            _read_monitoring_telemetry,
            _read_monitoring_resource_metrics,
            _read_monitoring_alert_summary,
            _read_monitoring_active_alerts,
            _read_monitoring_alert_history,
            _read_monitoring_recovery_status,
            _read_monitoring_events,
        ]
        for reader in readers:
            result = reader()
            assert result is not None
