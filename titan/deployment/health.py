from __future__ import annotations

import time
from threading import Lock
from typing import Callable

from titan.deployment.models import (
    DeploymentHealthReport,
    SubsystemHealth,
    SubsystemStatus,
)


class DeploymentHealthService:
    """Deployment-level health service providing readiness, liveness,
    and startup probes.

    This is distinct from the runtime-level :class:`HealthCheck`.
    It operates at the deployment infrastructure layer.
    """

    def __init__(self) -> None:
        self._subsystems: dict[str, SubsystemHealth] = {}
        self._readiness_checks: list[tuple[str, Callable[[], bool]]] = []
        self._liveness_checks: list[tuple[str, Callable[[], bool]]] = []
        self._startup_complete = False
        self._start_time: float = 0.0
        self._lock = Lock()

    def register_subsystem(self, name: str) -> None:
        with self._lock:
            self._subsystems[name] = SubsystemHealth(
                name=name, status=SubsystemStatus.UNKNOWN
            )

    def report_status(
        self,
        name: str,
        status: SubsystemStatus,
        message: str = "",
        latency_ms: float = 0.0,
    ) -> None:
        with self._lock:
            self._subsystems[name] = SubsystemHealth(
                name=name,
                status=status,
                message=message,
                latency_ms=latency_ms,
            )

    def add_readiness_check(self, name: str, fn: Callable[[], bool]) -> None:
        self._readiness_checks.append((name, fn))

    def add_liveness_check(self, name: str, fn: Callable[[], bool]) -> None:
        self._liveness_checks.append((name, fn))

    def mark_startup_complete(self) -> None:
        self._startup_complete = True

    def mark_start_time(self) -> None:
        self._start_time = time.monotonic()

    def readiness(self) -> bool:
        """Evaluate readiness probe."""
        if not self._startup_complete:
            return False
        for _name, fn in self._readiness_checks:
            try:
                if not fn():
                    return False
            except Exception:
                return False
        return True

    def liveness(self) -> bool:
        """Evaluate liveness probe."""
        for _name, fn in self._liveness_checks:
            try:
                if not fn():
                    return False
            except Exception:
                return False
        return True

    def startup(self) -> bool:
        """Evaluate startup probe."""
        return self._startup_complete

    def generate_report(self) -> DeploymentHealthReport:
        """Generate a full deployment health report."""
        with self._lock:
            subsystems = tuple(self._subsystems.values())

        statuses = [s.status for s in subsystems]
        if not statuses:
            overall = SubsystemStatus.UNKNOWN
        elif all(s == SubsystemStatus.HEALTHY for s in statuses):
            overall = SubsystemStatus.HEALTHY
        elif any(s == SubsystemStatus.UNHEALTHY for s in statuses):
            overall = SubsystemStatus.UNHEALTHY
        elif any(s == SubsystemStatus.DEGRADED for s in statuses):
            overall = SubsystemStatus.DEGRADED
        else:
            overall = SubsystemStatus.UNKNOWN

        uptime = 0.0
        if self._start_time > 0:
            uptime = time.monotonic() - self._start_time

        return DeploymentHealthReport(
            overall_status=overall,
            subsystems=subsystems,
            uptime_seconds=uptime,
            readiness=self.readiness(),
            liveness=self.liveness(),
            startup_complete=self._startup_complete,
        )

    def reset(self) -> None:
        with self._lock:
            self._subsystems.clear()
        self._startup_complete = False
        self._start_time = 0.0
