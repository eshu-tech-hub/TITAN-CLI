# Live Runtime Engine

## Overview

The Live Runtime Engine (`titan/runtime/`) is the production runtime that
operates TITAN in a live market environment. It coordinates market data
streaming, periodic pipeline execution, heartbeat monitoring, health
checking, and graceful lifecycle management — all without introducing
duplicate business logic from the existing pipeline, broker, or execution
layers.

The runtime is **not** a trading engine. It is an operations engine that
keeps the TITAN platform alive and healthy during market hours.

## Architecture

```
Market Data Source (WebSocket / API)
        │
        ▼
   MarketStream ────┐
        │           │
        ▼           ▼
   Subscription ── RuntimeEventBus ── HeartbeatMonitor
   Manager             │                    │
        │              │                    │
        ▼              ▼                    ▼
   PipelineScheduler ──┼──── RuntimeEngine ──┼── HealthCheck
        │              │                    │
        ▼              ▼                    ▼
   TradePipeline ── ExecutionOrchestrator ── Broker
```

## Package Structure

```
titan/runtime/
    __init__.py         # Public API exports
    models.py           # Frozen dataclasses and enums
    exceptions.py       # Domain exception hierarchy
    events.py           # RuntimeEventBus — typed pub/sub
    subscriptions.py    # SubscriptionManager — symbol tracking
    stream.py           # MarketStream — threaded data ingestion
    scheduler.py        # PipelineScheduler — periodic execution
    heartbeat.py        # HeartbeatMonitor — liveliness checks
    health.py           # HealthCheck — component health aggregation
    runtime.py          # RuntimeEngine — lifecycle orchestrator
```

## Component Overview

### RuntimeEngine

The central orchestrator that manages the complete lifecycle of all
runtime components. Implements start, stop, pause, resume, and restart
operations. Coordinates graceful shutdown by stopping components in
reverse order.

```python
from titan.runtime import RuntimeEngine

engine = RuntimeEngine(
    broker=broker,
    pipeline=TradePipeline(),
    stream=MarketStream(source=source),
    scheduler=PipelineScheduler(runner=pipeline_runner, interval_seconds=60),
    heartbeat=HeartbeatMonitor(interval_seconds=10),
)
engine.start()
engine.stop()
```

### EventBus

Typed publish-subscribe event bus for decoupled inter-component
communication. Supports subscribing/unsubscribing by event type,
publishing with optional data payloads, and clearing all listeners.

| Event Type | Source | Purpose |
|---|---|---|
| `RUNTIME_STARTED` | runtime | Lifecycle start |
| `RUNTIME_STOPPED` | runtime | Lifecycle stop |
| `RUNTIME_PAUSED` | runtime | Lifecycle pause |
| `RUNTIME_RESUMED` | runtime | Lifecycle resume |
| `RUNTIME_ERROR` | runtime | Fatal error |
| `STREAM_CONNECTED` | stream | Data source connected |
| `STREAM_DISCONNECTED` | stream | Data source disconnected |
| `STREAM_QUOTE` | stream | New quote received |
| `STREAM_ERROR` | stream | Stream failure |
| `BROKER_CONNECTED` | runtime | Broker connected |
| `BROKER_DISCONNECTED` | runtime | Broker disconnected |
| `SCHEDULER_PIPELINE_STARTED` | scheduler | Pipeline execution began |
| `SCHEDULER_PIPELINE_COMPLETED` | scheduler | Pipeline execution finished |
| `SCHEDULER_PIPELINE_FAILED` | scheduler | Pipeline execution failed |
| `SCHEDULER_ERROR` | scheduler | Scheduler failure |
| `SUBSCRIPTION_ADDED` | subscriptions | Symbol subscribed |
| `SUBSCRIPTION_REMOVED` | subscriptions | Symbol unsubscribed |
| `HEARTBEAT_TICK` | heartbeat | Heartbeat signal |
| `HEARTBEAT_MISSED` | heartbeat | Heartbeat missed |
| `HEARTBEAT_RESTORED` | heartbeat | Heartbeat recovered |
| `HEALTH_OK` | health | All components healthy |
| `HEALTH_DEGRADED` | health | Component degraded |
| `HEALTH_ERROR` | health | Component unhealthy |

