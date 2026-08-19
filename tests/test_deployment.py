from __future__ import annotations

import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from titan.deployment.environment import EnvironmentManager
from titan.deployment.exceptions import (
    DeploymentError,
    EnvironmentError,
    StartupError,
    ValidationError,
)
from titan.deployment.health import DeploymentHealthService
from titan.deployment.manager import DeploymentManager
from titan.deployment.models import (
    BackupManifest,
    DeploymentEnvironment,
    DeploymentHealthReport,
    DeploymentReport,
    DeploymentStatus,
    EnvironmentReport,
    StartupReport,
    StartupStep,
    SubsystemHealth,
    SubsystemStatus,
    VersionInfo,
)
from titan.deployment.service import ProductionValidator
from titan.deployment.startup import StartupManager, build_default_steps
from titan.deployment.version import VersionManager

# ── Models ──


class TestDeploymentEnvironment:
    def test_enum_values(self) -> None:
        assert DeploymentEnvironment.DEVELOPMENT.value == "development"
        assert DeploymentEnvironment.PRODUCTION.value == "production"
        assert DeploymentEnvironment.PAPER_TRADING.value == "paper"

    def test_all_values(self) -> None:
        envs = list(DeploymentEnvironment)
        assert len(envs) == 5


class TestDeploymentStatus:
    def test_enum_values(self) -> None:
        assert DeploymentStatus.RUNNING.value == "running"
        assert DeploymentStatus.STOPPED.value == "stopped"
        assert DeploymentStatus.ERROR.value == "error"


class TestSubsystemStatus:
    def test_enum_values(self) -> None:
        assert SubsystemStatus.HEALTHY.value == "healthy"
        assert SubsystemStatus.UNHEALTHY.value == "unhealthy"


class TestVersionInfo:
    def test_defaults(self) -> None:
        info = VersionInfo()
        assert info.version == "1.0.0"
        assert info.build_number == ""
        assert info.git_commit == ""

    def test_frozen(self) -> None:
        info = VersionInfo(version="2.0.0")
        with pytest.raises(AttributeError):
            info.version = "3.0.0"  # type: ignore[misc]


class TestEnvironmentReport:
    def test_defaults(self) -> None:
        report = EnvironmentReport()
        assert report.environment == DeploymentEnvironment.DEVELOPMENT
        assert report.config_loaded is False
        assert report.warnings == ()
        assert report.errors == ()


class TestStartupReport:
    def test_defaults(self) -> None:
        report = StartupReport()
        assert report.success is False
        assert report.steps == ()
        assert report.total_duration_ms == 0.0


class TestStartupStep:
    def test_creation(self) -> None:
        step = StartupStep(name="test", success=True, duration_ms=10.5)
        assert step.name == "test"
        assert step.success is True
        assert step.duration_ms == 10.5

    def test_frozen(self) -> None:
        step = StartupStep(name="x", success=True)
        with pytest.raises(AttributeError):
            step.name = "y"  # type: ignore[misc]


class TestSubsystemHealth:
    def test_defaults(self) -> None:
        h = SubsystemHealth(name="runtime")
        assert h.name == "runtime"
        assert h.status == SubsystemStatus.UNKNOWN


class TestDeploymentHealthReport:
    def test_defaults(self) -> None:
        report = DeploymentHealthReport()
        assert report.overall_status == SubsystemStatus.UNKNOWN
        assert report.readiness is False


class TestDeploymentReport:
    def test_defaults(self) -> None:
        report = DeploymentReport()
        assert report.status == DeploymentStatus.STOPPED
        assert report.environment == DeploymentEnvironment.DEVELOPMENT


class TestBackupManifest:
    def test_creation(self) -> None:
        manifest = BackupManifest(
            backup_id="backup-001",
            timestamp=datetime.now(UTC),
            components=("data",),
        )
        assert manifest.backup_id == "backup-001"
        assert manifest.success is True


# ── Exceptions ──


class TestExceptions:
    def test_hierarchy(self) -> None:
        assert issubclass(EnvironmentError, DeploymentError)
        assert issubclass(StartupError, DeploymentError)
        assert issubclass(ValidationError, DeploymentError)
        assert issubclass(DeploymentError, Exception)


