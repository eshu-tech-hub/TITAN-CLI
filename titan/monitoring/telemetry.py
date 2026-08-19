from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from typing import Any

from titan.monitoring.exceptions import MonitoringStorageError
from titan.monitoring.health import HealthEngine
from titan.monitoring.metrics import MetricsRegistry
from titan.monitoring.models import (
    MetricValue,
    Subsystem,
    TelemetrySnapshot,
)


@dataclass(slots=True)
class TelemetryManager:
    _metrics: MetricsRegistry = field(default_factory=MetricsRegistry)
    _health: HealthEngine = field(default_factory=HealthEngine)
    _snapshots: list[TelemetrySnapshot] = field(default_factory=list, init=False)
    _exporters: list[Callable[[TelemetrySnapshot], None]] = field(
        default_factory=list, init=False
    )
    _failed_collections: int = 0
    _total_collections: int = 0
    _lock: Lock = field(default_factory=Lock, init=False)

    @property
    def metrics(self) -> MetricsRegistry:
        return self._metrics

    @property
    def health(self) -> HealthEngine:
        return self._health

    def register_exporter(self, exporter: Callable[[TelemetrySnapshot], None]) -> None:
        with self._lock:
            self._exporters.append(exporter)

    def unregister_exporter(
        self, exporter: Callable[[TelemetrySnapshot], None]
    ) -> None:
        with self._lock:
            self._exporters = [e for e in self._exporters if e is not exporter]

    def record_metric(self, metric: MetricValue) -> None:
        self._metrics.record(metric)

    def record_metrics(self, metrics: tuple[MetricValue, ...]) -> None:
        self._metrics.record_many(metrics)

    def report_health(
        self,
        subsystem: Subsystem,
        status: str,
        message: str = "",
        latency_ms: float = 0.0,
        failures: int = 0,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        from titan.monitoring.models import HealthStatus as HS

        hs = HS.HEALTHY
        for candidate in HS:
            if candidate.value == status:
                hs = candidate
                break

        if not self._health.is_registered(subsystem):
            self._health.register(subsystem)

        self._health.report(
            subsystem=subsystem,
            status=hs,
            message=message,
            latency_ms=latency_ms,
            failures=failures,
            metadata=metadata,
        )

    def collect_snapshot(self) -> TelemetrySnapshot:
        with self._lock:
            try:
                metric_snapshot = self._metrics.snapshot()
                system_health = self._health.evaluate()
                self._total_collections += 1
            except Exception as exc:
                self._failed_collections += 1
                self._total_collections += 1
                raise MonitoringStorageError(
                    f"Failed to collect telemetry snapshot: {exc}"
                ) from exc

            snapshot = TelemetrySnapshot(
                metrics=metric_snapshot.metrics,
                health=system_health,
                failed_collections=self._failed_collections,
                total_collections=self._total_collections,
                timestamp=datetime.now(UTC),
            )

            self._snapshots.append(snapshot)

            for exporter in self._exporters:
                try:
                    exporter(snapshot)
                except Exception:
                    pass

            return snapshot

    def latest_snapshot(self) -> TelemetrySnapshot | None:
        with self._lock:
            if not self._snapshots:
                return None
            return self._snapshots[-1]

    def snapshots(self, count: int = 10) -> tuple[TelemetrySnapshot, ...]:
        with self._lock:
            return tuple(self._snapshots[-count:])

    def current_status(self) -> TelemetrySnapshot:
        metric_snapshot = self._metrics.snapshot()
        system_health = self._health.evaluate()
        return TelemetrySnapshot(
            metrics=metric_snapshot.metrics,
            health=system_health,
            failed_collections=self._failed_collections,
            total_collections=self._total_collections,
            timestamp=datetime.now(UTC),
        )

    def reset(self) -> None:
        with self._lock:
            self._metrics.clear()
            self._health.reset()
            self._snapshots.clear()
            self._failed_collections = 0
            self._total_collections = 0

    def clear_snapshots(self) -> None:
        with self._lock:
            self._snapshots.clear()
