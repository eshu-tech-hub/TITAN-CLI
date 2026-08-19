from dataclasses import dataclass
from datetime import datetime

from titan.validation.metrics import (
    ReliabilityMetrics,
    ResourceMetrics,
    RuntimeLatencyMetrics,
)


@dataclass(frozen=True, slots=True)
class PerformanceReport:
    timestamp: datetime
    run_duration_seconds: float
    latencies: RuntimeLatencyMetrics
    resources: ResourceMetrics
    recommendations: list[str]

    def to_markdown(self) -> str:
        return f"# TITAN Performance Baseline Report\nGenerated: {self.timestamp.isoformat()}\n..."


@dataclass(frozen=True, slots=True)
class BurnInReport:
    timestamp: datetime
    duration_hours: float
    faults_injected: int
    recoveries_successful: int
    failures_observed: list[str]
    final_assessment: str

    def to_markdown(self) -> str:
        return f"# TITAN Burn-In Report\nGenerated: {self.timestamp.isoformat()}\n..."


@dataclass(frozen=True, slots=True)
class StressReport:
    timestamp: datetime
    events_processed: int
    peak_throughput_eps: float
    bottlenecks_detected: list[str]
    final_assessment: str

    def to_markdown(self) -> str:
        return (
            f"# TITAN Stress Test Report\nGenerated: {self.timestamp.isoformat()}\n..."
        )


@dataclass(frozen=True, slots=True)
class ReliabilityReport:
    timestamp: datetime
    metrics: ReliabilityMetrics
    final_assessment: str

    def to_markdown(self) -> str:
        return (
            f"# TITAN Reliability Report\nGenerated: {self.timestamp.isoformat()}\n..."
        )


@dataclass(frozen=True, slots=True)
class ValidationReport:
    timestamp: datetime
    performance: PerformanceReport
    burn_in: BurnInReport
    stress: StressReport
    reliability: ReliabilityReport
    overall_status: str
