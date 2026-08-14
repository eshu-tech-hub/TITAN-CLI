"""CLI integration tests for TITAN CLI commands."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from titan.cli import app
from titan.cli.commands.backtest import _reset_backtest_session
from titan.cli.commands.paper import _reset_paper_session

runner = CliRunner()


@pytest.fixture
def running_runtime():
    from titan.runtime.models import (
        RuntimeReport, RuntimeStatus, RuntimeHealth, SchedulerStatus, 
        BrokerStatus, MarketStatus, JournalStatus, ResourceStatus, 
        PerformanceStatus, RecoveryStatus, PaperBrokerStatus, PortfolioStatus,
        ComponentHealth, HealthStatus
    )
    from titan.brokers.models import ConnectionStatus

    mock_engine = MagicMock()
    status_states = ["STOPPED", "STARTING", "RUNNING"]
    mock_engine.status.name = MagicMock(side_effect=status_states)
    
    dummy_health = ComponentHealth(
        component_name="dummy",
        status=HealthStatus.HEALTHY,
        error="ok"
    )
    
    mock_report = RuntimeReport(
        runtime_status=RuntimeStatus.RUNNING,
        health=RuntimeHealth(component_health=(dummy_health,), warnings=(), errors=()),
        scheduler=SchedulerStatus(active=True, pipeline_executions=0, last_pipeline_time=None),
        broker=BrokerStatus(connection=ConnectionStatus.CONNECTED),
        market=MarketStatus(stream_status="connected", active_subscriptions=0, last_quote_time=None),
        journal=JournalStatus(),
        resource=ResourceStatus(),
        performance=PerformanceStatus(uptime_seconds=100.0),
        recovery=RecoveryStatus(),
        paper=PaperBrokerStatus(active=False),
        portfolio=PortfolioStatus()
    )
    
    mock_engine.generate_report.return_value = mock_report
    mock_engine.start = MagicMock()
    mock_engine.stop = MagicMock()

    with patch("titan.cli.common._runtime_engine", mock_engine):
        yield mock_engine


@pytest.fixture(autouse=True)
def mock_runtime_start():
    with patch("titan.runtime.runtime.RuntimeEngine.start") as mock_start:
        with patch("titan.runtime.local_transport.LocalTransportServer.start"):
            yield mock_start


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


class TestRootCommands:
    def test_root_help(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "TITAN CLI" in result.output
        assert "version" in result.output
        assert "doctor" in result.output
        assert "paper" in result.output
        assert "config" in result.output

    def test_version(self) -> None:
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "TITAN CLI" in result.output or "TITAN" in result.output
        assert "1.0.0" in result.output

    def test_version_verbose(self) -> None:
        result = runner.invoke(app, ["version", "--verbose"])
        assert result.exit_code == 0
        assert "1.0.0" in result.output

    def test_doctor(self) -> None:
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "TITAN Doctor" in result.output
        assert "Python" in result.output


class TestPaperCommands:
    def setup_method(self) -> None:
        _reset_paper_session()
        # Ensure no paper process is running from previous aborted tests
        runner.invoke(app, ["paper", "stop"])

    def teardown_method(self) -> None:
        runner.invoke(app, ["paper", "stop"])

    def test_paper_help(self) -> None:
        result = runner.invoke(app, ["paper", "--help"])
        assert result.exit_code == 0
        assert "Paper trading" in result.output

    def test_paper_status_when_not_running(self) -> None:
        result = runner.invoke(app, ["paper", "status"])
        assert result.exit_code == 0
        assert "Not Running" in result.output

    def test_paper_status_json_when_not_running(self) -> None:
        result = runner.invoke(app, ["paper", "status", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert data["running"] is False

    def test_paper_start(self) -> None:
        result = runner.invoke(app, ["paper", "start"])
        assert result.exit_code == 0
        assert "started" in result.output.lower()

    def test_paper_start_verbose(self) -> None:
        result = runner.invoke(app, ["paper", "start", "--verbose"])
        assert result.exit_code == 0
        assert "Startup Checklist" in result.output
        assert "started" in result.output.lower()

    def test_paper_start_dry_run(self) -> None:
        result = runner.invoke(app, ["paper", "start", "--dry-run"])
        assert result.exit_code == 0
        assert "Startup Checklist" in result.output
        assert "Dry run passed" in result.output

    def test_paper_start_dry_run_verbose(self) -> None:
        result = runner.invoke(app, ["paper", "start", "--dry-run", "--verbose"])
        assert result.exit_code == 0
        assert "Startup Checklist" in result.output
        assert "Configuration loaded" in result.output

    def test_paper_start_custom_cash(self) -> None:
        result = runner.invoke(app, ["paper", "start", "--cash", "50000"])
        assert result.exit_code == 0
        assert "started" in result.output.lower()

    def test_paper_stop_when_not_running(self) -> None:
        result = runner.invoke(app, ["paper", "stop"])
        assert result.exit_code == 0
        assert (
            "not running" in result.output.lower() or "stopped" in result.output.lower()
        )

    def test_paper_stop_verbose_when_not_running(self) -> None:
        result = runner.invoke(app, ["paper", "stop", "--verbose"])
        assert result.exit_code == 0
        assert (
            "not running" in result.output.lower() or "stopped" in result.output.lower()
        )

    def test_paper_restart(self) -> None:
        result = runner.invoke(app, ["paper", "restart"])
        assert result.exit_code == 0
        assert "started" in result.output.lower()

    def test_paper_restart_verbose(self) -> None:
        result = runner.invoke(app, ["paper", "restart", "--verbose"])
        assert result.exit_code == 0
        assert "started" in result.output.lower()

    def test_paper_reset(self) -> None:
        result = runner.invoke(app, ["paper", "reset"])
        assert result.exit_code == 0
        assert "reset" in result.output.lower()

    def test_paper_report_when_not_running(self) -> None:
        result = runner.invoke(app, ["paper", "report"])
        assert result.exit_code == 0
        assert (
            "no active" in result.output.lower()
            or "not running" in result.output.lower()
        )

    def test_paper_report_json_when_not_running(self) -> None:
        result = runner.invoke(app, ["paper", "report", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert "error" in data

    def test_paper_full_lifecycle(self) -> None:
        result = runner.invoke(app, ["paper", "start"])
        assert result.exit_code == 0
        assert "started" in result.output.lower()

        result = runner.invoke(app, ["paper", "status"])
        assert result.exit_code == 0
        assert "Paper Trading Session" in result.output

        result = runner.invoke(app, ["paper", "report"])
        assert result.exit_code == 0

        result = runner.invoke(app, ["paper", "stop"])
        assert result.exit_code == 0
        assert "stopped" in result.output.lower()

    def test_paper_lifecycle_status_json(self) -> None:
        result = runner.invoke(app, ["paper", "start"])
        assert result.exit_code == 0

        result = runner.invoke(app, ["paper", "status", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert data["running"] is True
        assert "cash_balance" in data
        assert "portfolio_value" in data
        assert "open_positions" in data
        assert "win_rate" in data

        result = runner.invoke(app, ["paper", "stop"])
        assert result.exit_code == 0

    def test_paper_lifecycle_status_verbose(self) -> None:
        result = runner.invoke(app, ["paper", "start"])
        assert result.exit_code == 0

        result = runner.invoke(app, ["paper", "status", "--verbose"])
        assert result.exit_code == 0
        assert "Paper Trading Session" in result.output
        assert "Performance Metrics" in result.output

        result = runner.invoke(app, ["paper", "stop"])
        assert result.exit_code == 0

    def test_paper_lifecycle_report_json(self) -> None:
        result = runner.invoke(app, ["paper", "start"])
        assert result.exit_code == 0

        result = runner.invoke(app, ["paper", "report", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert "session" in data
        assert "portfolio" in data
        assert "performance" in data
        assert "pnl" in data
        assert "positions" in data
        assert "orders" in data

        result = runner.invoke(app, ["paper", "stop"])
        assert result.exit_code == 0

    def test_paper_lifecycle_report_verbose(self) -> None:
        result = runner.invoke(app, ["paper", "start"])
        assert result.exit_code == 0

        result = runner.invoke(app, ["paper", "report", "--verbose"])
        assert result.exit_code == 0
        assert "Session Summary" in result.output
        assert "Portfolio Summary" in result.output
        assert "P&L Breakdown" in result.output
        assert "Performance Metrics" in result.output

        result = runner.invoke(app, ["paper", "stop"])
        assert result.exit_code == 0

    def test_paper_report_export_json(self) -> None:
        result = runner.invoke(app, ["paper", "start"])
        assert result.exit_code == 0

        with tempfile.TemporaryDirectory() as tmpdir:
            export_path = Path(tmpdir) / "report.json"
            result = runner.invoke(
                app, ["paper", "report", "--export", str(export_path)]
            )
            assert result.exit_code == 0
            assert export_path.exists()
            data = json.loads(export_path.read_text(encoding="utf-8"))
            assert "session" in data
            assert "portfolio" in data

        result = runner.invoke(app, ["paper", "stop"])
        assert result.exit_code == 0

    def test_paper_report_export_csv(self) -> None:
        result = runner.invoke(app, ["paper", "start"])
        assert result.exit_code == 0

        with tempfile.TemporaryDirectory() as tmpdir:
            export_path = Path(tmpdir) / "report.csv"
            result = runner.invoke(
                app, ["paper", "report", "--export", str(export_path)]
            )
            assert result.exit_code == 0
            assert export_path.exists()
            content = export_path.read_text(encoding="utf-8")
            assert "Section" in content
            assert "Session" in content

        result = runner.invoke(app, ["paper", "stop"])
        assert result.exit_code == 0

    def test_paper_report_reset_after(self) -> None:
        result = runner.invoke(app, ["paper", "start"])
        assert result.exit_code == 0

        result = runner.invoke(app, ["paper", "report", "--reset"])
        assert result.exit_code == 0
        assert "reset" in result.output.lower()

    def test_paper_help_shows_all_commands(self) -> None:
        result = runner.invoke(app, ["paper", "--help"])
        assert result.exit_code == 0
        assert "start" in result.output
        assert "stop" in result.output
        assert "restart" in result.output
        assert "status" in result.output
        assert "reset" in result.output
        assert "report" in result.output


class TestConfigCommands:
    def test_config_help(self) -> None:
        result = runner.invoke(app, ["config", "--help"])
        assert result.exit_code == 0
        assert "Configuration" in result.output

    def test_config_show_all(self) -> None:
        result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
        assert "APP" in result.output
        assert "BROKER" in result.output
        assert "RUNTIME" in result.output
        assert "RISK" in result.output

    def test_config_show_section(self) -> None:
        result = runner.invoke(app, ["config", "show", "app"])
        assert result.exit_code == 0
        assert "APP" in result.output
        assert "TITAN" in result.output

    def test_config_show_unknown_section(self) -> None:
        result = runner.invoke(app, ["config", "show", "nonexistent"])
        assert result.exit_code == 0
        assert "Unknown section" in result.output


class TestMonitorCommands:
    def test_monitor_help(self) -> None:
        result = runner.invoke(app, ["monitor", "--help"])
        assert result.exit_code == 0

    def test_monitor_status(self) -> None:
        result = runner.invoke(app, ["monitor", "status"])
        assert result.exit_code == 0
        assert "Monitoring" in result.output


class TestAuditCommands:
    def test_audit_help(self) -> None:
        result = runner.invoke(app, ["audit", "--help"])
        assert result.exit_code == 0
        assert "Audit" in result.output

    def test_audit_status(self) -> None:
        result = runner.invoke(app, ["audit", "status"])
        assert result.exit_code == 0
        assert "Audit Trail" in result.output
        assert "Total Events" in result.output

    def test_audit_verify(self) -> None:
        result = runner.invoke(app, ["audit", "verify"])
        assert result.exit_code == 0
        assert "integrity" in result.output.lower()


class TestDeploymentCommands:
    def test_deployment_help(self) -> None:
        result = runner.invoke(app, ["deployment", "--help"])
        assert result.exit_code == 0
        assert "Deployment" in result.output

    def test_deployment_status(self) -> None:
        result = runner.invoke(app, ["deployment", "status"])
        assert result.exit_code == 0
        assert "Deployment" in result.output
        assert "Version" in result.output


class TestReportCommands:
    def test_report_help(self) -> None:
        result = runner.invoke(app, ["report", "--help"])
        assert result.exit_code == 0

    def test_report_generate(self) -> None:
        result = runner.invoke(app, ["report", "generate"])
        assert result.exit_code == 0
        assert "Deployment Report" in result.output


class TestLogsCommands:
    def test_logs_help(self) -> None:
        result = runner.invoke(app, ["logs", "--help"])
        assert result.exit_code == 0
        assert "Log" in result.output

    def test_logs_stats(self) -> None:
        result = runner.invoke(app, ["logs", "stats"])
        assert result.exit_code == 0
        assert "Log Statistics" in result.output

    def test_logs_path(self) -> None:
        result = runner.invoke(app, ["logs", "path"])
        assert result.exit_code == 0
        assert "titan.log" in result.output


class TestBacktestCommands:
    def setup_method(self) -> None:
        _reset_backtest_session()

    @staticmethod
    def _write_csv(tmpdir: str, rows: int = 10) -> Path:
        csv_path = Path(tmpdir) / "data.csv"
        lines = ["timestamp,open,high,low,close,volume"]
        for i in range(rows):
            ts = f"2024-01-{i + 1:02d}T09:15:00+00:00"
            op = 100 + i
            hi = op + 5
            lo = op - 2
            cl = op + 1
            lines.append(f"{ts},{op},{hi},{lo},{cl},10000")
        csv_path.write_text("\n".join(lines), encoding="utf-8")
        return csv_path

    def test_backtest_help(self) -> None:
        result = runner.invoke(app, ["backtest", "--help"])
        assert result.exit_code == 0
        assert "Backtesting" in result.output
        assert "run" in result.output
        assert "status" in result.output
        assert "report" in result.output
        assert "list" in result.output

    def test_backtest_status_idle(self) -> None:
        result = runner.invoke(app, ["backtest", "status"])
        assert result.exit_code == 0
        assert "Backtest Status" in result.output
        assert "idle" in result.output.lower()

    def test_backtest_status_json_idle(self) -> None:
        result = runner.invoke(app, ["backtest", "status", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert data["running"] is False
        assert data["completed_backtests"] == 0

    def test_backtest_list_empty(self) -> None:
        result = runner.invoke(app, ["backtest", "list"])
        assert result.exit_code == 0
        assert "No completed backtests" in result.output

    def test_backtest_list_json_empty(self) -> None:
        result = runner.invoke(app, ["backtest", "list", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert data["count"] == 0
        assert data["backtests"] == []

    def test_backtest_report_empty(self) -> None:
        result = runner.invoke(app, ["backtest", "report"])
        assert result.exit_code == 0
        assert "No completed backtests" in result.output

    def test_backtest_report_json_empty(self) -> None:
        result = runner.invoke(app, ["backtest", "report", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert "error" in data

    def test_backtest_run_basic(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = self._write_csv(tmpdir, rows=5)
            result = runner.invoke(
                app,
                [
                    "backtest",
                    "run",
                    "RELIANCE",
                    "nse",
                    "--csv",
                    str(csv_path),
                ],
            )
            assert result.exit_code == 0
            assert "completed" in result.output.lower() or "Backtest" in result.output

    def test_backtest_run_json_status_after(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = self._write_csv(tmpdir, rows=5)
            result = runner.invoke(
                app,
                [
                    "backtest",
                    "run",
                    "RELIANCE",
                    "nse",
                    "--csv",
                    str(csv_path),
                ],
            )
            assert result.exit_code == 0

            result = runner.invoke(app, ["backtest", "status", "--json"])
            assert result.exit_code == 0
            data = _extract_json(result.output)
            assert data["running"] is False
            assert data["completed_backtests"] == 1

    def test_backtest_run_list_after(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = self._write_csv(tmpdir, rows=5)
            result = runner.invoke(
                app,
                [
                    "backtest",
                    "run",
                    "RELIANCE",
                    "nse",
                    "--csv",
                    str(csv_path),
                ],
            )
            assert result.exit_code == 0

            result = runner.invoke(app, ["backtest", "list"])
            assert result.exit_code == 0
            assert "RELIAN" in result.output
            assert "nse" in result.output

    def test_backtest_run_report_after(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = self._write_csv(tmpdir, rows=5)
            result = runner.invoke(
                app,
                [
                    "backtest",
                    "run",
                    "RELIANCE",
                    "nse",
                    "--csv",
                    str(csv_path),
                ],
            )
            assert result.exit_code == 0

            result = runner.invoke(app, ["backtest", "report"])
            assert result.exit_code == 0
            assert "Backtest Summary" in result.output
            assert "Trading Statistics" in result.output
            assert "Performance Metrics" in result.output

    def test_backtest_run_report_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = self._write_csv(tmpdir, rows=5)
            result = runner.invoke(
                app,
                [
                    "backtest",
                    "run",
                    "RELIANCE",
                    "nse",
                    "--csv",
                    str(csv_path),
                ],
            )
            assert result.exit_code == 0

            result = runner.invoke(app, ["backtest", "report", "--json"])
            assert result.exit_code == 0
            data = _extract_json(result.output)
            assert "backtest_id" in data
            assert data["symbol"] == "RELIANCE"
            assert data["exchange"] == "nse"
            assert "statistics" in data
            assert "metrics" in data

    def test_backtest_run_report_verbose(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = self._write_csv(tmpdir, rows=5)
            result = runner.invoke(
                app,
                [
                    "backtest",
                    "run",
                    "RELIANCE",
                    "nse",
                    "--csv",
                    str(csv_path),
                ],
            )
            assert result.exit_code == 0

            result = runner.invoke(app, ["backtest", "report", "--verbose"])
            assert result.exit_code == 0
            assert "Backtest Summary" in result.output
            assert "Trading Statistics" in result.output
            assert "Performance Metrics" in result.output

    def test_backtest_run_report_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = self._write_csv(tmpdir, rows=5)
            result = runner.invoke(
                app,
                [
                    "backtest",
                    "run",
                    "RELIANCE",
                    "nse",
                    "--csv",
                    str(csv_path),
                ],
            )
            assert result.exit_code == 0

            export_path = Path(tmpdir) / "report.json"
            result = runner.invoke(
                app, ["backtest", "report", "--export", str(export_path)]
            )
            assert result.exit_code == 0
            assert export_path.exists()
            data = json.loads(export_path.read_text(encoding="utf-8"))
            assert "backtest_id" in data
            assert data["symbol"] == "RELIANCE"

    def test_backtest_run_report_invalid_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = self._write_csv(tmpdir, rows=5)
            result = runner.invoke(
                app,
                [
                    "backtest",
                    "run",
                    "RELIANCE",
                    "nse",
                    "--csv",
                    str(csv_path),
                ],
            )
            assert result.exit_code == 0

            result = runner.invoke(app, ["backtest", "report", "99"])
            assert result.exit_code == 1
            assert "Invalid index" in result.output

    def test_backtest_run_report_valid_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = self._write_csv(tmpdir, rows=5)
            result = runner.invoke(
                app,
                [
                    "backtest",
                    "run",
                    "RELIANCE",
                    "nse",
                    "--csv",
                    str(csv_path),
                ],
            )
            assert result.exit_code == 0

            result = runner.invoke(app, ["backtest", "report", "1"])
            assert result.exit_code == 0
            assert "Backtest Summary" in result.output

    def test_backtest_run_multiple(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = self._write_csv(tmpdir, rows=5)

            result = runner.invoke(
                app,
                [
                    "backtest",
                    "run",
                    "RELIANCE",
                    "nse",
                    "--csv",
                    str(csv_path),
                ],
            )
            assert result.exit_code == 0

            result = runner.invoke(
                app,
                [
                    "backtest",
                    "run",
                    "INFY",
                    "nse",
                    "--csv",
                    str(csv_path),
                ],
            )
            assert result.exit_code == 0

            result = runner.invoke(app, ["backtest", "list"])
            assert result.exit_code == 0
            assert "RELIAN" in result.output
            assert "INFY" in result.output

            result = runner.invoke(app, ["backtest", "status", "--json"])
            assert result.exit_code == 0
            data = _extract_json(result.output)
            assert data["completed_backtests"] == 2

    def test_backtest_run_bad_exchange(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = self._write_csv(tmpdir, rows=5)
            result = runner.invoke(
                app,
                [
                    "backtest",
                    "run",
                    "RELIANCE",
                    "INVALID_EXCHANGE",
                    "--csv",
                    str(csv_path),
                ],
            )
            assert result.exit_code == 3

    def test_backtest_run_missing_csv(self) -> None:
        result = runner.invoke(
            app,
            [
                "backtest",
                "run",
                "RELIANCE",
                "nse",
                "--csv",
                "/nonexistent/data.csv",
            ],
        )
        assert result.exit_code == 3

    def test_backtest_run_custom_capital(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = self._write_csv(tmpdir, rows=5)
            result = runner.invoke(
                app,
                [
                    "backtest",
                    "run",
                    "RELIANCE",
                    "nse",
                    "--csv",
                    str(csv_path),
                    "--capital",
                    "500000",
                ],
            )
            assert result.exit_code == 0

    def test_backtest_run_verbose(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = self._write_csv(tmpdir, rows=5)
            result = runner.invoke(
                app,
                [
                    "backtest",
                    "run",
                    "RELIANCE",
                    "nse",
                    "--csv",
                    str(csv_path),
                    "--verbose",
                ],
            )
            assert result.exit_code == 0
            assert (
                "Backtest completed" in result.output or "done" in result.output.lower()
            )

    def test_backtest_list_json_after_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = self._write_csv(tmpdir, rows=5)
            result = runner.invoke(
                app,
                [
                    "backtest",
                    "run",
                    "RELIANCE",
                    "nse",
                    "--csv",
                    str(csv_path),
                ],
            )
            assert result.exit_code == 0

            result = runner.invoke(app, ["backtest", "list", "--json"])
            assert result.exit_code == 0
            data = _extract_json(result.output)
            assert data["count"] == 1
            assert data["backtests"][0]["symbol"] == "RELIANCE"


class TestLiveCommands:
    def test_live_help(self) -> None:
        result = runner.invoke(app, ["live", "--help"])
        assert result.exit_code == 0
        assert "Live trading" in result.output
        assert "start" in result.output
        assert "stop" in result.output
        assert "restart" in result.output
        assert "status" in result.output

    def test_live_status(self) -> None:
        result = runner.invoke(app, ["live", "status"])
        assert result.exit_code == 0
        assert "Live Trading" in result.output
        assert "Broker" in result.output
        assert "Environment" in result.output

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
        assert "Risk Configuration" in result.output

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
            or "Live trading started" in result.output
        )

    def test_live_start_verbose(self) -> None:
        result = runner.invoke(app, ["live", "start", "--verbose"])
        assert result.exit_code == 0
        assert "Startup Checklist" in result.output
        assert "Live trading started" in result.output

    def test_live_stop_when_not_running(self) -> None:
        result = runner.invoke(app, ["live", "stop"])
        assert result.exit_code == 0
        assert (
            "not running" in result.output.lower() or "stopped" in result.output.lower()
        )

    def test_live_restart(self) -> None:
        result = runner.invoke(app, ["live", "restart"])
        assert result.exit_code == 0
        assert (
            "started" in result.output.lower()
            or "Live trading started" in result.output
        )


class TestExitCodes:
    def test_invalid_command(self) -> None:
        result = runner.invoke(app, ["nonexistent"])
        assert result.exit_code != 0

    def test_help_flag(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0


class TestRuntimeCommands:
    def test_runtime_help(self) -> None:
        result = runner.invoke(app, ["runtime", "--help"])
        assert result.exit_code == 0
        assert "Runtime" in result.output
        assert "start" in result.output
        assert "stop" in result.output
        assert "restart" in result.output
        assert "status" in result.output

    def test_runtime_status(self, running_runtime) -> None:
        result = runner.invoke(app, ["runtime", "status"])
        assert result.exit_code == 0
        assert "Runtime Engine" in result.output
        assert "Status" in result.output
        assert "Uptime" in result.output

    def test_runtime_status_json(self, running_runtime) -> None:
        result = runner.invoke(app, ["runtime", "status", "--json"])
        assert result.exit_code == 0
        assert "runtime_status" in result.output
        assert "uptime_seconds" in result.output
        assert "broker_status" in result.output

    def test_runtime_status_verbose(self, running_runtime) -> None:
        result = runner.invoke(app, ["runtime", "status", "--verbose"])
        assert result.exit_code == 0
        assert "Runtime Engine" in result.output
        assert "Component Health" in result.output

    def test_runtime_start(self, running_runtime) -> None:
        result = runner.invoke(app, ["runtime", "start"])
        assert result.exit_code == 0
        output = result.output.lower()
        assert "started" in output or "already running" in output

    def test_runtime_stop_when_stopped(self) -> None:
        from titan.runtime.exceptions import RuntimeError as TitanRuntimeError
        
        mock_transport = MagicMock()
        mock_transport.stop.side_effect = TitanRuntimeError("Runtime engine is not running (connection refused).")
        
        with patch("titan.cli.commands.runtime._get_transport", return_value=mock_transport):
            result = runner.invoke(app, ["runtime", "stop"])
            assert result.exit_code == 0
            assert (
                "already stopped" in result.output.lower()
                or "stopped" in result.output.lower()
            )

    def test_runtime_restart(self) -> None:
        result = runner.invoke(app, ["runtime", "restart"])
        assert result.exit_code == 0
        assert (
            "restart" in result.output.lower() or "Runtime restarted" in result.output
        )