# ── VersionManager ──


class TestVersionManager:
    def teardown_method(self) -> None:
        VersionManager.reset_instance()

    def test_singleton(self) -> None:
        m1 = VersionManager.instance()
        m2 = VersionManager.instance()
        assert m1 is m2

    def test_version(self) -> None:
        vm = VersionManager()
        info = vm.get()
        assert info.version
        assert info.python_version
        assert info.platform

    def test_to_dict(self) -> None:
        vm = VersionManager()
        d = vm.to_dict()
        assert "version" in d
        assert "python_version" in d
        assert "platform" in d

    def test_property(self) -> None:
        vm = VersionManager()
        assert vm.version == vm.get().version


# ── EnvironmentManager ──


class TestEnvironmentManager:
    def test_resolve_development(self) -> None:
        em = EnvironmentManager()
        env = em.resolve("development")
        assert env == DeploymentEnvironment.DEVELOPMENT

    def test_resolve_production(self) -> None:
        em = EnvironmentManager()
        env = em.resolve("production")
        assert env == DeploymentEnvironment.PRODUCTION

    def test_resolve_aliases(self) -> None:
        em = EnvironmentManager()
        assert em.resolve("dev") == DeploymentEnvironment.DEVELOPMENT
        assert em.resolve("prod") == DeploymentEnvironment.PRODUCTION
        assert em.resolve("test") == DeploymentEnvironment.TESTING
        assert em.resolve("paper") == DeploymentEnvironment.PAPER_TRADING
        assert em.resolve("backtest") == DeploymentEnvironment.BACKTESTING

    def test_resolve_unknown_raises(self) -> None:
        em = EnvironmentManager()
        with pytest.raises(EnvironmentError):
            em.resolve("nonexistent")

    def test_resolve_from_env_var(self) -> None:
        os.environ["TITAN_ENVIRONMENT"] = "production"
        try:
            em = EnvironmentManager()
            env = em.resolve()
            assert env == DeploymentEnvironment.PRODUCTION
        finally:
            del os.environ["TITAN_ENVIRONMENT"]

    def test_resolve_default(self) -> None:
        os.environ.pop("TITAN_ENVIRONMENT", None)
        em = EnvironmentManager()
        env = em.resolve()
        assert env == DeploymentEnvironment.DEVELOPMENT

    def test_validate(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "data").mkdir()
            Path(tmpdir, "logs").mkdir()
            em = EnvironmentManager(tmpdir)
            report = em.validate(DeploymentEnvironment.DEVELOPMENT)
            assert report.environment == DeploymentEnvironment.DEVELOPMENT
            assert report.python_version_ok is True
            assert report.dependencies_ok is True

    def test_ensure_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            em = EnvironmentManager(tmpdir)
            em.ensure_directories()
            assert (Path(tmpdir) / "data").exists()
            assert (Path(tmpdir) / "logs").exists()


# ── StartupManager ──


class TestStartupManager:
    def test_empty_run(self) -> None:
        sm = StartupManager()
        sm.set_environment(DeploymentEnvironment.DEVELOPMENT)
        result = sm.run()
        assert result.success is True
        assert result.steps == ()

    def test_successful_step(self) -> None:
        sm = StartupManager()
        sm.add_step("step1", lambda: None)
        result = sm.run()
        assert result.success is True
        assert len(result.steps) == 1
        assert result.steps[0].success is True

    def test_failing_step(self) -> None:
        sm = StartupManager()
        sm.add_step("ok", lambda: None)
        sm.add_step("fail", lambda: (_ for _ in ()).throw(ValueError("boom")))
        result = sm.run()
        assert result.success is False
        assert len(result.steps) == 2
        assert result.steps[1].success is False
        assert "boom" in result.steps[1].message

    def test_stops_on_first_failure(self) -> None:
        sm = StartupManager()
        sm.add_step("ok", lambda: None)
        sm.add_step("fail", lambda: (_ for _ in ()).throw(RuntimeError("x")))
        sm.add_step("never", lambda: None)
        result = sm.run()
        assert len(result.steps) == 2

    def test_step_count(self) -> None:
        sm = StartupManager()
        sm.add_step("a", lambda: None)
        sm.add_step("b", lambda: None)
        assert sm.step_count == 2

    def test_clear(self) -> None:
        sm = StartupManager()
        sm.add_step("a", lambda: None)
        sm.clear()
        assert sm.step_count == 0

    def test_default_steps(self) -> None:
        steps = build_default_steps()
        assert len(steps) > 0
        names = [s[0] for s in steps]
        assert "validate_configuration" in names
        assert "initialize_logging" in names


