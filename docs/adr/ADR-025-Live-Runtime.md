# ADR-025: Live Runtime and Streaming Engine

**Status:** Accepted (Milestone M6.4)

**Date:** 2026-07-07

**Author:** TITAN Architecture Team

## Context

TITAN's Trade Pipeline (ADR-022) orchestrates the complete trading
workflow from market data to broker execution. The Pipeline Scheduler
(ADR-022) enables periodic execution. The Paper Trading Engine
(ADR-023) provides broker-independent simulation. The Backtesting
Engine (ADR-024) replays historical data through the pipeline.

Before this ADR:

- There was no production runtime that kept the TITAN platform alive
  during market hours.
- Market data streaming (WebSocket, tick-by-tick) was unscoped — the
  existing `MarketDataProvider` interface only supported snapshot
  `quote()` calls.
- There was no typed event bus for decoupled inter-component
  communication.
- No component health monitoring, heartbeat mechanism, or subscription
  management existed.
- There was no graceful lifecycle (start, stop, pause, resume) for the
  TITAN platform as a whole.
- The runtime was invoked manually — no scheduler ran the pipeline on
  a configurable interval.

## Problem Statement

The TITAN platform needs a production-grade runtime that:

1. Streams real-time market data without blocking the pipeline.
2. Executes the Trade Pipeline on a configurable schedule.
3. Monitors component health and runtime liveliness.
4. Manages symbol subscriptions for market data feeds.
5. Provides a typed event system for decoupled communication.
6. Supports graceful start, stop, pause, resume, and restart.
7. Reports runtime status, health, and metrics on demand.
8. Handles component failures without crashing the platform.
9. Integrates with the existing Broker abstraction without modification.

## Decision

We introduce `titan/runtime/` with the following modules and
architecture.

### Architecture

```
RuntimeEventBus (typed pub/sub)
     │
     ├── MarketStream ─── reads ─── StreamDataSource (protocol)
     │
     ├── PipelineScheduler ─── runs ─── TradePipeline (via runner)
     │
     ├── HeartbeatMonitor ─── emits ─── HEARTBEAT_TICK events
     │
     ├── SubscriptionManager ─── tracks ─── symbol+exchange pairs
     │
     ├── HealthCheck ─── aggregates ─── component health status
     │
     └── RuntimeEngine ─── orchestrates ─── lifecycle (start/stop/pause/resume)
```

### RuntimeEventBus

A lightweight typed publish-subscribe event bus with zero external
dependencies. Components publish and subscribe to `RuntimeEventType`
enum values. The bus supports multiple listeners per event type,
unsubscribe, clear, and listener count introspection.

The event bus is the central communication backbone — every runtime
component is wired to the same bus instance via the `RuntimeEngine`
constructor.

### MarketStream and StreamDataSource Protocol

Rather than extending the `Broker` ABC with streaming methods (which
would break all existing broker adapters and the PaperBroker), we
introduce a `StreamDataSource` protocol in `titan/runtime/stream.py`:

```python
class StreamDataSource(Protocol):
    def connect(self) -> ConnectionStatus: ...
    def disconnect(self) -> ConnectionStatus: ...
    def is_connected(self) -> bool: ...
    def subscribe(self, symbol: str, exchange: Exchange) -> None: ...
    def unsubscribe(self, symbol: str, exchange: Exchange) -> None: ...
    def read(self) -> Quote | None: ...
```

This protocol:
- Keeps the `Broker` ABC unchanged (backward compatible).
- Enables mock sources in unit tests.
- Allows any WebSocket or REST-based source to be adapted.
- Is optional — the runtime works without a stream.

`MarketStream` wraps the source in a background daemon thread that
reads quotes and distributes them via the `on_quote` callback and the
event bus.

### PipelineScheduler

Runs the Trade Pipeline on a configurable interval in a background
daemon thread:

- Default interval: 60 seconds.
- Errors during pipeline execution are caught, logged as events, and
  do not stop the scheduler loop.
- Pause/resume controls whether the pipeline executes on each tick.
- `execute_once()` runs the pipeline immediately without affecting the
  schedule.
- The `RuntimeEngine` overrides the scheduler runner with its internal
  `_pipeline_runner` method.

### HeartbeatMonitor

A periodic tick generator that detects missed heartbeats:

- Emits `HEARTBEAT_TICK` at a configurable interval (default: 10s).
- Tracks `missed_count` — consecutive ticks without a `beat()` call.
- Emits `HEARTBEAT_MISSED` when ticks are missed.
- Emits `HEARTBEAT_RESTORED` when a `beat()` call resumes.
- Threaded with daemon=True.

### HealthCheck

A component health aggregator with four health states:

| State | Meaning |
|---|---|
| HEALTHY | Operating normally |
| DEGRADED | Operating with reduced capability |
| UNHEALTHY | Component has failed |
| UNKNOWN | Not yet reported |

Supports register, unregister, report status, get, summary, is_healthy,
has_degraded, has_unhealthy, and reset.