## Runtime Lifecycle

### States

```
STOPPED ──► STARTING ──► RUNNING ──► STOPPING ──► STOPPED
                │            │
                ▼            ▼
              ERROR ◄─── PAUSED ──► RUNNING (resume)
                │
                ▼
             STOP (restart)
```

### Start

1. Validate not already running or paused.
2. Set status to `STARTING`.
3. Connect broker via `Broker.connect()`.
4. Start market stream (threaded).
5. Start pipeline scheduler (threaded with runner set to internal
   `_pipeline_runner`).
6. Start heartbeat monitor (threaded).
7. Set status to `RUNNING`.
8. Publish `RUNTIME_STARTED` event.
9. If any step fails, set status to `ERROR` and publish
   `RUNTIME_ERROR`.

### Stop

1. Set `_stop_event` to signal all threads.
2. Set status to `STOPPING`.
3. Stop heartbeat monitor.
4. Stop pipeline scheduler (joins thread with 5s timeout).
5. Stop market stream.
6. Disconnect broker.
7. Set status to `STOPPED`.
8. Publish `RUNTIME_STOPPED`.

### Pause

1. Validate status is `RUNNING`.
2. Set status to `PAUSED`.
3. Pause scheduler (prevents new pipeline executions).
4. Mark health as degraded.
5. Publish `RUNTIME_PAUSED`.

### Resume

1. Validate status is `PAUSED`.
2. Set status to `RUNNING`.
3. Resume scheduler.
4. Mark health as healthy.
5. Publish `RUNTIME_RESUMED`.

### Restart

1. Call `stop()` (graceful shutdown).
2. Call `start()` (fresh initialization).

## Scheduler Architecture

The `PipelineScheduler` runs the Trade Pipeline on a configurable
interval in a background daemon thread.

```
PipelineScheduler
    ├── runner: Callable (set by RuntimeEngine._pipeline_runner)
    ├── interval_seconds: float (default 60)
    ├── _thread: Thread (daemon)
    ├── _stop_event: Event
    ├── _paused: bool
    ├── execution_count: int
    └── last_execution_time: datetime
```

### Execution Loop

```
while not stop_event:
    if not paused:
        try:
            run_pipeline()
        except Exception:
            publish SCHEDULER_ERROR
    sleep(interval_seconds)
```

### Pipeline Runner

The `RuntimeEngine._pipeline_runner()` method increments
`_pipeline_executions`, determines the primary exchange from the
broker profile, and calls `TradePipeline.run(symbol, exchange)`.

```python
def _pipeline_runner(self) -> Any:
    self._pipeline_executions += 1
    exchanges = self.broker.profile().enabled_exchanges
    exchange = exchanges[0] if exchanges else Exchange.NSE
    return self.pipeline.run(symbol="", exchange=exchange)
```

### Manual Execution

```python
scheduler.execute_once()  # Runs pipeline immediately, bypasses schedule
```

## Market Stream Architecture

The `MarketStream` receives quotes from a data source and distributes
them to registered callbacks and the event bus. Runs in a background
daemon thread.

```
Market Data Source (StreamDataSource protocol)
        │
        ▼
   MarketStream (threaded)
        │
        ├── on_quote callback(s)
        ├── RuntimeEventBus (STREAM_QUOTE events)
        └── Quote queue (internal buffer)
```

### StreamDataSource Protocol

