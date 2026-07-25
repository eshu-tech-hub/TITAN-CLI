from __future__ import annotations

import time
from typing import Any, Callable

from titan.deployment.models import (
    DeploymentEnvironment,
    StartupReport,
    StartupStep,
)


class StartupManager:
    """Orchestrates the TITAN startup sequence.

    Executes a ordered list of startup steps, recording the result
    and duration of each.  If any step fails, startup is aborted
    and a failure report is returned.

    Steps are registered via :meth:`add_step` and executed by
    :meth:`run`.  Each step is a callable that raises on failure.
    """

    def __init__(self) -> None:
        self._steps: list[tuple[str, Callable[[], Any]]] = []
        self._environment: DeploymentEnvironment = DeploymentEnvironment.DEVELOPMENT

    def set_environment(self, environment: DeploymentEnvironment) -> None:
        self._environment = environment

    def add_step(self, name: str, fn: Callable[[], Any]) -> None:
        """Register a startup step by name and callable."""
        self._steps.append((name, fn))

    def run(self) -> StartupReport:
        """Execute all registered startup steps sequentially.

        Returns a :class:`StartupReport` with per-step results.
        """
        results: list[StartupStep] = []
        errors: list[str] = []
        overall_start = time.monotonic()

        for name, fn in self._steps:
            step_start = time.monotonic()
            try:
                fn()
                duration = (time.monotonic() - step_start) * 1000
                results.append(
                    StartupStep(name=name, success=True, duration_ms=duration)
                )
            except Exception as exc:
                duration = (time.monotonic() - step_start) * 1000
                msg = str(exc)
                results.append(
                    StartupStep(
                        name=name,
                        success=False,
                        duration_ms=duration,
                        message=msg,
                    )
                )
                errors.append(f"{name}: {msg}")
                break

        total_duration = (time.monotonic() - overall_start) * 1000
        success = len(errors) == 0

        from titan import __version__

        return StartupReport(
            success=success,
            steps=tuple(results),
            total_duration_ms=total_duration,
            environment=self._environment,
            version=__version__,
            errors=tuple(errors),
        )

    @property
    def step_count(self) -> int:
        return len(self._steps)

    def clear(self) -> None:
        self._steps.clear()


def build_default_steps() -> list[tuple[str, Callable[[], Any]]]:
    """Return the standard TITAN startup steps.

    These steps can be registered with a :class:`StartupManager`
    or used as a reference for custom startup sequences.
    """
    steps: list[tuple[str, Callable[[], Any]]] = [
        ("validate_configuration", _step_validate_configuration),
        ("verify_dependencies", _step_verify_dependencies),
        ("ensure_directories", _step_ensure_directories),
        ("initialize_logging", _step_initialize_logging),
        ("initialize_monitoring", _step_initialize_monitoring),
        ("initialize_alerting", _step_initialize_alerting),
        ("initialize_recovery", _step_initialize_recovery),
        ("initialize_audit", _step_initialize_audit),
        ("initialize_runtime", _step_initialize_runtime),
    ]
    return steps


def _step_validate_configuration() -> None:
    from titan.config.manager import ConfigManager

    manager = ConfigManager()
    manager.load_env()
    manager.get_config()


def _step_verify_dependencies() -> None:
    required = ["typer", "rich", "loguru"]
    missing: list[str] = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        raise ImportError(f"Missing required dependencies: {', '.join(missing)}")


def _step_ensure_directories() -> None:
    from pathlib import Path

    for dirname in ("data", "logs"):
        Path(dirname).mkdir(parents=True, exist_ok=True)


def _step_initialize_logging() -> None:
    from titan.logging.manager import LoggerManager

    LoggerManager.instance()


def _step_initialize_monitoring() -> None:
    from titan.monitoring.manager import MonitoringManager

    MonitoringManager()


def _step_initialize_alerting() -> None:
    from titan.alerting.manager import AlertManager

    AlertManager()


def _step_initialize_recovery() -> None:
    from titan.recovery.manager import RecoveryManager

    RecoveryManager()


def _step_initialize_audit() -> None:
    from titan.audit.manager import AuditManager

    AuditManager()


def _step_initialize_runtime() -> None:
    pass
