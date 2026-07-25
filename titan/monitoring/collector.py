from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock, Thread
from time import sleep

from titan.monitoring.exceptions import MonitoringCollectionError
from titan.monitoring.models import (
    CollectorDescriptor,
    CollectorType,
    MetricSnapshot,
    MetricValue,
)


@dataclass(slots=True)
class MetricCollector:
    _collectors: dict[str, CollectorDescriptor] = field(
        default_factory=dict, init=False
    )
    _running: bool = False
    _thread: Thread | None = None
    _lock: Lock = field(default_factory=Lock, init=False)
    _total_collections: int = 0
    _failed_collections: int = 0

    @property
    def total_collections(self) -> int:
        with self._lock:
            return self._total_collections

    @property
    def failed_collections(self) -> int:
        with self._lock:
            return self._failed_collections

    def register(
        self,
        name: str,
        collect_fn: Callable[[], tuple[MetricValue, ...]],
        collector_type: CollectorType = CollectorType.PERIODIC,
        interval_seconds: float = 60.0,
        description: str = "",
    ) -> CollectorDescriptor:
        with self._lock:
            if name in self._collectors:
                raise MonitoringCollectionError(
                    f"Collector '{name}' is already registered."
                )

            descriptor = CollectorDescriptor(
                name=name,
                type=collector_type,
                collect=collect_fn,
                interval_seconds=interval_seconds,
                enabled=True,
                description=description,
            )
            self._collectors[name] = descriptor
            return descriptor

    def unregister(self, name: str) -> None:
        with self._lock:
            if name not in self._collectors:
                raise MonitoringCollectionError(
                    f"Collector '{name}' is not registered."
                )
            del self._collectors[name]

    def enable(self, name: str) -> None:
        with self._lock:
            if name not in self._collectors:
                raise MonitoringCollectionError(
                    f"Collector '{name}' is not registered."
                )
            existing = self._collectors[name]
            self._collectors[name] = CollectorDescriptor(
                name=existing.name,
                type=existing.type,
                collect=existing.collect,
                interval_seconds=existing.interval_seconds,
                enabled=True,
                description=existing.description,
            )

    def disable(self, name: str) -> None:
        with self._lock:
            if name not in self._collectors:
                raise MonitoringCollectionError(
                    f"Collector '{name}' is not registered."
                )
            existing = self._collectors[name]
            self._collectors[name] = CollectorDescriptor(
                name=existing.name,
                type=existing.type,
                collect=existing.collect,
                interval_seconds=existing.interval_seconds,
                enabled=False,
                description=existing.description,
            )

    def collect_all(self) -> MetricSnapshot:
        collected: list[MetricValue] = []
        with self._lock:
            descriptors = dict(self._collectors)

        for name, desc in descriptors.items():
            if not desc.enabled:
                continue
            try:
                metrics = desc.collect()
                collected.extend(metrics)
                with self._lock:
                    self._total_collections += 1
            except Exception:
                with self._lock:
                    self._failed_collections += 1
                    self._total_collections += 1

        return MetricSnapshot(
            metrics=tuple(collected),
            timestamp=datetime.now(timezone.utc),
            source="metric_collector",
        )

    def collect_one(self, name: str) -> tuple[MetricValue, ...]:
        with self._lock:
            desc = self._collectors.get(name)
            if desc is None:
                raise MonitoringCollectionError(
                    f"Collector '{name}' is not registered."
                )
            if not desc.enabled:
                return ()

        try:
            metrics = desc.collect()
            with self._lock:
                self._total_collections += 1
            return metrics
        except Exception as exc:
            with self._lock:
                self._failed_collections += 1
                self._total_collections += 1
            raise MonitoringCollectionError(
                f"Collector '{name}' failed: {exc}"
            ) from exc

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = Thread(
                target=self._run_loop, daemon=True, name="metric-collector"
            )
            self._thread.start()

    def stop(self) -> None:
        with self._lock:
            self._running = False

    def _run_loop(self) -> None:
        while True:
            with self._lock:
                if not self._running:
                    return
                descriptors = dict(self._collectors)

            for name, desc in descriptors.items():
                if not desc.enabled or desc.type != CollectorType.PERIODIC:
                    continue
                try:
                    desc.collect()
                    with self._lock:
                        self._total_collections += 1
                except Exception:
                    with self._lock:
                        self._failed_collections += 1
                        self._total_collections += 1

            sleep(1.0)

    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def descriptors(self) -> tuple[CollectorDescriptor, ...]:
        with self._lock:
            return tuple(self._collectors.values())

    def reset(self) -> None:
        with self._lock:
            self._collectors.clear()
            self._total_collections = 0
            self._failed_collections = 0