```python
class StreamDataSource(Protocol):
    def connect(self) -> ConnectionStatus: ...
    def disconnect(self) -> ConnectionStatus: ...
    def is_connected(self) -> bool: ...
    def subscribe(self, symbol: str, exchange: Exchange) -> None: ...
    def unsubscribe(self, symbol: str, exchange: Exchange) -> None: ...
    def read(self) -> Quote | None: ...
```

This protocol enables mock sources in tests and real WebSocket sources
in production.

### Thread Loop

```
while not stop_event:
    quote = source.read()
    if quote:
        update last_quote_time
        increment quote_count
        for each on_quote callback: callback(quote)
        publish STREAM_QUOTE event
    else:
        sleep(0.01)
```

### Reconnection

On `start()`, the stream calls `source.connect()`. If connection fails,
the stream enters an error state but does not crash. The `RuntimeEngine`
reports the stream health as `UNHEALTHY`.

## Event Bus Architecture

The `RuntimeEventBus` is a lightweight typed publish-subscribe bus with
no external dependencies.

```python
bus = RuntimeEventBus()

def handle_tick(event: RuntimeEvent) -> None:
    print(f"Heartbeat at {event.timestamp}")

bus.subscribe(RuntimeEventType.HEARTBEAT_TICK, handle_tick)
bus.publish_type(RuntimeEventType.HEARTBEAT_TICK, "heartbeat")
```

Features:
- Subscribe/unsubscribe by event type
- Multiple listeners per event type
- `publish()` accepts a `RuntimeEvent` instance
- `publish_type()` convenience method
- `listener_count()` introspection
- `clear()` to reset all listeners

All core runtime components are wired to the same event bus instance
via the `RuntimeEngine.__post_init__()` method.

## Subscription Management

The `SubscriptionManager` tracks which symbols and exchanges are being
watched by the runtime.

```python
mgr = SubscriptionManager(event_bus=bus)

# Add a subscription
sub = mgr.add("RELIANCE", Exchange.NSE)

# Enable/disable
mgr.disable("RELIANCE", Exchange.NSE)
mgr.enable("RELIANCE", Exchange.NSE)

# Query
active = mgr.list_active()    # Enabled subscriptions only
all_subs = mgr.list_all()     # All subscriptions
symbols = mgr.symbols()       # All symbol+exchange pairs
count = mgr.count()           # Total count
```

### Subscription Model

```python
@dataclass(frozen=True)
class Subscription:
    symbol: str
    exchange: Exchange
    subscription_type: SubscriptionType = SubscriptionType.SYMBOL
    enabled: bool = True
```

### Subscription Types

| Type | Purpose |
|---|---|
| `SYMBOL` | Individual equity or futures |
| `OPTION_CHAIN` | Full option chain for a symbol |
| `INDEX` | Index data (NIFTY, BANKNIFTY) |
| `WATCHLIST` | User-defined watchlist |
| `MARKET_DEPTH` | Level 2/3 market depth |

## Health Monitoring

The `HealthCheck` aggregator maintains the health status of all runtime
components.

```python
hc = HealthCheck()

# Register components
hc.register("runtime")
hc.register("broker")
hc.register("stream")

# Report status
hc.report_healthy("broker")
hc.report_degraded("stream", error="high latency")
hc.report_unhealthy("broker", error="connection lost")

# Query
hc.is_healthy()        # All components HEALTHY
hc.has_degraded()      # Any component DEGRADED
hc.has_unhealthy()     # Any component UNHEALTHY
hc.summary()           # {"broker": "healthy", "stream": "degraded"}
```

### Health Status Enum

| Status | Meaning |
|---|---|
| `HEALTHY` | Component operating normally |
| `DEGRADED` | Component operating with reduced capability |
| `UNHEALTHY` | Component has failed |
| `UNKNOWN` | Component status not yet reported |

The `RuntimeEngine` registers five components by default:
`runtime`, `broker`, `stream`, `scheduler`, `heartbeat`.

## Heartbeat Mechanism

The `HeartbeatMonitor` emits periodic ticks and detects missed
heartbeats as a liveliness check for the runtime.

