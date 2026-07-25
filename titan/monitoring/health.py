from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from titan.monitoring.exceptions import MonitoringHealthError
from titan.monitoring.models import (
    HealthStatus,
    Subsystem,
    SubsystemHealth,
    SystemHealth,
)


@dataclass(slots=True)
class HealthEngine:
    _subsystems: dict[Subsystem, SubsystemHealth] = field(
        default_factory=dict, init=False
    )
    _lock: Lock = field(default_factory=Lock, init=False)

    def register(
        self,
        subsystem: Subsystem,
        initial_status: HealthStatus = HealthStatus.HEALTHY,
    ) -> SubsystemHealth:
        with self._lock:
            if subsystem in self._subsystems:
                raise MonitoringHealthError(
                    f"Subsystem '{subsystem.value}' is already registered."
                )

            health = SubsystemHealth(
                subsystem=subsystem,
                status=initial_status,
                last_check=datetime.now(timezone.utc),
            )
            self._subsystems[subsystem] = health
            return health

    def unregister(self, subsystem: Subsystem) -> None:
        with self._lock:
            if subsystem not in self._subsystems:
                raise MonitoringHealthError(
                    f"Subsystem '{subsystem.value}' is not registered."
                )
            del self._subsystems[subsystem]

    def report(
        self,
        subsystem: Subsystem,
        status: HealthStatus,
        message: str = "",
        latency_ms: float = 0.0,
        failures: int = 0,
        metadata: Mapping[str, Any] | None = None,
    ) -> SubsystemHealth:
        with self._lock:
            if subsystem not in self._subsystems:
                raise MonitoringHealthError(
                    f"Subsystem '{subsystem.value}' is not registered. Call register() first."
                )

            existing = self._subsystems[subsystem]
            last_healthy = existing.last_healthy
            if status == HealthStatus.HEALTHY:
                last_healthy = datetime.now(timezone.utc)

            health = SubsystemHealth(
                subsystem=subsystem,
                status=status,
                message=message,
                last_healthy=last_healthy,
                last_check=datetime.now(timezone.utc),
                latency_ms=latency_ms,
                failures=failures,
                metadata=metadata or {},
            )
            self._subsystems[subsystem] = health
            return health

    def get(self, subsystem: Subsystem) -> SubsystemHealth | None:
        with self._lock:
            return self._subsystems.get(subsystem)

    def all_health(self) -> tuple[SubsystemHealth, ...]:
        with self._lock:
            return tuple(self._subsystems.values())

    def evaluate(self) -> SystemHealth:
        with self._lock:
            subsystems = list(self._subsystems.values())
            if not subsystems:
                return SystemHealth()

            healthy = sum(1 for s in subsystems if s.status == HealthStatus.HEALTHY)
            warning = sum(1 for s in subsystems if s.status == HealthStatus.WARNING)
            critical = sum(1 for s in subsystems if s.status == HealthStatus.CRITICAL)
            offline = sum(1 for s in subsystems if s.status == HealthStatus.OFFLINE)

            if critical > 0 or offline > 0:
                overall = HealthStatus.CRITICAL
            elif warning > 0:
                overall = HealthStatus.WARNING
            else:
                overall = HealthStatus.HEALTHY

            return SystemHealth(
                subsystems=tuple(subsystems),
                overall=overall,
                healthy_count=healthy,
                warning_count=warning,
                critical_count=critical,
                offline_count=offline,
                timestamp=datetime.now(timezone.utc),
            )

    def reset(self) -> None:
        with self._lock:
            self._subsystems.clear()

    def is_registered(self, subsystem: Subsystem) -> bool:
        with self._lock:
            return subsystem in self._subsystems