The `RuntimeEngine` registers five components: runtime, broker, stream,
scheduler, heartbeat.

### SubscriptionManager

Tracks which symbols and exchanges the runtime is subscribed to:

- Add/remove with duplicate detection.
- Enable/disable individual subscriptions.
- List active (enabled) and all subscriptions.
- Publishes SUBSCRIPTION_ADDED and SUBSCRIPTION_REMOVED events.
- Supports five subscription types: SYMBOL, OPTION_CHAIN, INDEX,
  WATCHLIST, MARKET_DEPTH.

### RuntimeEngine

The lifecycle orchestrator that coordinates all components:

```
Lifecycle:
  START: broker.connect() → stream.start() → scheduler.start() → heartbeat.start()
  STOP:  heartbeat.stop() → scheduler.stop() → stream.stop() → broker.disconnect()
  PAUSE: scheduler.pause()
  RESUME: scheduler.resume()
  RESTART: stop() → start()
```

- All threads are daemon threads (don't block process exit).
- Scheduler thread join has a 5-second timeout.
- Error handling: any start failure sets status to ERROR and raises.
- Health is reported on every lifecycle transition.
- Events are published on every transition.

### RuntimeReport

A frozen dataclass snapshot of the runtime state at a point in time:

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

### Exception Hierarchy

```
RuntimeError
    ├── StreamError
    │   └── StreamConnectionError
    ├── SchedulerError
    ├── SubscriptionError
    ├── HeartbeatError
    └── HealthError
```

## Alternatives Considered

### 1. Extending the Broker ABC with Streaming Methods

We considered adding `subscribe(symbol, exchange)`, `unsubscribe()`, and
`on_quote()` to the `Broker` interface. This would have required all
existing broker adapters (AngelOneBroker, PaperBroker) to implement
streaming methods, even though only a subset of live brokers support
WebSocket data.

**Rejected because:**
- Breaks backward compatibility with all existing broker adapters.
- PaperBroker would need no-op stream methods.
- Not all brokers provide streaming data.
- Mixing snapshot and streaming APIs in one interface violates the
  Interface Segregation Principle.

### 2. asyncio Event Loop

We considered using `asyncio` for the runtime event loop, with coroutines
for the stream reader, scheduler, and heartbeat.

**Rejected because:**
- The existing TITAN codebase (pipeline, broker, execution) is fully
  synchronous — there are no async methods anywhere.
- Introducing asyncio would require wrapping sync calls in
  `run_in_executor`, adding complexity without benefit.
- The runtime needs at most 3-4 concurrent threads — threading with
  `queue.Queue` is simpler, more testable, and matches the existing
  code style.
- All existing broker SDKs (Angel One, etc.) are synchronous.

### 3. External Message Queue (Redis Pub/Sub, RabbitMQ)

We considered using Redis or RabbitMQ for the event bus.

**Rejected because:**
- The runtime operates within a single process. An external message
  queue adds deployment complexity, a runtime dependency, and a
  single point of failure for no benefit.
- The event bus is purely internal — no cross-process or cross-host
  communication is needed at this stage.
- A lightweight in-process pub/sub is sufficient for the current
  architecture and can be replaced later if distributed runtime
  is needed.

### 4. External Process Monitoring (Supervisor, systemd)

We considered relying on external process monitors for health checking
and restart.

**Accepted as complementary.** The runtime's built-in health check
and heartbeat are for internal monitoring and dashboarding. External
process monitors (Kubernetes, systemd, Supervisor) should be used
for process-level restart at the deployment layer. The two approaches
are complementary, not competing.

### 5. Separate CLI Process for Runtime Management

We considered creating a separate CLI subcommand (`titan runtime`)
that runs as a daemon process, managed by `start`, `stop`, `status`,
and `logs` subcommands.

**Deferred.** The current `RuntimeEngine` is a programmable class that
can be embedded in any Python process. A CLI wrapper is future work.

## Consequences

### Positive

1. **Production lifecycle management.** The runtime provides
   deterministic start, stop, pause, resume, and restart — essential
   for production operations.

2. **Decoupled architecture.** The event bus enables components to
   communicate without direct dependencies. New components can be
   added by subscribing to existing events.

3. **Healthy-by-default.** Every component has health reporting.
   The runtime can be monitored and alert on degradation before
   failure.

4. **No changes to existing interfaces.** The Broker ABC, Trade
   Pipeline, and Execution Orchestrator are completely unchanged.
   The runtime wraps them without modification.

5. **Thread-safe by design.** Each component runs in its own thread
   with explicit stop events and queue-based communication. No
   shared mutable state between threads.

6. **Graceful shutdown.** Components stop in reverse order with
   thread join timeouts. Daemon threads ensure the process can exit
   even if a component hangs.

7. **Deterministic testing.** The `StreamDataSource` protocol and
   injectable dependencies make every component testable without
   network, WebSocket, or broker connections.

8. **89 unit tests.** Full coverage of all components, edge cases,
   and lifecycle scenarios.

### Negative

1. **No automatic reconnection.** The `MarketStream` does not
   automatically reconnect on source failure. Reconnection requires
   a runtime restart or external process management.

2. **No WebSocket implementation.** The `StreamDataSource` protocol
   is defined, but no concrete WebSocket data source is provided.
   Users must supply their own adapter.

3. **Single-process only.** The event bus and subscription manager
   are in-memory — the runtime cannot be distributed across multiple
   processes or hosts without additional infrastructure.

4. **No persistent state.** Runtime status, health, and subscription
   state are lost on process restart. Recovery requires external
   coordination (Kubernetes, etc.).

### Neutral

1. **Threading over asyncio.** The threading approach is simpler
   for the existing synchronous codebase but consumes more memory
   per component than an async equivalent.

2. **Scheduler runner override.** The `RuntimeEngine` overrides the
   scheduler's runner with its `_pipeline_runner` method. Custom
   runners passed via constructor are replaced. This is intentional
   — the engine must own the runner to track execution counts and
   use the correct broker — but it may surprise users who pass a
   custom runner.

3. **Pipeline symbol="" convention.** The `_pipeline_runner` calls
   `pipeline.run(symbol="")`. The pipeline's intelligence engines
   are expected to determine symbols autonomously from watchlists
   and market data. This works for the current architecture but
   may need refinement for multi-symbol runtime modes.

## Trade-offs

| Trade-off | Choice | Rationale |
|---|---|---|
| Threading vs asyncio | Threading | Matches existing sync codebase; simpler threading model |
| Protocol vs ABC | Protocol | Lighter weight; no class hierarchy needed for data sources |
| In-process vs external event bus | In-process | No deployment dependency; replaceable later |
| New stream interface vs extend Broker | New interface | Backward compatibility; ISP compliance |
| Daemon vs non-daemon threads | Daemon | Process can exit even if components hang |

## Future Evolution

### Multi-Broker Support

The `RuntimeEngine` currently accepts a single `Broker`. Future versions
could accept a `dict[str, Broker]` with per-symbol routing via the
`SubscriptionManager`. The event bus would need additional event types
for per-broker health.

### Automatic Stream Reconnection

The `MarketStream` could be extended with exponential backoff
reconnection logic. The current architecture supports this — the
event bus already emits `STREAM_CONNECTED` and `STREAM_DISCONNECTED`
events that a reconnection manager could observe.

### Distributed Runtime

The `RuntimeReport` is a serializable frozen dataclass. A remote
monitoring agent could:
- Poll `generate_report()` at intervals.
- Stream reports to a dashboard.
- Accept remote lifecycle commands via the event bus.

### WebSocket Data Source

A concrete `WebSocketStreamDataSource` implementing the
`StreamDataSource` protocol is the natural next step. It would
accept a WebSocket URL, authentication token, and symbol list.

### CLI Integration

A `titan runtime start|stop|status` CLI subcommand would wrap the
`RuntimeEngine` in a long-running process with log output and signal
handling.

### Kubernetes Integration

- Health check endpoints (`/healthz`, `/readyz`) returning
  `HealthCheck.summary()`.
- Prometheus metrics for pipeline executions, quote rates, and
  component health.
- ConfigMap-driven subscription configuration.
- Graceful SIGTERM handling via `RuntimeEngine.stop()`.

## Relationship to Other ADRs

### ADR-018 (Broker Abstraction)

The runtime consumes the `Broker` ABC defined in ADR-018. It calls
`broker.connect()` and `broker.disconnect()` as part of the lifecycle.
It does not extend or modify the Broker interface.

The `StreamDataSource` protocol is separate from the Broker ABC —
market data streaming is an orthogonal concern handled by the runtime.

### ADR-019 (Order Management System)

The runtime does not interact with the OMS directly. The OMS is
embedded within the `ExecutionOrchestrator`, which is invoked by the
`TradePipeline`, which is invoked by the `PipelineScheduler`.

### ADR-021 (Execution Orchestrator)

Same as ADR-019 — the runtime does not call the orchestrator directly.
The orchestrator is invoked within the pipeline's EXECUTION stage.

### ADR-022 (Trade Pipeline)

The `PipelineScheduler` invokes `TradePipeline.run()` on each execution
cycle. The `RuntimeEngine._pipeline_runner` creates the bridge between
the scheduler and the pipeline.

The pipeline's existing hooks (before_stage, after_stage, on_complete,
on_error) remain available for monitoring and metrics.

### ADR-023 (Paper Trading)

The `PaperBroker` from ADR-023 is a valid `Broker` implementation for
the runtime. It can be used in dry-run mode to validate the runtime
without a live broker connection.

### ADR-024 (Backtesting Engine)

The backtesting engine (ADR-024) and the runtime engine (this ADR) are
complementary. The backtesting engine replays historical data through
the pipeline synchronously. The runtime engine operates on live data
asynchronously. Both reuse the same pipeline, broker, and execution
layers.
