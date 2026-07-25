"""CLI integration tests for TITAN operations and administration commands."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from titan.cli import app

runner = CliRunner()


def _extract_json(output: str) -> dict[str, Any]:
    """Extract JSON from CLI output that may contain loguru lines."""
    for line in output.strip().splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                pass
    lines = output.strip().splitlines()
    json_lines: list[str] = []
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


def _extract_json_list(output: str) -> list[Any]:
    """Extract JSON array from CLI output."""
    for line in output.strip().splitlines():
        line = line.strip()
        if line.startswith("["):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                pass
    lines = output.strip().splitlines()
    json_lines: list[str] = []
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


# ──────────────────────────────────────────────────
# Recovery CLI
# ──────────────────────────────────────────────────


class TestRecoveryHelp:
    def test_recovery_help(self) -> None:
        result = runner.invoke(app, ["recovery", "--help"])
        assert result.exit_code == 0
        assert "Recovery" in result.output
        assert "status" in result.output
        assert "retry" in result.output
        assert "checkpoint" in result.output
        assert "restore" in result.output
        assert "circuit" in result.output


class TestRecoveryStatus:
    def test_status(self) -> None:
        result = runner.invoke(app, ["recovery", "status"])
        assert result.exit_code == 0
        assert "Recovery Subsystem" in result.output

    def test_status_json(self) -> None:
        result = runner.invoke(app, ["recovery", "status", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert "total_requests" in data
        assert "successful" in data
        assert "failed" in data
        assert "status" in data

    def test_status_verbose(self) -> None:
        result = runner.invoke(app, ["recovery", "status", "--verbose"])
        assert result.exit_code == 0
        assert "Recovery Subsystem" in result.output


class TestRecoveryRetry:
    def test_retry_valid(self) -> None:
        result = runner.invoke(app, ["recovery", "retry", "pipeline", "test failure"])
        assert result.exit_code == 0

    def test_retry_json(self) -> None:
        result = runner.invoke(app, ["recovery", "retry", "pipeline", "test", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert "request_id" in data
        assert "status" in data

    def test_retry_invalid_component(self) -> None:
        result = runner.invoke(
            app, ["recovery", "retry", "invalid_component", "reason"]
        )
        assert result.exit_code == 1


class TestRecoveryCheckpoint:
    def test_checkpoint_list_empty(self) -> None:
        result = runner.invoke(app, ["recovery", "checkpoint", "list"])
        assert result.exit_code == 0

    def test_checkpoint_save(self) -> None:
        result = runner.invoke(
            app,
            [
                "recovery",
                "checkpoint",
                "save",
                "--component",
                "pipeline",
                "--id",
                "test-cp-1",
            ],
        )
        assert result.exit_code == 0
        assert "saved" in result.output.lower() or "test-cp-1" in result.output

    def test_checkpoint_save_json(self) -> None:
        result = runner.invoke(
            app,
            [
                "recovery",
                "checkpoint",
                "save",
                "--component",
                "pipeline",
                "--id",
                "cp-json-1",
                "--json",
            ],
        )
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert data.get("checkpoint_id") == "cp-json-1"

    def test_checkpoint_list_after_save(self) -> None:
        runner.invoke(
            app,
            [
                "recovery",
                "checkpoint",
                "save",
                "--component",
                "pipeline",
                "--id",
                "cp-list-1",
            ],
        )
        result = runner.invoke(app, ["recovery", "checkpoint", "list", "--json"])
        assert result.exit_code == 0
        data = _extract_json_list(result.output)
        assert len(data) >= 1

    def test_checkpoint_latest(self) -> None:
        runner.invoke(
            app,
            [
                "recovery",
                "checkpoint",
                "save",
                "--component",
                "pipeline",
                "--id",
                "cp-latest",
            ],
        )
        result = runner.invoke(
            app, ["recovery", "checkpoint", "latest", "--component", "pipeline"]
        )
        assert result.exit_code == 0

    def test_checkpoint_invalid_component(self) -> None:
        result = runner.invoke(
            app, ["recovery", "checkpoint", "save", "--component", "bogus", "--id", "x"]
        )
        assert result.exit_code == 1


class TestRecoveryRestore:
    def test_restore_valid(self) -> None:
        runner.invoke(
            app,
            [
                "recovery",
                "checkpoint",
                "save",
                "--component",
                "pipeline",
                "--id",
                "restore-1",
            ],
        )
        result = runner.invoke(app, ["recovery", "restore", "restore-1"])
        assert result.exit_code == 0
        assert "restored" in result.output.lower()

    def test_restore_json(self) -> None:
        runner.invoke(
            app,
            [
                "recovery",
                "checkpoint",
                "save",
                "--component",
                "pipeline",
                "--id",
                "restore-json",
            ],
        )
        result = runner.invoke(app, ["recovery", "restore", "restore-json", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert data.get("restored") is True

    def test_restore_invalid(self) -> None:
        result = runner.invoke(app, ["recovery", "restore", "nonexistent-id"])
        assert result.exit_code == 1


class TestRecoveryCircuit:
    def test_circuit_list_empty(self) -> None:
        result = runner.invoke(app, ["recovery", "circuit", "list"])
        assert result.exit_code == 0

    def test_circuit_list_json(self) -> None:
        result = runner.invoke(app, ["recovery", "circuit", "list", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert "circuit_breakers" in data

    def test_circuit_reset_not_found(self) -> None:
        result = runner.invoke(
            app, ["recovery", "circuit", "reset", "--name", "nonexistent"]
        )
        assert result.exit_code == 1

    def test_circuit_reset_json(self) -> None:
        from titan.cli.common import get_recovery_manager

        rm = get_recovery_manager()
        rm.register_circuit_breaker("test-cb")
        result = runner.invoke(
            app, ["recovery", "circuit", "reset", "--name", "test-cb", "--json"]
        )
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert data.get("reset") is True


# ──────────────────────────────────────────────────
# Deployment CLI
# ──────────────────────────────────────────────────


class TestDeploymentHelp:
    def test_deployment_help(self) -> None:
        result = runner.invoke(app, ["deployment", "--help"])
        assert result.exit_code == 0
        assert "Deployment" in result.output
        assert "validate" in result.output
        assert "restore" in result.output
        assert "health" in result.output
        assert "backup" in result.output


class TestDeploymentStatus:
    def test_status(self) -> None:
        result = runner.invoke(app, ["deployment", "status"])
        assert result.exit_code == 0
        assert "Deployment" in result.output

    def test_status_json(self) -> None:
        result = runner.invoke(app, ["deployment", "status", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert "status" in data
        assert "environment" in data
        assert "version" in data

    def test_status_verbose(self) -> None:
        result = runner.invoke(app, ["deployment", "status", "--verbose"])
        assert result.exit_code == 0


class TestDeploymentValidate:
    def test_validate(self) -> None:
        result = runner.invoke(app, ["deployment", "validate"])
        assert result.exit_code == 0

    def test_validate_json(self) -> None:
        result = runner.invoke(app, ["deployment", "validate", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert "overall_status" in data
        assert "readiness" in data
        assert "liveness" in data

    def test_validate_verbose(self) -> None:
        result = runner.invoke(app, ["deployment", "validate", "--verbose"])
        assert result.exit_code == 0


class TestDeploymentHealth:
    def test_health(self) -> None:
        result = runner.invoke(app, ["deployment", "health"])
        assert result.exit_code == 0
        assert "Deployment Health" in result.output

    def test_health_json(self) -> None:
        result = runner.invoke(app, ["deployment", "health", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert "overall_status" in data
        assert "uptime_seconds" in data

    def test_health_verbose(self) -> None:
        result = runner.invoke(app, ["deployment", "health", "--verbose"])
        assert result.exit_code == 0


class TestDeploymentBackup:
    def test_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["deployment", "backup", "--dest", tmpdir])
            assert result.exit_code == 0
            assert "Backup created" in result.output

    def test_backup_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(
                app, ["deployment", "backup", "--dest", tmpdir, "--json"]
            )
            assert result.exit_code == 0
            data = _extract_json(result.output)
            assert "backup_id" in data
            assert data.get("success") is True


class TestDeploymentRestore:
    def test_restore_invalid(self) -> None:
        result = runner.invoke(app, ["deployment", "restore", "nonexistent-backup"])
        assert result.exit_code == 1


# ──────────────────────────────────────────────────
# Audit CLI
# ──────────────────────────────────────────────────


class TestAuditHelp:
    def test_audit_help(self) -> None:
        result = runner.invoke(app, ["audit", "--help"])
        assert result.exit_code == 0
        assert "Audit" in result.output
        assert "search" in result.output
        assert "export" in result.output
        assert "stats" in result.output


class TestAuditStatus:
    def test_status(self) -> None:
        result = runner.invoke(app, ["audit", "status"])
        assert result.exit_code == 0
        assert "Audit Trail" in result.output

    def test_status_json(self) -> None:
        result = runner.invoke(app, ["audit", "status", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert "total_events" in data
        assert "integrity_status" in data


class TestAuditSearch:
    def test_search_empty(self) -> None:
        result = runner.invoke(app, ["audit", "search"])
        assert result.exit_code == 0

    def test_search_json(self) -> None:
        result = runner.invoke(app, ["audit", "search", "--json"])
        assert result.exit_code == 0
        data = _extract_json_list(result.output)
        assert isinstance(data, list)

    def test_search_limit(self) -> None:
        result = runner.invoke(app, ["audit", "search", "--limit", "5"])
        assert result.exit_code == 0


class TestAuditExport:
    def test_export_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out = str(Path(tmpdir) / "audit.json")
            result = runner.invoke(app, ["audit", "export", "--output", out])
            assert result.exit_code == 0
            assert Path(out).exists()

    def test_export_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out = str(Path(tmpdir) / "audit.csv")
            result = runner.invoke(
                app, ["audit", "export", "--output", out, "--format", "csv"]
            )
            assert result.exit_code == 0
            assert Path(out).exists()

    def test_export_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out = str(Path(tmpdir) / "audit_lim.json")
            result = runner.invoke(
                app, ["audit", "export", "--output", out, "--limit", "2"]
            )
            assert result.exit_code == 0


class TestAuditStats:
    def test_stats(self) -> None:
        result = runner.invoke(app, ["audit", "stats"])
        assert result.exit_code == 0
        assert "Audit Statistics" in result.output

    def test_stats_json(self) -> None:
        result = runner.invoke(app, ["audit", "stats", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert "total_events" in data


# ──────────────────────────────────────────────────
# Logs CLI
# ──────────────────────────────────────────────────


class TestLogsHelp:
    def test_logs_help(self) -> None:
        result = runner.invoke(app, ["logs", "--help"])
        assert result.exit_code == 0
        assert "Log" in result.output
        assert "level" in result.output
        assert "rotate" in result.output
        assert "clear" in result.output


class TestLogsShow:
    def test_show_json(self) -> None:
        result = runner.invoke(app, ["logs", "show", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert "entries" in data


class TestLogsStats:
    def test_stats_json(self) -> None:
        result = runner.invoke(app, ["logs", "stats", "--json"])
        assert result.exit_code == 0


class TestLogLevel:
    def test_level_get(self) -> None:
        result = runner.invoke(app, ["logs", "level"])
        assert result.exit_code == 0
        assert "log level" in result.output.lower()

    def test_level_get_json(self) -> None:
        result = runner.invoke(app, ["logs", "level", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert "level" in data

    def test_level_set_valid(self) -> None:
        result = runner.invoke(app, ["logs", "level", "DEBUG"])
        assert result.exit_code == 0
        assert "DEBUG" in result.output

    def test_level_set_json(self) -> None:
        result = runner.invoke(app, ["logs", "level", "WARNING", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert data.get("level") == "WARNING"

    def test_level_set_invalid(self) -> None:
        result = runner.invoke(app, ["logs", "level", "BOGUS"])
        assert result.exit_code == 1


class TestLogsRotate:
    def test_rotate_no_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            orig = Path.cwd()
            try:
                import os

                os.chdir(tmpdir)
                result = runner.invoke(app, ["logs", "rotate"])
                assert result.exit_code == 0
            finally:
                os.chdir(orig)

    def test_rotate_with_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "logs"
            log_dir.mkdir()
            log_file = log_dir / "titan.log"
            log_file.write_text("test log line\n", encoding="utf-8")
            orig = Path.cwd()
            try:
                import os

                os.chdir(tmpdir)
                result = runner.invoke(app, ["logs", "rotate"])
                assert result.exit_code == 0
            finally:
                os.chdir(orig)

    def test_rotate_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "logs"
            log_dir.mkdir()
            log_file = log_dir / "titan.log"
            log_file.write_text("log data\n", encoding="utf-8")
            orig = Path.cwd()
            try:
                import os

                os.chdir(tmpdir)
                result = runner.invoke(app, ["logs", "rotate", "--json"])
                assert result.exit_code == 0
            finally:
                os.chdir(orig)


class TestLogsClear:
    def test_clear_no_file(self) -> None:
        result = runner.invoke(app, ["logs", "clear", "--force"])
        assert result.exit_code == 0

    def test_clear_with_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "logs"
            log_dir.mkdir()
            log_file = log_dir / "titan.log"
            log_file.write_text("log to clear\n", encoding="utf-8")
            orig = Path.cwd()
            try:
                import os

                os.chdir(tmpdir)
                result = runner.invoke(app, ["logs", "clear", "--force"])
                assert result.exit_code == 0
                assert log_file.read_text(encoding="utf-8") == ""
            finally:
                os.chdir(orig)

    def test_clear_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "logs"
            log_dir.mkdir()
            log_file = log_dir / "titan.log"
            log_file.write_text("data\n", encoding="utf-8")
            orig = Path.cwd()
            try:
                import os

                os.chdir(tmpdir)
                result = runner.invoke(app, ["logs", "clear", "--force", "--json"])
                assert result.exit_code == 0
                data = _extract_json(result.output)
                assert data.get("cleared") is True
            finally:
                os.chdir(orig)


# ──────────────────────────────────────────────────
# Config CLI
# ──────────────────────────────────────────────────


class TestConfigHelp:
    def test_config_help(self) -> None:
        result = runner.invoke(app, ["config", "--help"])
        assert result.exit_code == 0
        assert "Configuration" in result.output
        assert "validate" in result.output
        assert "diff" in result.output
        assert "export" in result.output
        assert "profile" in result.output


class TestConfigShow:
    def test_show_json(self) -> None:
        result = runner.invoke(app, ["config", "show", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert "app" in data or "broker" in data

    def test_show_section_json(self) -> None:
        result = runner.invoke(app, ["config", "show", "broker", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert "broker" in data


class TestConfigValidate:
    def test_validate(self) -> None:
        result = runner.invoke(app, ["config", "validate"])
        assert result.exit_code == 0

    def test_validate_json(self) -> None:
        result = runner.invoke(app, ["config", "validate", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert "validation_status" in data
        assert "profile" in data
        assert "warnings" in data
        assert "errors" in data


class TestConfigDiff:
    def test_diff(self) -> None:
        result = runner.invoke(app, ["config", "diff"])
        assert result.exit_code == 0

    def test_diff_json(self) -> None:
        result = runner.invoke(app, ["config", "diff", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert "profile" in data
        assert "diffs" in data

    def test_diff_invalid_profile(self) -> None:
        result = runner.invoke(app, ["config", "diff", "--profile", "nonexistent"])
        assert result.exit_code == 1


class TestConfigExport:
    def test_export_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out = str(Path(tmpdir) / "cfg.json")
            result = runner.invoke(app, ["config", "export", "--output", out])
            assert result.exit_code == 0
            assert Path(out).exists()
            with open(out, encoding="utf-8") as f:
                data = json.load(f)
            assert "app" in data
            assert "broker" in data

    def test_export_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out = str(Path(tmpdir) / "cfg.json")
            result = runner.invoke(
                app, ["config", "export", "--output", out, "--format", "yaml"]
            )
            assert result.exit_code == 0
            assert Path(out).exists()


class TestConfigProfile:
    def test_profile_show(self) -> None:
        result = runner.invoke(app, ["config", "profile"])
        assert result.exit_code == 0
        assert "profile" in result.output.lower()

    def test_profile_show_json(self) -> None:
        result = runner.invoke(app, ["config", "profile", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert "profile" in data

    def test_profile_set_valid(self) -> None:
        result = runner.invoke(app, ["config", "profile", "testing"])
        assert result.exit_code == 0

    def test_profile_set_json(self) -> None:
        result = runner.invoke(app, ["config", "profile", "production", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert data.get("set") is True

    def test_profile_set_invalid(self) -> None:
        result = runner.invoke(app, ["config", "profile", "bogus"])
        assert result.exit_code == 1


# ──────────────────────────────────────────────────
# Root command discovers new subcommands
# ──────────────────────────────────────────────────


class TestRootDiscovery:
    def test_root_help_shows_recovery(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "recovery" in result.output

    def test_root_help_shows_all_ops(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "deployment" in result.output
        assert "audit" in result.output
        assert "logs" in result.output
        assert "config" in result.output


# ──────────────────────────────────────────────────
# Additional edge-case tests
# ──────────────────────────────────────────────────


class TestRecoveryEdgeCases:
    def test_retry_all_component_types(self) -> None:
        components = ["pipeline", "broker_session", "market_stream", "execution_engine"]
        for comp in components:
            result = runner.invoke(app, ["recovery", "retry", comp, "test"])
            assert result.exit_code == 0

    def test_checkpoint_save_and_load(self) -> None:
        runner.invoke(
            app,
            [
                "recovery",
                "checkpoint",
                "save",
                "--component",
                "pipeline",
                "--id",
                "e2e-cp",
            ],
        )
        result = runner.invoke(app, ["recovery", "restore", "e2e-cp"])
        assert result.exit_code == 0
        assert "restored" in result.output.lower()

    def test_circuit_reset_not_found_json(self) -> None:
        result = runner.invoke(
            app, ["recovery", "circuit", "reset", "--name", "nope", "--json"]
        )
        assert result.exit_code == 1
        data = _extract_json(result.output)
        assert "error" in data


class TestAuditEdgeCases:
    def test_search_action_filter(self) -> None:
        result = runner.invoke(app, ["audit", "search", "--action", "config", "--json"])
        assert result.exit_code == 0
        data = _extract_json_list(result.output)
        assert isinstance(data, list)

    def test_export_creates_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out = str(Path(tmpdir) / "audit_valid.json")
            runner.invoke(app, ["audit", "export", "--output", out])
            with open(out, encoding="utf-8") as f:
                data = json.load(f)
            assert isinstance(data, list)


class TestConfigEdgeCases:
    def test_validate_returns_warnings(self) -> None:
        result = runner.invoke(app, ["config", "validate", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert isinstance(data.get("warnings"), list)
        assert isinstance(data.get("errors"), list)

    def test_export_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out = str(Path(tmpdir) / "roundtrip.json")
            runner.invoke(app, ["config", "export", "--output", out])
            with open(out, encoding="utf-8") as f:
                data = json.load(f)
            assert "app" in data
            assert "broker" in data
            assert "runtime" in data
