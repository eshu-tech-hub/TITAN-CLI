# ADR-028: Monitoring & Telemetry Framework

**Status:** Accepted (Milestone M6.5.3)

**Date:** 2026-07-08

**Author:** TITAN Architecture Team

## Context

Before this ADR, TITAN had no centralized monitoring system. Health
checks were handled ad-hoc by individual modules (e.g.,
`titan/runtime/health.py` with `HealthCheck` and `ComponentHealth`).
Metrics were not collected, aggregated, or exposed in a uniform way.

This created several problems:

- **No centralized metric collection.** Each module tracked its own
  performance metrics using local variables, timestamps, and ad-hoc
  logging. There was no shared `MetricsRegistry`.
- **No health aggregation.** The runtime's `HealthCheck` tracked
  component health for the runtime only. Other subsystems (market,
  broker, risk, execution, pipeline, portfolio, decision, events,
  intelligence, trading, config) had no health reporting mechanism.
- **No telemetry snapshots.** There was no mechanism to capture a
  point-in-time snapshot of all metrics and health status.
- **No monitoring dashboard.** Operators had no unified view of system
  health, metric summaries, recent failures, or performance overview.
- **No monitoring report.** There was no machine-readable report
  combining system health, metrics, warnings, and recommendations.
- **No collector framework.** Metrics were not collected on a schedule
  or in response to events. There was no plugin/collector abstraction.
- **No future-export compatibility.** Prometheus, Grafana, OpenTelemetry,
  CloudWatch, and Azure Monitor integration would require a redesign
  of each module's metric handling.

## Problem Statement

TITAN needs an institutional monitoring and telemetry framework that:

1. Provides a centralized `MonitoringManager` as the single authority
   for metric collection, health tracking, and telemetry.
2. Collects operational metrics: pipeline latency, decision latency,
   execution latency, broker latency, OMS latency, runtime latency,
   CPU, memory, disk, network, active pipelines, active positions,
   orders/minute, signals/minute, trades/day.
3. Aggregates metrics into meaningful summaries (current, min, max,
   avg, count) for display and alerting.
4. Tracks subsystem health across all TITAN subsystems with four
   status levels: HEALTHY, WARNING, CRITICAL, OFFLINE.
5. Provides a `TelemetryManager` that records metrics, accepts health
   reports, stores snapshots, and supports future exporters.
6. Provides a `MetricCollector` with periodic collection, event-driven
   collection, custom collectors, and plugin architecture.
7. Provides a `MonitoringDashboard` exposing current status, metric
   summaries, subsystem health, recent failures, and performance
   overview.
8. Generates a `MonitoringReport` with system health, metrics,
   warnings, and recommendations.
9. Supports future export to Prometheus, Grafana, OpenTelemetry
   Metrics, CloudWatch, Azure Monitor, and distributed workers
   without redesign.
10. Is thread-safe by design — all mutable state is protected by
    `Lock`.
11. Has zero trading logic, zero market analysis, zero execution
    logic — it collects metrics only.

## Decision

We introduce `titan/monitoring/` with the following architecture.

### Architecture

```
                    MonitoringManager
                         │
              ┌──────────┼──────────┐
              │          │          │
      MetricCollector  Telemetry   Dashboard
              │        Manager        │
              │          │            │
              │    ┌─────┴─────┐      │
              │    │           │      │
         Periodic   Metrics  Health  Status()
         Event      Registry Engine
         Custom
```

### Data Flow

```
Subsystems ──> MetricCollector ──> MetricsRegistry ──> Dashboard
     │                                    │
     └────> HealthEngine ──> TelemetryManager ──> Exporters
                                    │
                              Snapshots
```

### Module Layout

```
titan/monitoring/
    __init__.py    — Public API exports
    models.py      — All dataclasses and enums
    exceptions.py  — Exception hierarchy
    metrics.py     — MetricsRegistry, MetricAggregator, MetricsEngine
    health.py      — HealthEngine
    telemetry.py   — TelemetryManager
    collector.py   — MetricCollector
    dashboard.py   — MonitoringDashboard
    manager.py     — MonitoringManager
```

