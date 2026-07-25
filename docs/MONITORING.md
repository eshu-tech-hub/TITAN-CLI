# TITAN Monitoring & Telemetry Framework

## Overview

The Monitoring Framework is TITAN's centralized operational nervous
system. It continuously measures the health, performance, and
operational state of the platform.

**It does not perform market analysis or trading.**

Every TITAN subsystem reports metrics through this framework. No
module may implement its own monitoring solution.

## Architecture

```
Runtime
   │
   ▼
Metric Collector ──> MetricsRegistry ──> Dashboard
   │                       │
   └──> TelemetryManager ──┤
               │           │
            HealthEngine ──┘
               │
           Subsystems
```

## Module Layout

```
titan/monitoring/
    __init__.py      Public API exports
    models.py        Frozen dataclasses and enums
    exceptions.py    Exception hierarchy
    metrics.py       MetricsRegistry, MetricAggregator, MetricsEngine
    health.py        HealthEngine
    telemetry.py     TelemetryManager
    collector.py     MetricCollector
    dashboard.py     MonitoringDashboard
    manager.py       MonitoringManager (top-level orchestrator)
```

## Quick Start

### Basic Usage

```python
from titan.monitoring import (
    MonitoringManager,
    MetricValue,
    MetricType,
    MetricUnit,
    Subsystem,
)

# Create the manager (all components are wired automatically)
manager = MonitoringManager()

# Register a subsystem for health tracking
manager.register_subsystem(Subsystem.MARKET)

# Register a metric collector
def collect_system_metrics() -> tuple[MetricValue, ...]:
    import psutil
    return (
        MetricValue(
            name="system.cpu.percent",
            value=psutil.cpu_percent(),
            type=MetricType.GAUGE,
            unit=MetricUnit.PERCENT,
            tags={"host": "localhost"},
        ),
        MetricValue(
            name="system.memory.percent",
            value=psutil.virtual_memory().percent,
            type=MetricType.GAUGE,
            unit=MetricUnit.PERCENT,
        ),
    )

manager.register_collector("system", collect_system_metrics)

# Collect a snapshot
snapshot = manager.collect_snapshot()

# Get dashboard status
status = manager.dashboard_status()

# Generate a report
report = manager.generate_report()
```

### Health Reporting

```python
from titan.monitoring import HealthStatus, Subsystem

# A subsystem reports its health
manager.health.report(
    Subsystem.BROKER,
    HealthStatus.HEALTHY,
    latency_ms=12.5,
)

# When something goes wrong:
manager.health.report(
    Subsystem.BROKER,
    HealthStatus.CRITICAL,
    message="Connection lost to upstream API",
    failures=3,
)

# Get system-wide health
system_health = manager.health.evaluate()
print(f"Overall: {system_health.overall}")
print(f"Healthy: {system_health.healthy_count}")
print(f"Warning: {system_health.warning_count}")
print(f"Critical: {system_health.critical_count}")
print(f"Offline: {system_health.offline_count}")
```

### Telemetry Snapshots

```python
# The TelemetryManager stores historical snapshots
manager.telemetry.collect_snapshot()

# Get the latest snapshot
latest = manager.telemetry.latest_snapshot()

# Get recent snapshots
recent = manager.telemetry.snapshots(count=5)

# Register an exporter (e.g., for Prometheus)
def prometheus_exporter(snapshot):
    for metric in snapshot.metrics:
        # Convert to Prometheus format
        pass

manager.telemetry.register_exporter(prometheus_exporter)
```

### Dashboard

```python
# Get current dashboard status
status = manager.dashboard_status()
print(f"Uptime: {status.uptime_seconds:.0f}s")
print(f"Active collectors: {status.active_collectors}")

for summary in status.metric_summaries:
    print(f"{summary.name}: {summary.current} ({summary.trend})")

for failure in status.recent_failures:
    print(f"FAILURE: {failure}")
```

### Reports

```python
# Generate a diagnostic report
report = manager.generate_report()

print(f"Warnings: {report.warnings}")
print(f"Recommendations: {report.recommendations}")
```

## Models

### MetricValue

A single metric measurement.

| Field | Type | Default |
|---|---|---|
| `name` | `str` | required |
| `value` | `float` | required |
| `type` | `MetricType` | `GAUGE` |
| `unit` | `MetricUnit` | `NONE` |
| `tags` | `Mapping[str, str]` | `{}` |
| `timestamp` | `datetime` | `utcnow()` |
| `description` | `str` | `""` |

### MetricType

- `GAUGE` — Point-in-time value (e.g., CPU percent)
- `COUNTER` — Monotonically increasing count (e.g., orders served)
- `HISTOGRAM` — Distribution of values (e.g., latency samples)
- `SUMMARY` — Quantile-based summary

### MetricUnit

`MILLISECONDS`, `SECONDS`, `PERCENT`, `COUNT`, `BYTES`, `MEGABYTES`,
`GIGABYTES`, `BITS_PER_SECOND`, `MEGABITS_PER_SECOND`, `NONE`

### HealthStatus

