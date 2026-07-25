from __future__ import annotations

import time
import threading
from datetime import datetime, timezone
from typing import Any, Callable

from titan.deployment.environment import EnvironmentManager
from titan.deployment.exceptions import DeploymentError, ShutdownError, StartupError
from titan.deployment.health import DeploymentHealthService
from titan.deployment.models import (
    BackupManifest,
    DeploymentEnvironment,
    DeploymentReport,
    DeploymentStatus,
    SubsystemStatus,
    VersionInfo,
)
from titan.deployment.startup import StartupManager, build_default_steps
from titan.deployment.service import ProductionValidator
from titan.deployment.version import VersionManager


class DeploymentManager:
    """Single authority for TITAN's production lifecycle.

    All runtime lifecycle operations must flow through this manager.
    No subsystem should implement independent startup or shutdown.

    Responsibilities:
        - Start TITAN (full startup sequence).
        - Stop TITAN (graceful shutdown).
        - Restart TITAN.
        - Report status, health, and version.
        - Backup and restore.
    """

    _instance: DeploymentManager | None = None
    _instance_lock = threading.Lock()

    def __init__(self, root_dir: str | None = None) -> None:
        self._env_manager = EnvironmentManager(root_dir)
        self._startup_manager = StartupManager()
        self._health_service = DeploymentHealthService()
        self._validator = ProductionValidator(root_dir)
        self._version_manager = VersionManager.instance()

        self._status: DeploymentStatus = DeploymentStatus.STOPPED
        self._environment: DeploymentEnvironment = DeploymentEnvironment.DEVELOPMENT
        self._start_time: float = 0.0
        self._lock = threading.Lock()

        self._register_default_health_checks()

    @classmethod
    def instance(cls, root_dir: str | None = None) -> DeploymentManager:
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls(root_dir)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        with cls._instance_lock:
            cls._instance = None

    # ── Lifecycle ──

    def start(
        self,
        profile: str | None = None,
        steps: list[tuple[str, Callable[[], Any]]] | None = None,
    ) -> DeploymentReport:
        """Start TITAN with the full deployment sequence."""
        with self._lock:
            if self._status == DeploymentStatus.RUNNING:
                raise DeploymentError("TITAN is already running.")
            self._status = DeploymentStatus.STARTING

        try:
            self._environment = self._env_manager.resolve(profile)
            self._startup_manager.set_environment(self._environment)

            report = self._env_manager.validate(self._environment)
            if report.errors:
                self._status = DeploymentStatus.ERROR
                raise StartupError(
                    f"Environment validation failed: {'; '.join(report.errors[:3])}"
                )

            self._env_manager.ensure_directories()

            if self._environment == DeploymentEnvironment.PRODUCTION:
                self._validator.validate_strict(report)

            startup_steps = steps or build_default_steps()
            for name, fn in startup_steps:
                self._startup_manager.add_step(name, fn)

            self._health_service.mark_start_time()
            result = self._startup_manager.run()

            if not result.success:
                self._status = DeploymentStatus.ERROR
                raise StartupError(
                    f"Startup failed at step '{result.errors[0]}': "
                    + "; ".join(result.errors)
                )

            self._status = DeploymentStatus.RUNNING
            self._start_time = time.monotonic()
            self._health_service.mark_startup_complete()
            self._set_all_subsystems_healthy()

            return self._build_startup_report(result)

        except StartupError, DeploymentError:
            raise
        except Exception as exc:
            self._status = DeploymentStatus.ERROR
            raise StartupError(f"Unexpected startup error: {exc}") from exc

    def stop(self) -> DeploymentReport:
        """Stop TITAN gracefully."""
        with self._lock:
            if self._status == DeploymentStatus.STOPPED:
                return self.generate_report()
            self._status = DeploymentStatus.STOPPING

        try:
            self._health_service.reset()
            self._startup_manager.clear()

            self._status = DeploymentStatus.STOPPED
            return self.generate_report()

        except Exception as exc:
            self._status = DeploymentStatus.ERROR
            raise ShutdownError(f"Shutdown error: {exc}") from exc

    def restart(
        self,
        profile: str | None = None,
        steps: list[tuple[str, Callable[[], Any]]] | None = None,
    ) -> DeploymentReport:
        """Restart TITAN."""
        self.stop()
        return self.start(profile=profile, steps=steps)

    # ── Status & Reporting ──

    @property
    def status(self) -> DeploymentStatus:
        return self._status

    @property
    def is_running(self) -> bool:
        return self._status == DeploymentStatus.RUNNING

    @property
    def uptime_seconds(self) -> float:
        if self._start_time <= 0:
            return 0.0
        return time.monotonic() - self._start_time

    def generate_report(self) -> DeploymentReport:
        health = self._health_service.generate_report()
        return DeploymentReport(
            status=self._status,
            environment=self._environment,
            version=self._version_manager.get(),
            uptime_seconds=self.uptime_seconds,
            start_time=(datetime.now(timezone.utc) if self._start_time > 0 else None),
            health=health,
        )

    def health(self) -> DeploymentHealthService:
        return self._health_service

    def version(self) -> VersionInfo:
        return self._version_manager.get()

    # ── Backup ──

    def backup(self, destination: str) -> BackupManifest:
        """Create a backup of TITAN configuration and data."""
        import shutil
        import uuid
        from pathlib import Path

        dest = Path(destination)
        dest.mkdir(parents=True, exist_ok=True)
        backup_id = f"backup-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
        backup_dir = dest / backup_id
        backup_dir.mkdir(parents=True, exist_ok=True)

        components: list[str] = []
        total_files = 0
        errors: list[str] = []

        for dirname in ("data", "logs"):
            src = Path(dirname)
            if src.exists():
                try:
                    dst = backup_dir / dirname
                    shutil.copytree(str(src), str(dst))
                    components.append(dirname)
                    total_files += sum(1 for _ in dst.rglob("*") if _.is_file())
                except Exception as exc:
                    errors.append(f"{dirname}: {exc}")

        for filename in (".env", ".env.example"):
            src = Path(filename)
            if src.exists():
                try:
                    shutil.copy2(str(src), str(backup_dir / filename))
                    components.append(filename)
                    total_files += 1
                except Exception as exc:
                    errors.append(f"{filename}: {exc}")

        return BackupManifest(
            backup_id=backup_id,
            timestamp=datetime.now(timezone.utc),
            components=tuple(components),
            total_files=total_files,
            destination=str(backup_dir),
            success=len(errors) == 0,
            errors=tuple(errors),
        )

    # ── Internal ──

    def _register_default_health_checks(self) -> None:
        self._health_service.register_subsystem("configuration")
        self._health_service.register_subsystem("logging")
        self._health_service.register_subsystem("monitoring")
        self._health_service.register_subsystem("alerting")
        self._health_service.register_subsystem("recovery")
        self._health_service.register_subsystem("audit")
        self._health_service.register_subsystem("runtime")

    def _set_all_subsystems_healthy(self) -> None:
        for name in (
            "configuration",
            "logging",
            "monitoring",
            "alerting",
            "recovery",
            "audit",
            "runtime",
        ):
            self._health_service.report_status(name, SubsystemStatus.HEALTHY)

    def _build_startup_report(self, result: Any) -> DeploymentReport:
        health = self._health_service.generate_report()
        return DeploymentReport(
            status=self._status,
            environment=self._environment,
            version=self._version_manager.get(),
            uptime_seconds=self.uptime_seconds,
            start_time=datetime.now(timezone.utc),
            health=health,
        )
