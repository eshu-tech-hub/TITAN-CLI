"""CLI integration tests for TITAN live trading commands."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from titan.cli import app
from titan.cli.commands.live import _reset_live_session

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


class TestLiveHelp:
    def test_live_help_shows_all_commands(self) -> None:
        result = runner.invoke(app, ["live", "--help"])
        assert result.exit_code == 0
        assert "Live trading" in result.output
        assert "start" in result.output
        assert "stop" in result.output
        assert "restart" in result.output
        assert "status" in result.output
        assert "pause" in result.output
        assert "resume" in result.output
        assert "positions" in result.output
        assert "orders" in result.output
        assert "exposure" in result.output
        assert "health" in result.output
        assert "report" in result.output

    def test_live_root_help_shows_live(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "live" in result.output


class TestLiveStatus:
    def setup_method(self) -> None:
        _reset_live_session()

    def test_live_status(self) -> None:
        result = runner.invoke(app, ["live", "status"])
        assert result.exit_code == 0
        assert "Live Trading" in result.output

    def test_live_status_json(self) -> None:
        result = runner.invoke(app, ["live", "status", "--json"])
        assert result.exit_code == 0
        assert "broker_provider" in result.output
        assert "runtime_status" in result.output
        assert "deployment_status" in result.output

    def test_live_status_verbose(self) -> None:
        result = runner.invoke(app, ["live", "status", "--verbose"])
        assert result.exit_code == 0
        assert "Live Trading" in result.output

    def test_live_status_json_data(self) -> None:
        result = runner.invoke(app, ["live", "status", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert "broker_provider" in data
        assert "environment" in data
        assert "runtime_status" in data
        assert isinstance(data["runtime_uptime_seconds"], (int, float))


class TestLiveStart:
    def setup_method(self) -> None:
        _reset_live_session()

    def test_live_start_dry_run(self) -> None:
        result = runner.invoke(app, ["live", "start", "--dry-run"])
        assert result.exit_code == 0
        assert "Startup Checklist" in result.output
        assert "Dry run passed" in result.output

    def test_live_start_dry_run_verbose(self) -> None:
        result = runner.invoke(app, ["live", "start", "--dry-run", "--verbose"])
        assert result.exit_code == 0
        assert "Startup Checklist" in result.output
        assert "Configuration loaded" in result.output

    def test_live_start(self) -> None:
        result = runner.invoke(app, ["live", "start"])
        assert result.exit_code == 0
        assert (
            "started" in result.output.lower()
            or "live trading started" in result.output.lower()
        )

    def test_live_start_verbose(self) -> None:
        result = runner.invoke(app, ["live", "start", "--verbose"])
        assert result.exit_code == 0
        assert "Startup Checklist" in result.output


class TestLiveStop:
    def setup_method(self) -> None:
        _reset_live_session()

    def test_live_stop_when_not_running(self) -> None:
        result = runner.invoke(app, ["live", "stop"])
        assert result.exit_code == 0
        assert (
            "not running" in result.output.lower() or "stopped" in result.output.lower()
        )

    def test_live_stop_verbose_when_not_running(self) -> None:
        result = runner.invoke(app, ["live", "stop", "--verbose"])
        assert result.exit_code == 0


class TestLiveRestart:
    def setup_method(self) -> None:
        _reset_live_session()

    def test_live_restart(self) -> None:
        result = runner.invoke(app, ["live", "restart"])
        assert result.exit_code == 0
        assert (
            "started" in result.output.lower()
            or "live trading started" in result.output.lower()
        )


class TestLivePause:
    def setup_method(self) -> None:
        _reset_live_session()

    def test_live_pause_when_not_running(self) -> None:
        result = runner.invoke(app, ["live", "pause"])
        assert result.exit_code == 0
        assert "not running" in result.output.lower()

    def test_live_pause_json_when_not_running(self) -> None:
        result = runner.invoke(app, ["live", "pause", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert data["paused"] is False

    def test_live_pause_verbose_when_not_running(self) -> None:
        result = runner.invoke(app, ["live", "pause", "--verbose"])
        assert result.exit_code == 0


class TestLiveResume:
    def setup_method(self) -> None:
        _reset_live_session()

    def test_live_resume_when_not_running(self) -> None:
        result = runner.invoke(app, ["live", "resume"])
        assert result.exit_code == 0
        assert "not running" in result.output.lower()

    def test_live_resume_json_when_not_running(self) -> None:
        result = runner.invoke(app, ["live", "resume", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert data["resumed"] is False

    def test_live_resume_verbose_when_not_running(self) -> None:
        result = runner.invoke(app, ["live", "resume", "--verbose"])
        assert result.exit_code == 0


class TestLivePauseResumeCycle:
    def setup_method(self) -> None:
        _reset_live_session()

    def test_live_pause_when_not_paused(self) -> None:
        runner.invoke(app, ["live", "start"])
        result = runner.invoke(app, ["live", "pause"])
        assert result.exit_code == 0

    def test_live_resume_when_not_paused(self) -> None:
        runner.invoke(app, ["live", "start"])
        result = runner.invoke(app, ["live", "resume"])
        assert result.exit_code == 0
        assert "not paused" in result.output.lower()

    def test_live_resume_json_when_not_paused(self) -> None:
        runner.invoke(app, ["live", "start"])
        result = runner.invoke(app, ["live", "resume", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert data["resumed"] is False


class TestLivePositions:
    def setup_method(self) -> None:
        _reset_live_session()

    def test_live_positions_no_broker(self) -> None:
        result = runner.invoke(app, ["live", "positions"])
        assert result.exit_code == 0
        assert (
            "no broker connected" in result.output.lower()
            or "no open positions" in result.output.lower()
        )

    def test_live_positions_json_no_broker(self) -> None:
        result = runner.invoke(app, ["live", "positions", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert "positions" in data
        assert data["count"] == 0

    def test_live_positions_verbose_no_broker(self) -> None:
        result = runner.invoke(app, ["live", "positions", "--verbose"])
        assert result.exit_code == 0

    def test_live_positions_after_start(self) -> None:
        runner.invoke(app, ["live", "start"])
        result = runner.invoke(app, ["live", "positions"])
        assert result.exit_code == 0
        assert (
            "no open positions" in result.output.lower()
            or "position" in result.output.lower()
        )

    def test_live_positions_json_after_start(self) -> None:
        runner.invoke(app, ["live", "start"])
        result = runner.invoke(app, ["live", "positions", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert "positions" in data
        assert "count" in data


class TestLiveOrders:
    def setup_method(self) -> None:
        _reset_live_session()

    def test_live_orders_no_broker(self) -> None:
        result = runner.invoke(app, ["live", "orders"])
        assert result.exit_code == 0
        assert (
            "no broker connected" in result.output.lower()
            or "no orders" in result.output.lower()
        )

    def test_live_orders_json_no_broker(self) -> None:
        result = runner.invoke(app, ["live", "orders", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert "orders" in data
        assert data["count"] == 0

    def test_live_orders_verbose_no_broker(self) -> None:
        result = runner.invoke(app, ["live", "orders", "--verbose"])
        assert result.exit_code == 0

    def test_live_orders_after_start(self) -> None:
        runner.invoke(app, ["live", "start"])
        result = runner.invoke(app, ["live", "orders"])
        assert result.exit_code == 0
        assert "no orders" in result.output.lower() or "order" in result.output.lower()

    def test_live_orders_json_after_start(self) -> None:
        runner.invoke(app, ["live", "start"])
        result = runner.invoke(app, ["live", "orders", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert "orders" in data
        assert "count" in data

    def test_live_orders_status_filter(self) -> None:
        runner.invoke(app, ["live", "start"])
        result = runner.invoke(app, ["live", "orders", "--status", "FILLED"])
        assert result.exit_code == 0


class TestLiveExposure:
    def setup_method(self) -> None:
        _reset_live_session()

    def test_live_exposure_no_broker(self) -> None:
        result = runner.invoke(app, ["live", "exposure"])
        assert result.exit_code == 0
        assert (
            "no broker connected" in result.output.lower()
            or "funds" in result.output.lower()
        )

    def test_live_exposure_json_no_broker(self) -> None:
        result = runner.invoke(app, ["live", "exposure", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert "funds" in data
        assert "margin" in data

    def test_live_exposure_verbose_no_broker(self) -> None:
        result = runner.invoke(app, ["live", "exposure", "--verbose"])
        assert result.exit_code == 0

    def test_live_exposure_after_start(self) -> None:
        runner.invoke(app, ["live", "start"])
        result = runner.invoke(app, ["live", "exposure"])
        assert result.exit_code == 0

    def test_live_exposure_json_after_start(self) -> None:
        runner.invoke(app, ["live", "start"])
        result = runner.invoke(app, ["live", "exposure", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert "has_broker" in data


class TestLiveHealth:
    def setup_method(self) -> None:
        _reset_live_session()

    def test_live_health_when_not_running(self) -> None:
        result = runner.invoke(app, ["live", "health"])
        assert result.exit_code == 0
        assert "not running" in result.output.lower()

    def test_live_health_json_when_not_running(self) -> None:
        result = runner.invoke(app, ["live", "health", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert "engine" in data
        assert "monitoring" in data
        assert "recovery" in data
        assert "alerts" in data

    def test_live_health_verbose_when_not_running(self) -> None:
        result = runner.invoke(app, ["live", "health", "--verbose"])
        assert result.exit_code == 0

    def test_live_health_after_start(self) -> None:
        runner.invoke(app, ["live", "start"])
        result = runner.invoke(app, ["live", "health"])
        assert result.exit_code == 0
        assert (
            "system health" in result.output.lower()
            or "runtime" in result.output.lower()
        )

    def test_live_health_json_after_start(self) -> None:
        runner.invoke(app, ["live", "start"])
        result = runner.invoke(app, ["live", "health", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert "engine" in data
        assert "runtime_status" in data["engine"]

    def test_live_health_verbose_after_start(self) -> None:
        runner.invoke(app, ["live", "start"])
        result = runner.invoke(app, ["live", "health", "--verbose"])
        assert result.exit_code == 0
        assert (
            "system health" in result.output.lower()
            or "runtime" in result.output.lower()
        )


class TestLiveReport:
    def setup_method(self) -> None:
        _reset_live_session()

    def test_live_report_when_not_running(self) -> None:
        result = runner.invoke(app, ["live", "report"])
        assert result.exit_code == 0
        assert "Live Trading Report" in result.output

    def test_live_report_json_when_not_running(self) -> None:
        result = runner.invoke(app, ["live", "report", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert "runtime" in data
        assert "deployment" in data
        assert "positions" in data
        assert "orders" in data

    def test_live_report_verbose_when_not_running(self) -> None:
        result = runner.invoke(app, ["live", "report", "--verbose"])
        assert result.exit_code == 0

    def test_live_report_after_start(self) -> None:
        runner.invoke(app, ["live", "start"])
        result = runner.invoke(app, ["live", "report"])
        assert result.exit_code == 0
        assert "Live Trading Report" in result.output

    def test_live_report_json_after_start(self) -> None:
        runner.invoke(app, ["live", "start"])
        result = runner.invoke(app, ["live", "report", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert "runtime" in data
        assert "monitoring" in data
        assert "recovery" in data
        assert "audit" in data

    def test_live_report_verbose_after_start(self) -> None:
        runner.invoke(app, ["live", "start"])
        result = runner.invoke(app, ["live", "report", "--verbose"])
        assert result.exit_code == 0

    def test_live_report_json_data_after_start(self) -> None:
        runner.invoke(app, ["live", "start"])
        result = runner.invoke(app, ["live", "report", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        rt = data["runtime"]
        assert "status" in rt
        assert "uptime_seconds" in rt
        assert "broker_status" in rt
        assert "pipeline_executions" in rt


class TestLiveExitCodes:
    def setup_method(self) -> None:
        _reset_live_session()

    def test_live_invalid_command(self) -> None:
        result = runner.invoke(app, ["live", "nonexistent"])
        assert result.exit_code != 0

    def test_live_help_flag(self) -> None:
        result = runner.invoke(app, ["live", "--help"])
        assert result.exit_code == 0


class TestLiveLifecycle:
    def setup_method(self) -> None:
        _reset_live_session()

    def test_live_full_lifecycle(self) -> None:
        result = runner.invoke(app, ["live", "start"])
        assert result.exit_code == 0

        result = runner.invoke(app, ["live", "status"])
        assert result.exit_code == 0
        assert "Live Trading" in result.output

        result = runner.invoke(app, ["live", "stop"])
        assert result.exit_code == 0

        result = runner.invoke(app, ["live", "status"])
        assert result.exit_code == 0

    def test_live_start_stop_start_lifecycle(self) -> None:
        runner.invoke(app, ["live", "start"])
        runner.invoke(app, ["live", "stop"])
        result = runner.invoke(app, ["live", "start"])
        assert result.exit_code == 0
        assert "started" in result.output.lower()

    def test_live_positions_after_start_stop(self) -> None:
        runner.invoke(app, ["live", "start"])
        runner.invoke(app, ["live", "stop"])
        result = runner.invoke(app, ["live", "positions"])
        assert result.exit_code == 0

    def test_live_orders_after_start_stop(self) -> None:
        runner.invoke(app, ["live", "start"])
        runner.invoke(app, ["live", "stop"])
        result = runner.invoke(app, ["live", "orders"])
        assert result.exit_code == 0

    def test_live_health_after_start_stop(self) -> None:
        runner.invoke(app, ["live", "start"])
        runner.invoke(app, ["live", "stop"])
        result = runner.invoke(app, ["live", "health"])
        assert result.exit_code == 0

    def test_live_report_after_start_stop(self) -> None:
        runner.invoke(app, ["live", "start"])
        runner.invoke(app, ["live", "stop"])
        result = runner.invoke(app, ["live", "report"])
        assert result.exit_code == 0

    def test_live_exposure_after_start_stop(self) -> None:
        runner.invoke(app, ["live", "start"])
        runner.invoke(app, ["live", "stop"])
        result = runner.invoke(app, ["live", "exposure"])
        assert result.exit_code == 0


class TestLiveStatusJSON:
    def setup_method(self) -> None:
        _reset_live_session()

    def test_live_status_json_has_all_fields(self) -> None:
        result = runner.invoke(app, ["live", "status", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        required_fields = [
            "broker_provider",
            "environment",
            "deployment_status",
            "deployment_uptime_seconds",
            "version",
            "runtime_status",
            "runtime_uptime_seconds",
            "broker_connected",
            "pipeline_executions",
            "active_subscriptions",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
