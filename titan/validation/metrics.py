from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReliabilityMetrics:
    availability_percentage: float
    mtbf_seconds: float
    mttr_seconds: float
    recovery_success_rate: float
    heartbeat_stability: float
    scheduler_drift_ms: float
    pipeline_success_rate: float
    journal_integrity_percentage: float
    configuration_success_rate: float
    decision_persistence_rate: float
    trade_persistence_rate: float


@dataclass(frozen=True, slots=True)
class ResourceMetrics:
    cpu_utilization_percent: float
    ram_mb_peak: float
    ram_mb_avg: float
    object_count_peak: int
    garbage_collections: int


@dataclass(frozen=True, slots=True)
class RuntimeLatencyMetrics:
    startup_ms: float
    shutdown_ms: float
    scheduler_jitter_ms: float
    event_latency_ms: float
    decision_latency_ms: float
    journal_latency_ms: float
    replay_latency_ms: float
    recovery_latency_ms: float