### Models

All data models are frozen dataclasses with slots:

**MetricValue** — A single metric measurement with name, value, type
(GAUGE, COUNTER, HISTOGRAM, SUMMARY), unit, tags, timestamp, and
description.

**MetricSnapshot** — A point-in-time collection of `MetricValue`
objects with a source identifier and timestamp.

**SubsystemHealth** — Health status of one subsystem with status
(HEALTHY, WARNING, CRITICAL, OFFLINE), message, latency, failure
count, and metadata.

**SystemHealth** — Aggregate health across all registered subsystems
with counts per status level.

**TelemetrySnapshot** — Combined metrics and health snapshot with
collection statistics.

**DashboardStatus** — Current dashboard view with metric summaries,
recent failures, collector counts, and uptime.

**MonitoringReport** — Full diagnostic report with system health,
metrics, warnings, and recommendations.

### MetricType

```python
class MetricType(str, Enum):
    GAUGE = "gauge"         # Point-in-time value
    COUNTER = "counter"     # Monotonically increasing count
    HISTOGRAM = "histogram" # Distribution of values
    SUMMARY = "summary"     # Quantile-based summary
```

### HealthStatus

```python
class HealthStatus(str, Enum):
    HEALTHY = "healthy"     # Operating normally
    WARNING = "warning"     # Degraded but functional
    CRITICAL = "critical"   # Not operating correctly
    OFFLINE = "offline"     # Not reachable/stopped
```

### Subsystem Enum

Every TITAN subsystem is represented: MARKET, BROKER, EXECUTION, RISK,
PIPELINE, PORTFOLIO, DECISION, RUNTIME, EVENTS, INTELLIGENCE, TRADING,
CONFIG, MONITORING, PAPER, BACKTESTING.

### MetricsRegistry

Thread-safe registry that stores `MetricValue` objects by name. Supports
`record()`, `record_many()`, `snapshot()`, `latest()`, `latest_values()`,
`range()`, `clear()`, `count()`, and `metric_names()`.

### MetricAggregator

Computes summary statistics (current, min, max, avg, count) for a named
metric using `mean()` from the `statistics` module.

### MetricsEngine

Orchestrates named collector functions, collects from all registered
collectors, records results in the aggregator, and provides
`snapshot()` and `aggregate()` access.

### HealthEngine

Manages subsystem health with `register()`, `unregister()`,
`report()`, `get()`, `all_health()`, and `evaluate()`. The
`evaluate()` method computes `SystemHealth` with overall status and
counts per level.

### MetricCollector

Supports registration of named collectors with `CollectorType`
(PERIODIC, EVENT_DRIVEN, CUSTOM), enable/disable, collect-all,
collect-one, and a background thread for periodic collection.
Tracks total and failed collection counts.

### TelemetryManager

Central telemetry hub that:
- Exposes `MetricsRegistry` and `HealthEngine` as properties
- Records metrics via `record_metric()` and `record_metrics()`
- Accepts health reports via `report_health()`
- Stores historical snapshots
- Supports external exporters via `register_exporter()` /
  `unregister_exporter()`
- Provides `collect_snapshot()`, `latest_snapshot()`, `snapshots()`,
  and `current_status()`

### MonitoringDashboard

Provides `status()` returning `DashboardStatus` with:
- `SystemHealth` aggregation
- Per-metric `DashboardMetricSummary` with trend detection
  (increasing, decreasing, stable)
- Recent failure messages (last 10)
- Active collector and collection statistics
- Uptime tracking

### MonitoringManager

Top-level orchestrator that wires all components together:
- Maintains `TelemetryManager`, `MetricCollector`, and
  `MonitoringDashboard` instances
- Registers itself (`Subsystem.MONITORING`) as healthy on init
- Provides `register_subsystem()`, `register_collector()`,
  `collect_snapshot()`, `dashboard_status()`, `generate_report()`
