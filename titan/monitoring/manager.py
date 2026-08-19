from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock

from titan.monitoring.collector import MetricCollector
from titan.monitoring.dashboard import MonitoringDashboard
from titan.monitoring.health import HealthEngine
from titan.monitoring.metrics import MetricsRegistry
from titan.monitoring.models import (
    CollectorType,
    DashboardStatus,
    HealthStatus,
    MetricValue,
    MonitoringReport,
    Subsystem,
    TelemetrySnapshot,
)
from titan.monitoring.telemetry import TelemetryManager


@dataclass(slots=True)
class MonitoringManager:
    _telemetry: TelemetryManager = field(default_factory=TelemetryManager)
    _collector: MetricCollector = field(default_factory=MetricCollector)
    _dashboard: MonitoringDashboard = field(default_factory=MonitoringDashboard)
    _start_time: datetime = field(default_factory=lambda: datetime.now(UTC), init=False)
    _lock: Lock = field(default_factory=Lock, init=False)

    def __post_init__(self) -> None:
        self._wire_components()

    def _wire_components(self) -> None:
        self.health.register(Subsystem.MONITORING)
        self.health.report(Subsystem.MONITORING, HealthStatus.HEALTHY)

    @property
    def telemetry(self) -> TelemetryManager:
        return self._telemetry

    @property
    def collector(self) -> MetricCollector:
        return self._collector

    @property
    def dashboard(self) -> MonitoringDashboard:
        return self._dashboard

    @property
    def metrics(self) -> MetricsRegistry:
        return self._telemetry.metrics

    @property
    def health(self) -> HealthEngine:
        return self._telemetry.health

    def register_subsystem(self, subsystem: Subsystem) -> None:
        if not self.health.is_registered(subsystem):
            self.health.register(subsystem)

    def register_collector(
        self,
        name: str,
        collect_fn: Callable[[], tuple[MetricValue, ...]],
        collector_type: CollectorType = CollectorType.PERIODIC,
        interval_seconds: float = 60.0,
        description: str = "",
    ) -> None:
        self._collector.register(
            name=name,
            collect_fn=collect_fn,
            collector_type=collector_type,
            interval_seconds=interval_seconds,
            description=description,
        )

    def collect_snapshot(self) -> TelemetrySnapshot:
        collected = self._collector.collect_all()
        for m in collected.metrics:
            self._telemetry.record_metric(m)
        return self._telemetry.collect_snapshot()

    def dashboard_status(self) -> DashboardStatus:
        return self._dashboard.status()

    def generate_report(self) -> MonitoringReport:
        snapshot = self.collect_snapshot()

        warnings: list[str] = []
        recommendations: list[str] = []

        if snapshot.health:
            if snapshot.health.critical_count > 0:
                warnings.append(
                    f"{snapshot.health.critical_count} subsystem(s) in CRITICAL state."
                )
                recommendations.append(
                    "Investigate and resolve critical subsystem failures immediately."
                )
            if snapshot.health.offline_count > 0:
                warnings.append(
                    f"{snapshot.health.offline_count} subsystem(s) are OFFLINE."
                )
                recommendations.append(
                    "Restart offline subsystems and verify connectivity."
                )
            if snapshot.health.warning_count > 0:
                warnings.append(
                    f"{snapshot.health.warning_count} subsystem(s) in WARNING state."
                )
                recommendations.append(
                    "Review warning subsystems for potential issues."
                )

        if snapshot.failed_collections > 0:
            warnings.append(
                f"{snapshot.failed_collections} metric collection(s) failed."
            )
            recommendations.append(
                "Check collector configurations and subsystem availability."
            )

        uptime = (datetime.now(UTC) - self._start_time).total_seconds()
        collector_count = len(self._collector.descriptors())

        return MonitoringReport(
            system_health=snapshot.health,
            metrics=snapshot.metrics,
            warnings=tuple(warnings),
            recommendations=tuple(recommendations),
            collector_count=collector_count,
            failed_collections=snapshot.failed_collections,
            total_collections=snapshot.total_collections,
            uptime_seconds=uptime,
            timestamp=datetime.now(UTC),
        )

    def start(self) -> None:
        self._collector.start()

    def stop(self) -> None:
        self._collector.stop()

    def reset(self) -> None:
        self._telemetry.reset()
        self._collector.reset()
        self._dashboard.reset()
        self._start_time = datetime.now(UTC)
        self.__post_init__()