```python
monitor = HeartbeatMonitor(interval_seconds=10, event_bus=bus)
monitor.start()

# Manual beat (resets missed count)
monitor.beat()

# Query
monitor.last_heartbeat  # datetime of last beat
monitor.missed_count    # consecutive missed beats
monitor.is_running      # whether the thread is alive

monitor.stop()
```

### Heartbeat Events

| Event | Trigger |
|---|---|
| `HEARTBEAT_TICK` | Every interval when running |
| `HEARTBEAT_MISSED` | Consecutive ticks without a `beat()` call |
| `HEARTBEAT_RESTORED` | `beat()` called after a missed state |

## Runtime Reports

### RuntimeReport

```python
@dataclass(frozen=True)
class RuntimeReport:
    runtime_status: RuntimeStatus
    uptime_seconds: float
    broker_status: ConnectionStatus
    stream_status: str
    scheduler_active: bool
    pipeline_executions: int
    active_subscriptions: int
    last_pipeline_time: datetime | None
    last_quote_time: datetime | None
    component_health: tuple[ComponentHealth, ...]
    warnings: tuple[str, ...]
    errors: tuple[str, ...]
```

```python
report = engine.generate_report()
print(f"Status: {report.runtime_status}")
print(f"Uptime: {report.uptime_seconds:.0f}s")
print(f"Pipeline runs: {report.pipeline_executions}")
print(f"Active subscriptions: {report.active_subscriptions}")
print(f"Broker: {report.broker_status}")
print(f"Stream: {report.stream_status}")
print(f"Warnings: {list(report.warnings)}")
print(f"Errors: {list(report.errors)}")
```

## Dependency Graph

```
                        RuntimeEngine
                             │
         ┌───────────────────┼─────────────────────┐
         │                   │                     │
         ▼                   ▼                     ▼
    MarketStream      PipelineScheduler      HeartbeatMonitor
         │                   │                     │
         ▼                   ▼                     ▼
  StreamDataSource     TradePipeline            EventBus
         │                   │
         ▼                   ▼
   Subscription         ExecutionOrchestrator
    Manager                   │
                              ▼
                           Broker
```

## Integration with Trade Pipeline

The `PipelineScheduler` calls `TradePipeline.run()` on each execution
cycle. The `RuntimeEngine._pipeline_runner` method creates the
connection:

```python
self._pipeline_executions += 1
exchanges = self.broker.profile().enabled_exchanges
exchange = exchanges[0] if exchanges else Exchange.NSE
self.pipeline.run(symbol="", exchange=exchange)
```

The pipeline receives no direct symbol from the runtime — the pipeline's
own intelligence engines determine which symbols to analyze based on
configured watchlists and market data.

## Integration with Execution Orchestrator

The `TradePipeline` internally invokes the `ExecutionOrchestrator`
during its EXECUTION stage. The orchestrator receives an approved
`TradeDecision` and routes orders through the OMS to the broker.

The runtime does **not** call the orchestrator directly — it only
triggers the pipeline, which owns the orchestrator invocation.

## Integration with Broker Abstraction

The `RuntimeEngine` receives a `Broker` instance at construction time.
During `start()`, it calls `broker.connect()`. During `stop()`, it calls
`broker.disconnect()`. The broker is passed through to the pipeline's
`ExecutionOrchestrator` and ultimately to the OMS and order router.

The runtime is broker-agnostic — any `Broker` implementation works:
- `PaperBroker` (for simulation/dry-run)
- `YFinanceBroker` (for live YFinance trading)
- Any future broker adapter

## Failure Handling

### Component-Level Failures

Each runtime component handles failures independently:

| Component | Failure Mode | Impact |
|---|---|---|
| MarketStream | Source connect failure | Stream stays stopped; health marked UNHEALTHY |
| PipelineScheduler | Pipeline execution exception | Caught in scheduler loop; error event published |
| HeartbeatMonitor | Thread failure | No health updates; Engine can detect via health check |
| Broker | Connect failure | Runtime start raises RuntimeError |

