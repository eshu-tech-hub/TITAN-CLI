"""CLI integration tests for TITAN monitoring and alerting commands."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from titan.cli import app
from titan.cli.commands.monitor import _reset_monitor_session
from titan.cli.common import get_alert_manager, reset_alert_manager

runner = CliRunner()


def _extract_json(output: str) -> dict:
    """Extract JSON from CLI output that may contain loguru lines."""
    for line in output.strip().splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                pass
    lines = output.strip().splitlines()
    json_lines = []
    in_json = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("{") and not in_json:
            in_json = True
        if in_json:
            json_lines.append(line)
    if json_lines:
        return json.loads("\n".join(json_lines), strict=False)
    return json.loads(output, strict=False)


def _extract_json_list(output: str) -> list:
    """Extract JSON array from CLI output."""
    for line in output.strip().splitlines():
        line = line.strip()
        if line.startswith("["):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                pass
    lines = output.strip().splitlines()
    json_lines = []
    in_json = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and not in_json:
            in_json = True
        if in_json:
            json_lines.append(line)
    if json_lines:
        return json.loads("\n".join(json_lines), strict=False)
    return json.loads(output, strict=False)


class TestMonitorCommands:
    def setup_method(self) -> None:
        _reset_monitor_session()

    def test_monitor_help(self) -> None:
        result = runner.invoke(app, ["monitor", "--help"])
        assert result.exit_code == 0
        assert "Monitoring" in result.output
        assert "start" in result.output
        assert "stop" in result.output
        assert "restart" in result.output
        assert "status" in result.output
        assert "metrics" in result.output
        assert "dashboard" in result.output

    def test_monitor_status(self) -> None:
        result = runner.invoke(app, ["monitor", "status"])
        assert result.exit_code == 0
        assert "Monitoring Subsystem" in result.output

    def test_monitor_status_json(self) -> None:
        result = runner.invoke(app, ["monitor", "status", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert "running" in data
        assert "collector_count" in data
        assert "total_collections" in data
        assert "failed_collections" in data

    def test_monitor_status_verbose(self) -> None:
        result = runner.invoke(app, ["monitor", "status", "--verbose"])
        assert result.exit_code == 0
        assert "Monitoring Subsystem" in result.output

    def test_monitor_start(self) -> None:
        result = runner.invoke(app, ["monitor", "start"])
        assert result.exit_code == 0
        assert "started" in result.output.lower()

    def test_monitor_start_verbose(self) -> None:
        result = runner.invoke(app, ["monitor", "start", "--verbose"])
        assert result.exit_code == 0
        assert "started" in result.output.lower()

    def test_monitor_start_already_running(self) -> None:
        result = runner.invoke(app, ["monitor", "start"])
        assert result.exit_code == 0
        result = runner.invoke(app, ["monitor", "start"])
        assert result.exit_code == 0
        assert "already running" in result.output.lower()

    def test_monitor_stop(self) -> None:
        result = runner.invoke(app, ["monitor", "start"])
        assert result.exit_code == 0
        result = runner.invoke(app, ["monitor", "stop"])
        assert result.exit_code == 0
        assert "stopped" in result.output.lower()

    def test_monitor_stop_when_not_running(self) -> None:
        result = runner.invoke(app, ["monitor", "stop"])
        assert result.exit_code == 0
        assert "not running" in result.output.lower()

    def test_monitor_stop_verbose(self) -> None:
        result = runner.invoke(app, ["monitor", "start"])
        assert result.exit_code == 0
        result = runner.invoke(app, ["monitor", "stop", "--verbose"])
        assert result.exit_code == 0
        assert "stopped" in result.output.lower()

    def test_monitor_restart(self) -> None:
        result = runner.invoke(app, ["monitor", "restart"])
        assert result.exit_code == 0
        assert "started" in result.output.lower()

    def test_monitor_restart_verbose(self) -> None:
        result = runner.invoke(app, ["monitor", "restart", "--verbose"])
        assert result.exit_code == 0
        assert "started" in result.output.lower()

    def test_monitor_metrics(self) -> None:
        result = runner.invoke(app, ["monitor", "metrics"])
        assert result.exit_code == 0

    def test_monitor_metrics_json(self) -> None:
        result = runner.invoke(app, ["monitor", "metrics", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert "metric_count" in data
        assert "metrics" in data
        assert "snapshot_timestamp" in data

    def test_monitor_dashboard(self) -> None:
        result = runner.invoke(app, ["monitor", "dashboard"])
        assert result.exit_code == 0

    def test_monitor_dashboard_json(self) -> None:
        result = runner.invoke(app, ["monitor", "dashboard", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert "uptime_seconds" in data
        assert "active_collectors" in data
        assert "metric_summaries" in data

    def test_monitor_dashboard_verbose(self) -> None:
        result = runner.invoke(app, ["monitor", "dashboard", "--verbose"])
        assert result.exit_code == 0

    def test_monitor_start_stop_lifecycle(self) -> None:
        result = runner.invoke(app, ["monitor", "start"])
        assert result.exit_code == 0
        assert "started" in result.output.lower()

        result = runner.invoke(app, ["monitor", "status"])
        assert result.exit_code == 0
        assert "running" in result.output.lower()

        result = runner.invoke(app, ["monitor", "stop"])
        assert result.exit_code == 0
        assert "stopped" in result.output.lower()

        result = runner.invoke(app, ["monitor", "status"])
        assert result.exit_code == 0
        assert "not running" in result.output.lower()

    def test_monitor_status_json_after_start(self) -> None:
        result = runner.invoke(app, ["monitor", "start"])
        assert result.exit_code == 0

        result = runner.invoke(app, ["monitor", "status", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert data["running"] is True

    def test_monitor_dashboard_json_after_start(self) -> None:
        result = runner.invoke(app, ["monitor", "start"])
        assert result.exit_code == 0

        result = runner.invoke(app, ["monitor", "dashboard", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert "metric_summaries" in data


class TestAlertCommands:
    def setup_method(self) -> None:
        reset_alert_manager()

    def test_alert_help(self) -> None:
        result = runner.invoke(app, ["alert", "--help"])
        assert result.exit_code == 0
        assert "Alerting" in result.output
        assert "status" in result.output
        assert "active" in result.output
        assert "history" in result.output
        assert "acknowledge" in result.output
        assert "resolve" in result.output
        assert "rules" in result.output

    def test_alert_status(self) -> None:
        result = runner.invoke(app, ["alert", "status"])
        assert result.exit_code == 0
        assert "Alerting Subsystem" in result.output

    def test_alert_status_json(self) -> None:
        result = runner.invoke(app, ["alert", "status", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert "report" in data
        assert "channels" in data
        assert "active_count" in data

    def test_alert_status_verbose(self) -> None:
        result = runner.invoke(app, ["alert", "status", "--verbose"])
        assert result.exit_code == 0
        assert "Alerting Subsystem" in result.output

    def test_alert_active_empty(self) -> None:
        result = runner.invoke(app, ["alert", "active"])
        assert result.exit_code == 0
        assert "No active alerts" in result.output

    def test_alert_active_json_empty(self) -> None:
        result = runner.invoke(app, ["alert", "active", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert data["count"] == 0

    def test_alert_history_empty(self) -> None:
        result = runner.invoke(app, ["alert", "history"])
        assert result.exit_code == 0
        assert "No alert history" in result.output

    def test_alert_history_json_empty(self) -> None:
        result = runner.invoke(app, ["alert", "history", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert data["total_count"] == 0

    def test_alert_rules_empty(self) -> None:
        result = runner.invoke(app, ["alert", "rules"])
        assert result.exit_code == 0
        assert "No alert rules" in result.output

    def test_alert_rules_json_empty(self) -> None:
        result = runner.invoke(app, ["alert", "rules", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert data["count"] == 0

    def test_alert_acknowledge_not_found(self) -> None:
        result = runner.invoke(app, ["alert", "acknowledge", "alert:999:2024-01-01"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_alert_resolve_not_found(self) -> None:
        result = runner.invoke(app, ["alert", "resolve", "alert:999:2024-01-01"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_alert_fire_and_active(self) -> None:
        from titan.alerting.models import AlertLevel, AlertSource

        mgr = get_alert_manager()
        mgr.fire(
            level=AlertLevel.WARNING,
            source=AlertSource.RUNTIME,
            title="Test Alert",
            message="This is a test",
        )

        result = runner.invoke(app, ["alert", "active"])
        assert result.exit_code == 0
        assert "Test Alert" in result.output

        result = runner.invoke(app, ["alert", "active", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert data["count"] >= 1

    def test_alert_fire_and_acknowledge(self) -> None:
        from titan.alerting.models import AlertLevel, AlertSource

        mgr = get_alert_manager()
        alert = mgr.fire(
            level=AlertLevel.ERROR,
            source=AlertSource.BROKER,
            title="Broker Error",
            message="Connection lost",
        )

        result = runner.invoke(app, ["alert", "acknowledge", alert.alert_id])
        assert result.exit_code == 0
        assert "acknowledged" in result.output.lower()

    def test_alert_fire_and_resolve(self) -> None:
        from titan.alerting.models import AlertLevel, AlertSource

        mgr = get_alert_manager()
        alert = mgr.fire(
            level=AlertLevel.CRITICAL,
            source=AlertSource.PIPELINE,
            title="Pipeline Failed",
            message="Fatal error",
        )

        result = runner.invoke(app, ["alert", "resolve", alert.alert_id])
        assert result.exit_code == 0
        assert "resolved" in result.output.lower()

    def test_alert_acknowledge_already_resolved(self) -> None:
        from titan.alerting.models import AlertLevel, AlertSource

        mgr = get_alert_manager()
        alert = mgr.fire(
            level=AlertLevel.WARNING,
            source=AlertSource.SYSTEM,
            title="Already Resolved",
            message="test",
        )
        mgr.resolve(alert.alert_id)

        result = runner.invoke(app, ["alert", "acknowledge", alert.alert_id])
        assert result.exit_code == 0
        assert "already resolved" in result.output.lower()

    def test_alert_resolve_already_resolved(self) -> None:
        from titan.alerting.models import AlertLevel, AlertSource

        mgr = get_alert_manager()
        alert = mgr.fire(
            level=AlertLevel.WARNING,
            source=AlertSource.SYSTEM,
            title="Already Resolved",
            message="test",
        )
        mgr.resolve(alert.alert_id)

        result = runner.invoke(app, ["alert", "resolve", alert.alert_id])
        assert result.exit_code == 0
        assert "already resolved" in result.output.lower()

    def test_alert_acknowledge_json(self) -> None:
        from titan.alerting.models import AlertLevel, AlertSource

        mgr = get_alert_manager()
        alert = mgr.fire(
            level=AlertLevel.WARNING,
            source=AlertSource.SYSTEM,
            title="JSON Ack Test",
            message="test",
        )

        result = runner.invoke(app, ["alert", "acknowledge", alert.alert_id, "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert data["status"] == "acknowledged"

    def test_alert_resolve_json(self) -> None:
        from titan.alerting.models import AlertLevel, AlertSource

        mgr = get_alert_manager()
        alert = mgr.fire(
            level=AlertLevel.WARNING,
            source=AlertSource.SYSTEM,
            title="JSON Resolve Test",
            message="test",
        )

        result = runner.invoke(app, ["alert", "resolve", alert.alert_id, "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert data["status"] == "resolved"

    def test_alert_acknowledge_with_by(self) -> None:
        from titan.alerting.models import AlertLevel, AlertSource

        mgr = get_alert_manager()
        alert = mgr.fire(
            level=AlertLevel.WARNING,
            source=AlertSource.SYSTEM,
            title="Ack By Test",
            message="test",
        )

        result = runner.invoke(
            app, ["alert", "acknowledge", alert.alert_id, "--by", "admin"]
        )
        assert result.exit_code == 0
        assert "acknowledged" in result.output.lower()

    def test_alert_resolve_with_by(self) -> None:
        from titan.alerting.models import AlertLevel, AlertSource

        mgr = get_alert_manager()
        alert = mgr.fire(
            level=AlertLevel.WARNING,
            source=AlertSource.SYSTEM,
            title="Resolve By Test",
            message="test",
        )

        result = runner.invoke(app, ["alert", "resolve", alert.alert_id, "--by", "ops"])
        assert result.exit_code == 0
        assert "resolved" in result.output.lower()

    def test_alert_fire_multiple_and_history(self) -> None:
        from titan.alerting.models import AlertLevel, AlertSource

        mgr = get_alert_manager()
        mgr.fire(
            level=AlertLevel.WARNING,
            source=AlertSource.RUNTIME,
            title="Alert 1",
            message="First",
        )
        mgr.fire(
            level=AlertLevel.ERROR,
            source=AlertSource.BROKER,
            title="Alert 2",
            message="Second",
        )

        result = runner.invoke(app, ["alert", "history"])
        assert result.exit_code == 0
        assert "Alert 1" in result.output
        assert "Alert 2" in result.output

    def test_alert_history_json_with_data(self) -> None:
        from titan.alerting.models import AlertLevel, AlertSource

        mgr = get_alert_manager()
        mgr.fire(
            level=AlertLevel.WARNING,
            source=AlertSource.RUNTIME,
            title="History JSON Test",
            message="test",
        )

        result = runner.invoke(app, ["alert", "history", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert data["total_count"] >= 1

    def test_alert_history_limit(self) -> None:
        from titan.alerting.models import AlertLevel, AlertSource

        mgr = get_alert_manager()
        for i in range(5):
            mgr.fire(
                level=AlertLevel.WARNING,
                source=AlertSource.RUNTIME,
                title=f"Alert {i}",
                message=f"msg {i}",
            )

        result = runner.invoke(app, ["alert", "history", "--limit", "3"])
        assert result.exit_code == 0
        assert "showing 3" in result.output

    def test_alert_status_json_with_alerts(self) -> None:
        from titan.alerting.models import AlertLevel, AlertSource

        mgr = get_alert_manager()
        mgr.fire(
            level=AlertLevel.CRITICAL,
            source=AlertSource.MONITORING,
            title="Critical Test",
            message="critical alert",
        )

        result = runner.invoke(app, ["alert", "status", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert data["report"]["total_alerts"] >= 1
        assert data["report"]["critical_alerts"] >= 1

    def test_alert_status_verbose_with_alerts(self) -> None:
        from titan.alerting.models import AlertLevel, AlertSource

        mgr = get_alert_manager()
        mgr.fire(
            level=AlertLevel.WARNING,
            source=AlertSource.RUNTIME,
            title="Verbose Test",
            message="test",
        )

        result = runner.invoke(app, ["alert", "status", "--verbose"])
        assert result.exit_code == 0
        assert "Alerting Subsystem" in result.output

    def test_alert_active_multiple(self) -> None:
        from titan.alerting.models import AlertLevel, AlertSource

        mgr = get_alert_manager()
        mgr.fire(
            level=AlertLevel.WARNING,
            source=AlertSource.RUNTIME,
            title="Active 1",
            message="first",
        )
        mgr.fire(
            level=AlertLevel.ERROR,
            source=AlertSource.BROKER,
            title="Active 2",
            message="second",
        )

        result = runner.invoke(app, ["alert", "active"])
        assert result.exit_code == 0
        assert "2 active" in result.output

    def test_alert_active_after_resolve(self) -> None:
        from titan.alerting.models import AlertLevel, AlertSource

        mgr = get_alert_manager()
        a1 = mgr.fire(
            level=AlertLevel.WARNING,
            source=AlertSource.RUNTIME,
            title="Will Resolve",
            message="test",
        )
        mgr.fire(
            level=AlertLevel.WARNING,
            source=AlertSource.RUNTIME,
            title="Stays Active",
            message="test",
        )
        mgr.resolve(a1.alert_id)

        result = runner.invoke(app, ["alert", "active"])
        assert result.exit_code == 0
        assert "Stays Active" in result.output
        assert "1 active" in result.output

    def test_alert_fire_and_rules(self) -> None:
        from titan.alerting.models import AlertLevel, AlertSource

        mgr = get_alert_manager()
        mgr.fire(
            level=AlertLevel.WARNING,
            source=AlertSource.RUNTIME,
            title="Rule Test",
            message="test",
        )

        result = runner.invoke(app, ["alert", "rules"])
        assert result.exit_code == 0

    def test_alert_root_help_shows_alert(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "alert" in result.output