- Supports `start()`/`stop()` lifecycle for background collection
- `generate_report()` produces a `MonitoringReport` with health-
  derived warnings and recommendations

### Exception Hierarchy

```
MonitoringError (Exception)
├── MonitoringInputError (ValueError)
├── MonitoringCollectionError
├── MonitoringStorageError
├── MonitoringHealthError
├── MonitoringDashboardError
└── MonitoringExportError
```

### Thread Safety

All mutable state in `MetricsRegistry`, `MetricAggregator`,
`MetricsEngine`, `HealthEngine`, `MetricCollector`,
`TelemetryManager`, `MonitoringDashboard`, and `MonitoringManager`
is protected by `threading.Lock`.

## Alternatives Considered

### 1. Prometheus Client Library Directly

We considered using the `prometheus_client` library directly for
metric collection and exposition.

**Rejected because:**
- Binds the monitoring architecture to a single export format.
- Prometheus types (Counter, Gauge, Histogram, Summary) are well-
  designed but the library's exposition format is HTTP-based only.
- CloudWatch, Azure Monitor, and OpenTelemetry require different
  data models. A Prometheus-first design would make these integrations
  awkward.
- The `MonitoringManager` abstraction allows Prometheus to be one
  exporter among many, not the foundation.

### 2. OpenTelemetry SDK Directly

We considered using the OpenTelemetry Python SDK for metrics and
health tracking.

**Rejected because:**
- OpenTelemetry is designed for distributed tracing and service-
  oriented architectures. TITAN is a monolithic trading platform.
  The OTel data model (instruments, views, metric readers) adds
  complexity without benefit.
- OTel requires a running collector for full functionality. TITAN
  needs to operate independently.
- OTel can be added as an exporter later — the `TelemetryManager`
  exporter interface is compatible with OTLP export.

### 3. Extending Runtime HealthCheck

We considered extending `titan/runtime/health.py` to cover all
subsystems.

**Rejected because:**
- The runtime's `HealthCheck` is focused on runtime components
  (stream, scheduler, heartbeat, broker, pipeline). Adding market,
  risk, execution, portfolio, and other subsystems would create a
  circular dependency — monitoring would need to import from all
  modules, and all modules would need to import monitoring.
- The runtime health model uses `ComponentHealth` with HEALTHY,
  DEGRADED, UNHEALTHY, UNKNOWN. The monitoring framework needs
  HEALTHY, WARNING, CRITICAL, OFFLINE — a different status set
  designed for operational alerting rather than component health.
- Runtime health is consumed at a different cadence (per-component
  updates during pipeline execution) than monitoring health
  (aggregate snapshots for dashboard display).

### 4. Single Global Dashboard

We considered a single `MonitoringDashboard` with no manager layer.

**Rejected because:**
- A manager layer is needed for lifecycle management (start/stop,
  reset, report generation).
- Dependency injection requires a clear ownership boundary — the
  `MonitoringManager` owns the wiring, not the dashboard.
- Future exporters need a coordination point, which the
  `TelemetryManager` provides.

### 5. InfluxDB / Time-Series Database

We considered storing all metrics in InfluxDB or a similar TSDB.

**Rejected because:**
- Adds an external dependency and infrastructure requirement.
- TITAN is a desktop/CLI application that must operate offline.
- TSDB storage can be added as an exporter later without modifying
  the core monitoring framework.

## Consequences

### Positive

1. **Single monitoring authority.** `MonitoringManager` is the sole
   entry point for metric collection, health tracking, and telemetry.
   No module can bypass the framework.

2. **Unified metric collection.** All metrics flow through
   `MetricsRegistry`. Future export to any system (Prometheus,
   Grafana, CloudWatch, Azure Monitor, OpenTelemetry) requires only
   a new exporter, not changes to collection logic.

3. **Unified health tracking.** Every TITAN subsystem reports health
   through `HealthEngine`. The `SystemHealth` aggregate provides a
   single answer to "is the platform healthy?"

4. **Thread-safe by design.** All mutable state is protected by
   `Lock`. The background collector runs in a daemon thread.