# ── ProductionValidator ──


class TestProductionValidator:
    def test_validate_all_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "data").mkdir()
            Path(tmpdir, "logs").mkdir()
            pv = ProductionValidator(tmpdir)
            report = EnvironmentReport(
                python_version_ok=True,
                dependencies_ok=True,
                config_valid=True,
                directories_verified=True,
            )
            errors = pv.validate_all(report)
            assert errors == []

    def test_validate_strict_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "data").mkdir()
            Path(tmpdir, "logs").mkdir()
            pv = ProductionValidator(tmpdir)
            report = EnvironmentReport(
                python_version_ok=True,
                dependencies_ok=True,
                config_valid=True,
                directories_verified=True,
            )
            pv.validate_strict(report)

    def test_validate_strict_fails(self) -> None:
        pv = ProductionValidator()
        report = EnvironmentReport(python_version_ok=False)
        with pytest.raises(ValidationError):
            pv.validate_strict(report)

    def test_disk_space_check(self) -> None:
        pv = ProductionValidator()
        assert pv.check_disk_space(1) is True

    def test_port_available(self) -> None:
        pv = ProductionValidator()
        result = pv.check_port_available(19999)
        assert isinstance(result, bool)

    def test_validation_report(self) -> None:
        pv = ProductionValidator()
        report = EnvironmentReport(python_version_ok=True, dependencies_ok=True)
        result = pv.generate_validation_report(report)
        assert "valid" in result
        assert "python_ok" in result
        assert "errors" in result


# ── DeploymentHealthService ──


class TestDeploymentHealthService:
    def test_register_and_report(self) -> None:
        hs = DeploymentHealthService()
        hs.register_subsystem("test")
        hs.report_status("test", SubsystemStatus.HEALTHY)
        report = hs.generate_report()
        assert report.overall_status == SubsystemStatus.HEALTHY
        assert len(report.subsystems) == 1

    def test_unhealthy_overall(self) -> None:
        hs = DeploymentHealthService()
        hs.register_subsystem("a")
        hs.register_subsystem("b")
        hs.report_status("a", SubsystemStatus.HEALTHY)
        hs.report_status("b", SubsystemStatus.UNHEALTHY)
        report = hs.generate_report()
        assert report.overall_status == SubsystemStatus.UNHEALTHY

    def test_degraded_overall(self) -> None:
        hs = DeploymentHealthService()
        hs.register_subsystem("a")
        hs.register_subsystem("b")
        hs.report_status("a", SubsystemStatus.HEALTHY)
        hs.report_status("b", SubsystemStatus.DEGRADED)
        report = hs.generate_report()
        assert report.overall_status == SubsystemStatus.DEGRADED

    def test_readiness(self) -> None:
        hs = DeploymentHealthService()
        assert hs.readiness() is False
        hs.mark_startup_complete()
        assert hs.readiness() is True

    def test_readiness_check_failure(self) -> None:
        hs = DeploymentHealthService()
        hs.mark_startup_complete()
        hs.add_readiness_check("fail", lambda: False)
        assert hs.readiness() is False

    def test_liveness(self) -> None:
        hs = DeploymentHealthService()
        assert hs.liveness() is True

    def test_liveness_check_failure(self) -> None:
        hs = DeploymentHealthService()
        hs.add_liveness_check("fail", lambda: False)
        assert hs.liveness() is False

    def test_startup_probe(self) -> None:
        hs = DeploymentHealthService()
        assert hs.startup() is False
        hs.mark_startup_complete()
        assert hs.startup() is True

    def test_mark_start_time(self) -> None:
        hs = DeploymentHealthService()
        hs.mark_start_time()
        report = hs.generate_report()
        assert report.uptime_seconds >= 0

    def test_reset(self) -> None:
        hs = DeploymentHealthService()
        hs.register_subsystem("test")
        hs.report_status("test", SubsystemStatus.HEALTHY)
        hs.mark_startup_complete()
        hs.reset()
        report = hs.generate_report()
        assert len(report.subsystems) == 0
        assert report.startup_complete is False

    def test_empty_report(self) -> None:
        hs = DeploymentHealthService()
        report = hs.generate_report()
        assert report.overall_status == SubsystemStatus.UNKNOWN


