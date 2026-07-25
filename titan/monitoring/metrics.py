from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from statistics import mean
from threading import Lock

from titan.monitoring.exceptions import MonitoringCollectionError
from titan.monitoring.models import (
    MetricSnapshot,
    MetricValue,
)


@dataclass(slots=True)
class MetricsRegistry:
    _metrics: dict[str, list[MetricValue]] = field(default_factory=dict, init=False)
    _lock: Lock = field(default_factory=Lock, init=False)

    def record(self, metric: MetricValue) -> None:
        with self._lock:
            name = metric.name
            if name not in self._metrics:
                self._metrics[name] = []
            self._metrics[name].append(metric)

    def record_many(self, metrics: tuple[MetricValue, ...]) -> None:
        with self._lock:
            for m in metrics:
                name = m.name
                if name not in self._metrics:
                    self._metrics[name] = []
                self._metrics[name].append(m)

    def snapshot(self) -> MetricSnapshot:
        with self._lock:
            all_metrics: list[MetricValue] = []
            for vals in self._metrics.values():
                all_metrics.extend(vals)
            return MetricSnapshot(
                metrics=tuple(all_metrics),
                timestamp=datetime.now(timezone.utc),
                source="metrics_registry",
            )

    def latest(self, name: str) -> MetricValue | None:
        with self._lock:
            vals = self._metrics.get(name)
            if not vals:
                return None
            return vals[-1]

    def latest_values(self) -> dict[str, float]:
        with self._lock:
            return {
                name: vals[-1].value for name, vals in self._metrics.items() if vals
            }

    def range(self, name: str, since: datetime) -> tuple[MetricValue, ...]:
        with self._lock:
            vals = self._metrics.get(name, [])
            return tuple(v for v in vals if v.timestamp >= since)

    def clear(self) -> None:
        with self._lock:
            self._metrics.clear()

    def count(self) -> int:
        with self._lock:
            return sum(len(v) for v in self._metrics.values())

    def metric_names(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._metrics.keys()))


@dataclass(slots=True)
class MetricAggregator:
    _registry: MetricsRegistry = field(default_factory=MetricsRegistry)
    _lock: Lock = field(default_factory=Lock, init=False)

    def aggregate(self, metric_name: str) -> dict[str, float]:
        with self._lock:
            latest = self._registry.latest(metric_name)
            if latest is None:
                return {
                    "current": 0.0,
                    "min": 0.0,
                    "max": 0.0,
                    "avg": 0.0,
                    "count": 0.0,
                }

            vals = self._registry.range(
                metric_name, datetime(1970, 1, 1, tzinfo=timezone.utc)
            )
            if not vals:
                return {
                    "current": 0.0,
                    "min": 0.0,
                    "max": 0.0,
                    "avg": 0.0,
                    "count": 0.0,
                }

            values = [v.value for v in vals]
            return {
                "current": latest.value,
                "min": min(values),
                "max": max(values),
                "avg": mean(values),
                "count": float(len(values)),
            }

    def record(self, metric: MetricValue) -> None:
        self._registry.record(metric)

    def snapshot(self) -> MetricSnapshot:
        return self._registry.snapshot()

    def clear(self) -> None:
        self._registry.clear()


@dataclass(slots=True)
class MetricsEngine:
    _aggregator: MetricAggregator = field(default_factory=MetricAggregator)
    _collectors: dict[str, Callable[[], tuple[MetricValue, ...]]] = field(
        default_factory=dict, init=False
    )
    _lock: Lock = field(default_factory=Lock, init=False)

    def register_collector(
        self, name: str, collect_fn: Callable[[], tuple[MetricValue, ...]]
    ) -> None:
        with self._lock:
            self._collectors[name] = collect_fn

    def unregister_collector(self, name: str) -> None:
        with self._lock:
            self._collectors.pop(name, None)

    def collect_all(self) -> MetricSnapshot:
        collected: list[MetricValue] = []
        with self._lock:
            collectors = dict(self._collectors)

        for name, fn in collectors.items():
            try:
                metrics = fn()
                collected.extend(metrics)
                for m in metrics:
                    self._aggregator.record(m)
            except Exception as exc:
                raise MonitoringCollectionError(
                    f"Collector '{name}' failed: {exc}"
                ) from exc

        return MetricSnapshot(
            metrics=tuple(collected),
            timestamp=datetime.now(timezone.utc),
            source="metrics_engine",
        )

    def snapshot(self) -> MetricSnapshot:
        return self._aggregator.snapshot()

    def aggregate(self, metric_name: str) -> dict[str, float]:
        return self._aggregator.aggregate(metric_name)

    def clear(self) -> None:
        self._aggregator.clear()