### Pipeline Runner Failures

If `TradePipeline.run()` raises an exception:
1. `_pipeline_runner` propagates the exception to `_run_pipeline`.
2. `_run_pipeline` catches it, publishes `SCHEDULER_PIPELINE_FAILED`,
   and re-raises.
3. The scheduler `_run` loop catches the re-raised exception, publishes
   `SCHEDULER_ERROR`, and continues the loop.
4. The next scheduled execution proceeds normally.

No single pipeline failure stops the runtime or prevents future
executions.

## Retry Strategy

The runtime does not implement explicit retry logic. Instead:

- **Scheduler loop:** The `while not stop_event` loop automatically
  retries on the next interval after any failure.
- **Stream reconnection:** The `MarketStream.start()` must be called
  again after a failure. Future enhancement: automatic reconnection
  with exponential backoff.
- **Broker connection:** The `RuntimeEngine` connects once on `start()`.
  Broker disconnection during runtime requires manual restart.

## Graceful Shutdown

The `stop()` method performs a phased, ordered shutdown:

1. Set `_stop_event` — signals all threads to stop.
2. `_stop_heartbeat()` — stops the heartbeat thread.
3. `_stop_scheduler()` — joins the scheduler thread (5s timeout).
4. `_stop_stream()` — stops the market stream thread.
5. `_stop_broker()` — disconnects the broker.
6. Set status to `STOPPED`.
7. Publish `RUNTIME_STOPPED` event.

Threads use `daemon=True`, so if the main process exits unexpectedly,
daemon threads do not prevent process termination.

## Future Roadmap

### Multi-Broker Support

The `RuntimeEngine` currently accepts a single `Broker` instance.
Future versions could accept multiple brokers with per-symbol routing
via the SubscriptionManager.

### Distributed Runtime

The `RuntimeReport` and event bus architecture support serialization
for remote monitoring. Future versions could:
- Stream health and events to a remote dashboard.
- Accept remote start/stop/pause commands.
- Coordinate across multiple runtime instances for failover.

### Kubernetes / Container Deployment

The runtime is stateless (all state is in the broker, pipeline, and
event bus). Future enhancements:
- Health check endpoints for Kubernetes liveness/readiness probes.
- Configurable log levels for structured logging.
- Graceful SIGTERM handling for pod termination.
- Horizontal pod autoscaling based on pipeline execution load.

### High Availability

- Active-passive failover with health check arbitration.
- Shared `RuntimeReport` persistence for crash recovery.
- Subscription state recovery on restart.

## CLI Integration

The Live Trading CLI (`titan live`) orchestrates the runtime engine through a structured lifecycle with pre-flight validation.

### Startup Lifecycle

```
titan live start
  1. Load configuration (ConfigManager)
  2. Run pre-flight validation (StartupChecklist)
     - Configuration valid
     - Broker configured
     - Environment validated
     - Risk limits checked
     - Monitoring enabled
     - Recovery system available
     - Audit trail enabled
     - Runtime engine available
  3. Create broker (create_broker)
  4. Create RuntimeEngine (create_runtime_engine)
  5. Start RuntimeEngine (engine.start())
  6. Start DeploymentManager
  7. Start MonitoringManager
  8. Record audit event (SYSTEM_START)
```

If any mandatory validation fails, startup is aborted with exit code 2.
Use `--force` to override safety checks.
Use `--dry-run` to validate without starting.

### Runtime Lifecycle

```
STOPPED ──start()──> STARTING ──> RUNNING
RUNNING ──stop()───> STOPPING ──> STOPPED
RUNNING ──pause()──> PAUSED
PAUSED  ──resume()─> RUNNING
```