5. **Pluggable collectors.** New metric sources are added via
   `register_collector()`. Periodic, event-driven, and custom
   collectors share the same interface.

6. **Pluggable exporters.** Future export targets are registered
   as callbacks on `TelemetryManager`. No framework changes needed.

7. **Diagnostic reporting.** `generate_report()` provides machine-
   readable diagnostics with warnings and recommendations derived
   from system health and collection statistics.

8. **Dashboard status.** `dashboard_status()` provides a complete
   view of system health, metric summaries (with trend detection),
   recent failures, and uptime.

9. **Zero business logic.** The monitoring framework imports no
   trading logic, no execution logic, no broker SDKs. It collects
   metrics only.

10. **Frozen dataclasses.** All model classes are immutable,
    providing thread safety and hashability guarantees.

11. **Constructor injection.** All components accept their
    dependencies via the constructor, supporting testing and
    customization.

### Negative

1. **No built-in visualisation.** The `DashboardStatus` data model
   is machine-readable. A GUI dashboard requires a separate
   frontend (terminal UI, web UI, or Grafana).

2. **No alerting rules.** The framework collects metrics and
   evaluates health, but does not trigger alerts. Alerting rules
   (e.g., "if broker latency > 500ms for 3 consecutive checks,
   page on-call") require a separate alerting engine.

3. **No historical persistence.** Snapshots are stored in memory.
   Long-term metric storage requires an exporter to a TSDB or
   log aggregator.

4. **No rate limiting.** The collector thread runs at a fixed 1s
   interval. There is no backpressure mechanism for slow collectors.

### Neutral

1. **Background collection.** The `MetricCollector.start()` method
   runs a daemon thread that invokes periodic collectors every
   second. This is sufficient for operational metrics but not for
   high-frequency market data.

2. **Metric names as strings.** Metrics are identified by string
   names. There is no compile-time check for metric name typos.
   This matches every major metrics system (Prometheus, StatsD,
   OpenTelemetry).

3. **No metric type enforcement.** A metric registered as a GAUGE
   can be recorded with COUNTER values. Type-level validation is
   deferred to exporters that require it (e.g., Prometheus).

## Trade-offs

| Trade-off | Choice | Rationale |
|---|---|---|
| Frozen vs mutable models | Frozen | Thread safety, hashability, immutability guarantees |
| Lock-based vs lock-free | Lock-based | Simplicity, proven correctness for this access pattern |
| Background thread vs asyncio | Thread | TITAN is synchronous; async adds complexity without benefit |
| String enum vs IntEnum for status | String Enum | Human-readable serialization, JSON compatibility |
| Constructor injection vs service locator | Constructor | Testability, explicit dependencies |
| Single manager vs separate components | Manager + components | Manager for lifecycle, components for testability |
| Periodic collector at 1s fixed interval vs configurable | Configurable via `CollectorDescriptor` | Per-collector interval customization available |
| In-memory snapshots vs file-based | In-memory | Simplicity; file persistence is an exporter concern |

## Future Evolution

### Prometheus Exporter

A `PrometheusExporter` can convert `MetricValue` objects to
Prometheus metric families and expose them via HTTP:

```python
class PrometheusExporter:
    def __init__(self, port: int = 8000):
        self._port = port
        self._server = None

    def export(self, snapshot: TelemetrySnapshot) -> None:
        for metric in snapshot.metrics:
            # Convert to prometheus_client format
            pass
```

The exporter registers itself via `telemetry.register_exporter()`.

### Grafana Integration

`DashboardStatus` can be serialized to JSON for Grafana's
SimpleJSON datasource or a custom `titan-grafana-datasource` plugin.

### OpenTelemetry Metrics

An `OTLPMetricExporter` can convert `MetricValue` objects to
OpenTelemetry metric data points and export via OTLP:

```python
class OTLPMetricExporter:
    def __init__(self, endpoint: str = "http://localhost:4318/v1/metrics"):
        self._endpoint = endpoint

    def export(self, snapshot: TelemetrySnapshot) -> None:
        # Convert to OTLP Metric protobuf
        pass
```

### CloudWatch / Azure Monitor

CloudWatch and Azure Monitor exporters follow the same pattern —
convert `MetricValue` to the target format and send via the
provider's SDK:

```python
class CloudWatchExporter:
    def __init__(self, namespace: str = "TITAN", region: str = "us-east-1"):
        self._client = boto3.client("cloudwatch", region_name=region)

    def export(self, snapshot: TelemetrySnapshot) -> None:
        metrics = [
            {
                "MetricName": m.name,
                "Value": m.value,
                "Unit": m.unit.value,
                "Timestamp": m.timestamp,
            }
            for m in snapshot.metrics
        ]
        self._client.put_metric_data(Namespace=self._namespace, MetricData=metrics)
```

### Alerting Engine

A future `AlertEngine` could evaluate rules against `MetricValue`
streams and `SystemHealth` snapshots:

```python
class AlertRule:
    metric_name: str
    condition: Callable[[float], bool]
    severity: AlertSeverity
    message: str
```

### Distributed Workers

For multi-process or multi-host deployments, the `TelemetryManager`
exporter interface supports gRPC or message-queue based aggregation:

```python
class DistributedExporter:
    def __init__(self, channel: grpc.Channel):
        self._stub = TelemetryServiceStub(channel)

    def export(self, snapshot: TelemetrySnapshot) -> None:
        self._stub.ReportTelemetry(snapshot_to_proto(snapshot))
```

### Long-Term Storage

A `StorageExporter` can persist snapshots to SQLite or DuckDB for
historical analysis:

```python
class SQLiteExporter:
    def __init__(self, path: str = "./data/monitoring.db"):
        self._conn = sqlite3.connect(path)

    def export(self, snapshot: TelemetrySnapshot) -> None:
        # INSERT metrics and health into tables
        pass
```

## Relationship to Other ADRs

### ADR-025 (Live Runtime)

The runtime engine's `HealthCheck` (`titan/runtime/health.py`)
reports component health for runtime-specific components (stream,
scheduler, heartbeat, broker connection). The monitoring framework's
`HealthEngine` complements this by providing cross-subsystem health
aggregation. At integration time, the runtime reports its health
status to `HealthEngine` via `monitoring.health.report()`.

### ADR-026 (Configuration System)

The monitoring framework is configured via `MonitoringConfig` in
`titan/config/models.py`. The `ConfigManager` provides the
monitoring section to `MonitoringManager` at startup.

### ADR-027 (Logging Framework)

The monitoring framework is the operational data plane (metrics,
health). The logging framework is the diagnostic data plane (events,
errors). They complement each other — `MonitoringDashboard` tracks
cumulative health and metrics, while `StructuredLogger` captures
individual events with structured context.

## Migration Path

### Phase 1: Introduction (Milestone M6.5.3)

The `titan/monitoring/` module is introduced alongside existing
health tracking. No existing code is changed.

- `MonitoringManager` is available for new consumers.
- Existing `titan/runtime/health.py` continues to work independently.
- Documentation directs all new health reporting to use `HealthEngine`.

### Phase 2: Runtime Integration (Future Milestone)

The runtime engine registers its components with `HealthEngine` and
reports metrics via `MetricCollector`:

```python
manager = MonitoringManager()
manager.register_subsystem(Subsystem.RUNTIME)

def collect_runtime_metrics() -> tuple[MetricValue, ...]:
    return (
        MetricValue(name="runtime.uptime", value=runtime.uptime_seconds,
                    unit=MetricUnit.SECONDS),
        # ...
    )

manager.register_collector("runtime", collect_runtime_metrics,
                           interval_seconds=30.0)
```

### Phase 3: Full Adoption (Future Milestone)

All TITAN subsystems report health and metrics through the monitoring
framework. The `MonitoringDashboard` becomes the primary operational
interface. Ad-hoc metric tracking in individual modules is migrated
to `MetricsRegistry`.