# ── DeploymentManager ──


class TestDeploymentManager:
    def teardown_method(self) -> None:
        DeploymentManager.reset_instance()

    def test_singleton(self) -> None:
        m1 = DeploymentManager.instance()
        m2 = DeploymentManager.instance()
        assert m1 is m2

    def test_initial_status(self) -> None:
        dm = DeploymentManager()
        assert dm.status == DeploymentStatus.STOPPED
        assert dm.is_running is False
        assert dm.uptime_seconds == 0.0

    def test_version(self) -> None:
        dm = DeploymentManager()
        v = dm.version()
        assert v.version

    def test_health_service(self) -> None:
        dm = DeploymentManager()
        hs = dm.health()
        assert isinstance(hs, DeploymentHealthService)

    def test_generate_report(self) -> None:
        dm = DeploymentManager()
        report = dm.generate_report()
        assert isinstance(report, DeploymentReport)
        assert report.status == DeploymentStatus.STOPPED

    def test_stop_when_stopped(self) -> None:
        dm = DeploymentManager()
        report = dm.stop()
        assert report.status == DeploymentStatus.STOPPED

    def test_start_with_custom_steps(self) -> None:
        dm = DeploymentManager()
        steps = [("noop", lambda: None)]
        report = dm.start(steps=steps)
        assert report.status == DeploymentStatus.RUNNING
        assert dm.is_running is True

    def test_start_running_raises(self) -> None:
        dm = DeploymentManager()
        dm.start(steps=[("noop", lambda: None)])
        with pytest.raises(DeploymentError):
            dm.start(steps=[("noop", lambda: None)])

    def test_stop_then_start(self) -> None:
        dm = DeploymentManager()
        dm.start(steps=[("noop", lambda: None)])
        assert dm.is_running is True
        dm.stop()
        assert dm.is_running is False
        dm.start(steps=[("noop", lambda: None)])
        assert dm.is_running is True

    def test_restart(self) -> None:
        dm = DeploymentManager()
        dm.start(steps=[("noop", lambda: None)])
        report = dm.restart(steps=[("noop", lambda: None)])
        assert report.status == DeploymentStatus.RUNNING

    def test_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            dm = DeploymentManager(tmpdir)
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()
            (data_dir / "test.txt").write_text("data")
            logs_dir = Path(tmpdir) / "logs"
            logs_dir.mkdir()
            (logs_dir / "titan.log").write_text("log")
            manifest = dm.backup(tmpdir + "/backups")
            assert manifest.success is True
            assert "data" in manifest.components

    def test_thread_safety(self) -> None:
        dm = DeploymentManager()
        errors: list[Exception] = []

        def reporter(n: int) -> None:
            try:
                for _ in range(50):
                    dm.generate_report()
            except Exception as e:
                errors.append(e)

        import threading

        threads = [threading.Thread(target=reporter, args=(t,)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []


# ── Integration ──


class TestIntegration:
    def teardown_method(self) -> None:
        DeploymentManager.reset_instance()
        VersionManager.reset_instance()

    def test_full_lifecycle(self) -> None:
        dm = DeploymentManager()

        report = dm.start(steps=[("init", lambda: None)])
        assert report.status == DeploymentStatus.RUNNING

        health = dm.health().generate_report()
        assert health.startup_complete is True

        version = dm.version()
        assert version.version

        report = dm.stop()
        assert report.status == DeploymentStatus.STOPPED

    def test_dependency_injection(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            dm = DeploymentManager(tmpdir)
            report = dm.start(steps=[("custom", lambda: None)])
            assert report.status == DeploymentStatus.RUNNING
            dm.stop()