The CLI tracks the engine state via `_runtime_engine` in `common.py`:
- `start` creates a new engine and calls `set_runtime_engine()`
- `stop` calls `engine.stop()` then `set_runtime_engine(None)`
- `restart` stops then starts
- `pause` calls `engine.pause()` (suspends scheduler)
- `resume` calls `engine.resume()` (resumes scheduler)

### Pause/Resume

Pause suspends the pipeline scheduler without disconnecting the broker:

```
titan live pause     # Suspends scheduler tick
titan live resume    # Resumes scheduler tick
```

Use cases:
- Lunch break
- News events
- Manual intervention
- Maintenance windows

The broker remains connected during pause. Positions and orders are still accessible.

### Scheduler Interaction

The CLI does not directly interact with the scheduler. The scheduler is managed by the RuntimeEngine:
- `engine.start()` starts the scheduler daemon thread
- `engine.stop()` stops the scheduler
- `engine.pause()` suspends the scheduler
- `engine.resume()` resumes the scheduler

The scheduler runs the TradePipeline at configured intervals.

### Broker Interaction

The CLI accesses the broker through the RuntimeEngine:
- `engine.broker` - The connected broker instance
- `broker.positions()` - Current open positions
- `broker.orders()` - Order history
- `broker.funds()` - Account funds
- `broker.margin()` - Margin information
- `broker.is_connected()` - Connection status

### Monitoring Integration

The CLI starts and stops MonitoringManager alongside the runtime:
- `monitoring.start()` - Starts metric collectors
- `monitoring.stop()` - Stops metric collectors
- `monitoring.generate_report()` - Used by `titan live health`

### Recovery Integration

The CLI queries RecoveryManager for health status:
- `recovery.generate_report()` - Recovery attempt history
- Circuit breaker states
- Used by `titan live health`

### Audit Integration

The CLI records lifecycle events via AuditManager:
- `SYSTEM_START` on `titan live start`
- `SYSTEM_STOP` on `titan live stop`
- Source: `AuditSource.USER`
- Category: `AuditCategory.SYSTEM_START` / `SYSTEM_STOP`

### Shutdown Lifecycle

```
titan live stop
  1. Stop RuntimeEngine (engine.stop())
     - Stop heartbeat monitor
     - Stop pipeline scheduler
     - Disconnect market stream
     - Disconnect broker
  2. Stop MonitoringManager
  3. Stop DeploymentManager
  4. Record audit event (SYSTEM_STOP)
  5. Clear runtime engine reference (set_runtime_engine(None))
```

Each step is wrapped in try/except to ensure partial failures don't block cleanup.

### JSON Output

All live commands support `--json` for programmatic consumption:

```bash
titan live status --json
titan live positions --json
titan live orders --json
titan live exposure --json
titan live health --json
titan live report --json
```

JSON output bypasses Rich formatting and returns structured data.

### Verbose Mode

`--verbose` adds detailed subsystem information:
- Status: risk configuration, component health, monitoring summary
- Start: startup checklist with step-by-step progress
- Stop: shutdown progress display
- Health: component health table, monitoring details, recovery status

## Testing

```bash
pytest tests/test_runtime.py -v
```

89 tests covering:
- Model invariants (frozen dataclasses, enum values)
- Event bus: subscribe, unsubscribe, publish, clear, listener count
- Subscription manager: add, remove, enable, disable, list, clear
- Market stream: start, stop, double-start, quote callback, event bus
- Pipeline scheduler: start, stop, pause, resume, execute once
- Heartbeat monitor: start, stop, beat, missed detection
- Health check: register, report, summary, is_healthy, reset
- Runtime engine: full lifecycle, broker integration, stream integration,
  scheduler integration, heartbeat integration, report generation, health
  checks
- Exception hierarchy: all runtime exceptions are proper subtypes


## Architecture

For technical details on how the runtime is managed in the background, see [Runtime Service Architecture](RUNTIME_SERVICE.md).