- `HEALTHY` — Operating normally
- `WARNING` — Degraded but functional
- `CRITICAL` — Not operating correctly
- `OFFLINE` — Not reachable or stopped

### Subsystem Enum

All TITAN subsystems: `MARKET`, `BROKER`, `EXECUTION`, `RISK`,
`PIPELINE`, `PORTFOLIO`, `DECISION`, `RUNTIME`, `EVENTS`,
`INTELLIGENCE`, `TRADING`, `CONFIG`, `MONITORING`, `PAPER`,
`BACKTESTING`.

## Collectors

### Periodic Collectors

Run on a background thread at a configurable interval:

```python
manager.register_collector(
    "latency",
    collect_latency_metrics,
    collector_type=CollectorType.PERIODIC,
    interval_seconds=30.0,
    description="Pipeline and broker latency metrics",
)
```

### Event-Driven Collectors

Triggered by external events (health reported via `TelemetryManager`):

```python
def on_trade_executed(order_id: str, latency_ms: float):
    manager.metrics.record(
        MetricValue(
            name="execution.latency",
            value=latency_ms,
            type=MetricType.HISTOGRAM,
            unit=MetricUnit.MILLISECONDS,
            tags={"order_id": order_id},
        )
    )
```

### Custom Collectors

Any callable returning `tuple[MetricValue, ...]`:

```python
def custom_collector() -> tuple[MetricValue, ...]:
    return (
        MetricValue(name="custom.metric", value=get_value()),
    )
```

### Plugin Architecture

Collectors are registered by name. The `MetricCollector` class
serves as the extension point — third-party code can register
collectors without modifying the framework.

## Health Evaluation

The `HealthEngine.evaluate()` method computes aggregate health:

- **CRITICAL** if any subsystem is CRITICAL or OFFLINE
- **WARNING** if any subsystem is WARNING (and none CRITICAL/OFFLINE)
- **HEALTHY** if all subsystems are HEALTHY

## Metrics

### What to Collect

The framework is designed for these operational metrics:

| Metric | Type | Unit | Description |
|---|---|---|---|
| pipeline.latency | HISTOGRAM | ms | Pipeline execution latency |
| decision.latency | HISTOGRAM | ms | Decision engine latency |
| execution.latency | HISTOGRAM | ms | Execution latency |
| broker.latency | GAUGE | ms | Broker API latency |
| oms.latency | GAUGE | ms | OMS processing latency |
| runtime.latency | GAUGE | ms | Runtime tick latency |
| system.cpu.percent | GAUGE | % | CPU usage |
| system.memory.percent | GAUGE | % | Memory usage |
| system.disk.percent | GAUGE | % | Disk usage |
| system.network.bytes | COUNTER | bytes | Network I/O |
| pipelines.active | GAUGE | count | Active pipelines |
| positions.active | GAUGE | count | Active positions |
| orders.per_minute | GAUGE | count | Orders per minute |
| signals.per_minute | GAUGE | count | Signals per minute |
| trades.per_day | COUNTER | count | Trades today |

## Future Exporters

The `TelemetryManager` exporter interface (`Callable[[TelemetrySnapshot], None]`)
supports:

- **Prometheus** — HTTP endpoint exposing metric families
- **Grafana** — SimpleJSON datasource or plugin
- **OpenTelemetry Metrics** — OTLP gRPC/HTTP export
- **CloudWatch** — `put_metric_data` via boto3
- **Azure Monitor** — Custom metrics via Azure SDK
- **Distributed Workers** — gRPC aggregation service

## Configuration

The monitoring framework is configured via `MonitoringConfig` in
`titan/config/models.py`:

```python
@dataclass(frozen=True, slots=True)
class MonitoringConfig:
    enabled: bool = False
    collector_interval_seconds: float = 60.0
    health_check_interval_seconds: float = 30.0
    snapshot_retention: int = 100
    prometheus_enabled: bool = False
    prometheus_port: int = 8000
    max_failures_stored: int = 100
```

## Quality

- **Frozen dataclasses** — All models immutable
- **Strict typing** — Full type hints throughout
- **Dependency injection** — Constructor injection for testability
- **Thread-safe** — All mutable state protected by `Lock`
- **Ruff clean** — Zero linting errors
- **Black clean** — Zero formatting errors
- **MyPy clean** — Zero type errors

## Rules

1. No trading logic
2. No market analysis
3. No execution logic
4. Collect metrics only
5. Every subsystem reports through this framework
6. No module may implement its own monitoring solution

## TUI Integration

The Monitoring & Alerting screen (F6) provides real-time visualization of monitoring state:

- **SystemHealthWidget**: Displays overall health status and per-subsystem health from `HealthEngine.evaluate()`
- **TelemetryWidget**: Displays collector counts and uptime from `MonitoringDashboard.status()`
- **MetricsWidget**: Displays resource metric summaries from `DashboardStatus.metric_summaries`
- **MonitoringEventsWidget**: Displays monitoring warnings and recommendations

Data is read-only. The TUI reads `MonitoringManager.generate_report()` and `MonitoringManager.dashboard_status()` every second via `build_monitoring_state()` in `titan/tui/layout.py`.
