import time
import tracemalloc
from collections.abc import Callable
from typing import Any

from titan.validation.metrics import ResourceMetrics


class PerformanceProfiler:
    """Records runtime metrics and resource utilization during validation."""

    def __init__(self):
        self._start_time: float = 0.0
        self._latencies: dict[str, float] = {}

    def start(self) -> None:
        tracemalloc.start()
        self._start_time = time.perf_counter()

    def stop(self) -> ResourceMetrics:
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        return ResourceMetrics(
            cpu_utilization_percent=0.0,  # Simulated placeholder
            ram_mb_peak=peak / (1024 * 1024),
            ram_mb_avg=current / (1024 * 1024),
            object_count_peak=0,
            garbage_collections=0,
        )

    def record_latency(
        self, name: str, func: Callable, *args: Any, **kwargs: Any
    ) -> Any:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        duration = time.perf_counter() - start
        self._latencies[name] = duration * 1000  # Convert to ms
        return result
