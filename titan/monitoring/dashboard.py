from dataclasses import dataclass, field
from datetime import UTC, datetime
from statistics import mean
from threading import Lock

from titan.monitoring.health import HealthEngine
from titan.monitoring.metrics import MetricsRegistry
from titan.monitoring.models import (
    DashboardMetricSummary,
    DashboardStatus,
    SubsystemHealth,
)


@dataclass(slots=True)
class MonitoringDashboard:
    _metrics: MetricsRegistry = field(default_factory=MetricsRegistry)
    _health: HealthEngine = field(default_factory=HealthEngine)
    _failures: list[str] = field(default_factory=list, init=False)
    _start_time: datetime = field(default_factory=lambda: datetime.now(UTC), init=False)
    _lock: Lock = field(default_factory=Lock, init=False)

    def record_failure(self, failure: str) -> None:
        with self._lock:
            self._failures.append(failure)
            if len(self._failures) > 100:
                self._failures = self._failures[-100:]

    def status(self) -> DashboardStatus:
        with self._lock:
            system_health = self._health.evaluate()
            metric_names = self._metrics.metric_names()

            summaries: list[DashboardMetricSummary] = []
            for name in metric_names:
                vals = self._metrics.latest(name)
                if vals is None:
                    continue

                all_for_name = self._metrics.range(
                    name, datetime(1970, 1, 1, tzinfo=UTC)
                )
                values = [v.value for v in all_for_name]
                if not values:
                    continue

                trend = self._compute_trend(values)
                summaries.append(
                    DashboardMetricSummary(
                        name=name,
                        current=vals.value,
                        min=min(values),
                        max=max(values),
                        avg=mean(values),
                        unit=vals.unit,
                        trend=trend,
                    )
                )

            recent_failures = tuple(self._failures[-10:])
            uptime = (datetime.now(UTC) - self._start_time).total_seconds()

            return DashboardStatus(
                system_health=system_health,
                metric_summaries=tuple(summaries),
                recent_failures=recent_failures,
                active_collectors=len(metric_names),
                total_collections=0,
                failed_collections=0,
                uptime_seconds=uptime,
                timestamp=datetime.now(UTC),
            )

    def subsystem_health(self, subsystem_name: str) -> SubsystemHealth | None:
        from titan.monitoring.models import Subsystem

        for sub in Subsystem:
            if sub.value == subsystem_name:
                return self._health.get(sub)
        return None

    def metric_summary(self, name: str) -> DashboardMetricSummary | None:
        latest = self._metrics.latest(name)
        if latest is None:
            return None

        all_for_name = self._metrics.range(name, datetime(1970, 1, 1, tzinfo=UTC))
        values = [v.value for v in all_for_name]
        if not values:
            return None

        trend = self._compute_trend(values)
        return DashboardMetricSummary(
            name=name,
            current=latest.value,
            min=min(values),
            max=max(values),
            avg=mean(values),
            unit=latest.unit,
            trend=trend,
        )

    def recent_failures(self, count: int = 10) -> tuple[str, ...]:
        with self._lock:
            return tuple(self._failures[-count:])

    @staticmethod
    def _compute_trend(values: list[float]) -> str:
        if len(values) < 3:
            return "stable"

        recent = values[-3:]
        if recent[-1] > recent[0] * 1.05:
            return "increasing"
        if recent[-1] < recent[0] * 0.95:
            return "decreasing"
        return "stable"

    def reset(self) -> None:
        with self._lock:
            self._failures.clear()
            self._start_time = datetime.now(UTC)
