# ADR-027: Institutional Logging Framework

**Status:** Accepted (Milestone M6.5.2)

**Date:** 2026-07-08

**Author:** TITAN Architecture Team

## Context

Before this ADR, TITAN logging was handled by `titan/core/logger.py`,
which configured a module-level `loguru` logger with a simple console
and rotating file sink.

This created several problems:

- **No centralized logger management.** Any module could import `logger`
  from `loguru` directly, bypassing configuration.
- **No structured logging.** Log entries were free-form strings with no
  typed fields, no correlation IDs, no pipeline context.
- **No context propagation.** There was no mechanism to propagate a
  pipeline ID, trade ID, or order ID across module boundaries without
  manually threading the value through every function call.
- **No formatter abstraction.** All output used the same format. JSON
  output for ELK/Loki ingestion was not possible without modifying
  the shared logger.
- **No handler abstraction.** Adding a new sink (syslog, CloudWatch,
  OpenTelemetry) required modifying global configuration.
- **No per-module isolation.** All modules shared the same logger
  configuration — silencing one module silenced all modules.
- **No thread safety guarantee.** The module-level `logger` object
  was shared across threads with no isolation of context.

## Problem Statement

TITAN needs an institutional logging framework that:

1. Provides a centralized `LoggerManager` as the single authority for
   creating and configuring loggers.
2. Produces structured log entries with typed fields: timestamp, level,
   module, component, message, metadata, exception, duration, and
   contextual IDs (pipeline, correlation, request, trade, order,
   position, runtime).
3. Propagates context automatically across thread and async boundaries
   using `contextvars`.
4. Supports multiple formatters (human-readable console, JSON, compact)
   selectable per handler.
5. Supports multiple handlers (console, rotating file, JSON file) with
   independent level thresholds.
6. Is thread-safe by design — no shared mutable state between threads.
7. Generates a `LoggingReport` for diagnostics (handler count, dropped
   messages, registered components).
8. Has zero business logic, zero trading logic, zero execution logic.
9. Preserves backward compatibility with existing `titan/core/logger.py`
   until migration is complete.

## Decision

We introduce `titan/logging/` with the following architecture.

### Architecture

```
                    LoggerManager (singleton)
                         │
               ┌─────────┴──────────┐
               │                    │
        StructuredLogger      Handler ABC
               │              ├── ConsoleHandler
               │              ├── FileHandler
               │              └── JSONFileHandler
               │
        LoggingContext (contextvars)
               │
        Formatter ABC
            ├── ConsoleFormatter
            ├── JSONFormatter
            └── CompactFormatter
```

### Module Layout

```
titan/logging/
    __init__.py    — Public API exports
    models.py      — LogLevel, LogEntry, LoggingConfig, LoggingReport
    exceptions.py  — Exception hierarchy
    context.py     — LoggingContext (contextvars-based propagation)
    formatter.py   — ConsoleFormatter, JSONFormatter, CompactFormatter
    handlers.py    — ConsoleHandler, FileHandler, JSONFileHandler
    logger.py      — StructuredLogger
    manager.py     — LoggerManager (singleton, configuration)
```

### LogLevel

A `StrEnum` with six levels matching standard practice:

```python
class LogLevel(StrEnum):
    TRACE = "TRACE"       # 5
    DEBUG = "DEBUG"       # 10
    INFO = "INFO"         # 20
    WARNING = "WARNING"   # 30
    ERROR = "ERROR"       # 40
    CRITICAL = "CRITICAL" # 50
```

Each level maps to an integer for comparison via `to_int()` / `from_int()`.

### LogEntry

A frozen dataclass capturing every structured field:

```python
@dataclass(frozen=True, slots=True)
class LogEntry:
    timestamp: datetime
    level: LogLevel
    module: str
    component: str
    message: str
    metadata: dict[str, Any]
    exception: str | None
    duration_ms: float | None
    pipeline_id: str | None
    correlation_id: str | None
    request_id: str | None
    trade_id: str | None
    order_id: str | None
    position_id: str | None
    runtime_id: str | None
```

All context fields default to `None` and are populated automatically from
`LoggingContext`.

### LoggingContext

Uses `contextvars.ContextVar` for thread-safe, async-safe context
propagation:

```python
LoggingContext.bind(pipeline_id="pl-001", trade_id="tr-xyz")

# Automatic — all loggers see the current context
logger.info("Processing trade")

# Temporary override within a scope
with LoggingContext.scope(trade_id="tr-789"):
    logger.info("Inside scope")

# Clear all context
LoggingContext.clear()
```

Design decisions:

- **`contextvars` over `threading.local`.** `contextvars` works correctly
  with `asyncio` tasks — context is inherited by child tasks and restored
  on task switch. `threading.local` does not support this.
- **No implicit global state.** `LoggingContext` exposes explicit
  `bind()` and `scope()` methods. There is no magic thread-local import.
- **Safe default.** All context fields default to `None`. Modules that
  do not use context IDs produce valid log entries without modification.

### StructuredLogger

Provides a fluent API matching standard logging patterns:

```python
logger = StructuredLogger(module="execution", component="order_manager")

logger.trace("message")           # LogLevel.TRACE
logger.debug("message")           # LogLevel.DEBUG
logger.info("message")            # LogLevel.INFO
logger.warning("message")         # LogLevel.WARNING
logger.error("message")           # LogLevel.ERROR
logger.critical("message")        # LogLevel.CRITICAL
logger.exception("msg", exc_info) # LogLevel.ERROR with traceback
logger.duration("msg", ms)        # Any level with duration_ms
```

Each method accepts `**metadata` for arbitrary key-value pairs.

The logger captures `LoggingContext.current()` at call time and
constructs a `LogEntry` with all context fields populated.

### Formatters

Three formatters implement the `Formatter` ABC:

| Formatter | Output | Use Case |
|---|---|---|
| `ConsoleFormatter` | `2026-07-08 12:00:00 \| INFO \| comp \| msg [pipeline=pl-1]` | Interactive CLI |
| `JSONFormatter` | `{"timestamp":"...","level":"INFO",...}` | ELK / Loki ingestion |
| `CompactFormatter` | `12:00:00 I comp msg` | High-throughput logs |

`ConsoleFormatter` supports ANSI colorization. ERROR and CRITICAL levels
use red, WARNING uses yellow, INFO uses green, DEBUG uses cyan.

### Handlers

Three handlers implement the `Handler` ABC:

| Handler | Sink | Level Filter | Rotation |
|---|---|---|---|
| `ConsoleHandler` | stdout (INFO-), stderr (ERROR+) | Per-handler | N/A |
| `FileHandler` | Rotating text file | Per-handler | Size-based (configurable MB) |
| `JSONFileHandler` | Rotating JSONL file | Per-handler | Size-based (configurable MB) |

Handlers use `should_emit(level)` to filter before formatting. Dropped
message counts are tracked per handler for reporting.

### LoggerManager

The central singleton that:

1. **Creates loggers** via `get_logger(module, component)` — creates on
   first access, returns cached instance thereafter.
2. **Configures handlers** globally — all existing and future loggers
   receive the configured handlers.
3. **Provides singleton access** via `LoggerManager.instance()`.
4. **Generates reports** via `generate_report()` — returns `LoggingReport`
   with level, component count, handler configs, dropped messages.
5. **Supports reconfigure** — `reconfigure(config)` replaces all handlers
   and updates existing loggers.

```python
class LoggerManager:
    @classmethod
    def instance(cls) -> LoggerManager: ...
    def configure(self, config: LoggingConfig) -> None: ...
    def reconfigure(self, config: LoggingConfig) -> None: ...
    def get_logger(self, module: str, component: str | None = None) -> StructuredLogger: ...
    def generate_report(self) -> LoggingReport: ...
```

### LoggingConfig and HandlerConfig

```python
@dataclass(frozen=True, slots=True)
class HandlerConfig:
    handler_type: HandlerType
    level: LogLevel = LogLevel.DEBUG
    formatter: FormatterType = FormatterType.CONSOLE
    file_path: str = ""
    max_size_mb: int = 100
    backup_count: int = 5

@dataclass(frozen=True, slots=True)
class LoggingConfig:
    level: LogLevel = LogLevel.INFO
    handlers: tuple[HandlerConfig, ...]
    component: str = "titan"
```

Default configuration includes a console handler at INFO level and a
rotating file handler at DEBUG level writing to `./logs/titan.log`.

### LoggingReport

```python
@dataclass(frozen=True, slots=True)
class LoggingReport:
    level: LogLevel
    component_count: int
    handlers: tuple[HandlerConfig, ...]
    dropped_messages: int
    warnings: tuple[str, ...]
    errors: tuple[str, ...]
```

## Alternatives Considered

### 1. Extending loguru Directly

We considered adding structured logging methods directly to loguru's
logger via `logger.patch()` and `logger.bind()`.

**Rejected because:**
- loguru's `bind()` returns a new logger instance — the original is
  unchanged. This makes context propagation stateful and error-prone.
- loguru has no concept of a `LoggerManager` — anyone can import
  `logger` from `loguru` and configure it independently.
- The structured fields we need (pipeline_id, trade_id, etc.) are not
  loguru concepts — they would require string interpolation in every
  call site.
- Replacing loguru in the future would require changing every import.

### 2. Python Standard `logging` Module

We considered using the stdlib `logging` module with custom
`Formatter` and `Handler` subclasses.

**Rejected because:**
- stdlib logging is synchronous and blocking — problematic for
  high-throughput trading pipelines.
- stdlib logging lacks built-in structured/JSON output.
- stdlib logging uses `%`-formatting by default, which is error-prone
  with structured data.
- No built-in context propagation — requires manual `LoggerAdapter`
  wrapping.
- No built-in rotation with size limits in the standard `FileHandler`.

### 3. structlog

We considered using the `structlog` library, which provides structured
logging with processors, bound loggers, and context variables.

**Rejected because:**
- Adds a significant external dependency for what is fundamentally a
  thin wrapper around loguru.
- `structlog` is framework-agnostic — it works with stdlib logging,
  loguru, or raw `print()`. This flexibility adds complexity without
  benefit for TITAN's single-backend architecture.
- The processor pipeline model is powerful but opaque — debugging
  log entry transformation requires mental stack traces.
- loguru is already a project dependency — wrapping it directly is
  simpler and avoids version conflicts.

### 4. Thread-Local Context

We considered `threading.local()` for context propagation.

**Rejected because:**
- `threading.local()` does not work with `asyncio` — context is not
  inherited by child tasks and is not restored on task switches.
- TITAN's runtime uses threading (daemon threads for streaming,
  scheduling, heartbeat). `contextvars` is the correct Python 3
  mechanism for both threading and async.

### 5. Single Global Logger

We considered using a single global `StructuredLogger` instance with
no per-module isolation.

**Rejected because:**
- Without per-module loggers, filtering by component is impossible
  except via string matching in the message.
- Different modules legitimately need different log levels during
  debugging — making one module TRACE while others stay INFO.
- The `LoggerManager` pattern is familiar from every major logging
  framework and is the expected pattern for Python developers.

## Consequences

### Positive

1. **Single logging authority.** `LoggerManager` is the only way to
   create loggers. No module can bypass configuration or instantiate
   its own logging setup.

2. **Structured by default.** Every log entry is a typed `LogEntry`
   dataclass with pre-defined fields. Metadata is structured JSON,
   not string interpolation.

3. **Automatic context propagation.** Pipeline IDs, trade IDs, order
   IDs, and correlation IDs are propagated automatically via
   `contextvars`. No manual threading of context objects.

4. **Thread-safe.** `contextvars` provides per-task isolation.
   `LoggingContext` operations are atomic. Handler emit is protected
   by `Lock` where needed (file rotation).

5. **Pluggable formatters.** Adding a new output format (e.g., OTLP
   for OpenTelemetry) requires only a new `Formatter` subclass.

6. **Pluggable handlers.** Adding a new sink (CloudWatch, Syslog,
   Loki) requires only a new `Handler` subclass.

7. **Per-handler level filtering.** Console can show INFO+ while the
   file handler captures DEBUG+. Error handler can filter to CRITICAL
   only for alerting.

8. **Diagnostic reporting.** `generate_report()` provides machine-readable
   diagnostics: active handlers, dropped message counts, registered
   components.

9. **Zero business logic.** The logging framework imports no trading
   logic, no execution logic, no broker SDKs. It is a pure logging
   framework.

10. **49 unit tests.** Full coverage of models, context, formatters,
    handlers, logger, manager, and integration paths. Zero I/O
    dependencies in tests.

### Negative

1. **No network handlers.** Syslog, CloudWatch, Loki, and OpenTelemetry
   exporters are not implemented. These require production experience
   to design correctly.

2. **No async handlers.** All handlers are synchronous. For
   high-throughput logging to network sinks, an async handler with
   batching would be needed. This is deferred.

3. **No sampling.** There is no rate-limiting or log sampling
   mechanism. High-frequency TRACE logging could overwhelm handlers
   in production.

4. **No structured exception serialization.** Exceptions are captured
   as formatted traceback strings, not as structured error objects.
   This is acceptable for the current milestone but could be enhanced.

### Neutral

1. **loguru as backend.** The `StructuredLogger` wraps loguru internally.
   This is an implementation detail — consumers import from
   `titan.logging`, not from `loguru`. The backend can be replaced
   without changing any consumer code.

2. **No async support.** The framework is synchronous. TITAN's
   codebase is also synchronous. Async logging is unnecessary until
   the runtime or broker layer adopts async I/O.

3. **`HandlerConfig` frozen dataclass.** Handler configuration is
   immutable after creation. Runtime handler changes require
   `reconfigure()` which rebuilds all handlers.

## Trade-offs

| Trade-off | Choice | Rationale |
|---|---|---|
| `contextvars` vs `threading.local` | `contextvars` | Async-safe, inherited by child tasks |
| loguru backend vs structlog vs stdlib | loguru | Already a dependency, performant, rotation built-in |
| Singleton vs injected LoggerManager | Singleton | Convenience without precluding DI |
| Frozen dataclasses vs mutable config | Frozen | Immutability guarantees, thread-safe |
| `LogEntry` as intermediate object vs direct format | `LogEntry` | Enables multiple formatters, testable |
| Per-handler level vs global level | Per-handler | Console can be INFO, file DEBUG, alert CRITICAL |

## Future Evolution

### Distributed Tracing

`LoggingContext` can be extended with OpenTelemetry span context:

```python
from opentelemetry import trace

LoggingContext.bind(
    trace_id=trace.get_current_span().get_span_context().trace_id,
    span_id=trace.get_current_span().get_span_context().span_id,
)
```

The `JSONFormatter` would include `trace_id` and `span_id` fields
for correlation with distributed traces.

### Central Log Aggregation

The `JSONFileHandler` produces JSONL files compatible with:

- **ELK Stack** — Filebeat ships JSONL to Logstash/Elasticsearch.
- **Grafana Loki** — Promtail ships JSONL to Loki.
- **AWS CloudWatch** — CloudWatch agent ships JSONL.
- **Azure Monitor** — Azure Monitor agent ships JSONL.

A future `NetworkHandler` could send directly to these endpoints:

```python
HandlerConfig(
    handler_type=HandlerType.NETWORK,
    endpoint="https://logs.example.com:8080",
    batch_size=100,
    flush_interval_seconds=5,
)
```

### OpenTelemetry Exporter

A `TelemetryHandler` could implement the OpenTelemetry `LogRecord`
exporter for native OTLP output:

```python
HandlerConfig(
    handler_type=HandlerType.OTEL,
    endpoint="http://otel-collector:4318/v1/logs",
)
```

### Log Sampling

A `SamplingHandler` wrapper could apply rate limiting:

```python
handler = SamplingHandler(
    inner=ConsoleHandler(...),
    rate=100,  # max messages per second
    burst=50,
)
```

This would prevent log storms during market volatility while
preserving critical ERROR and CRITICAL messages.

### Correlation with Configuration System

The `LoggerManager.read_config(config.LoggingConfig)` method could
bridge the config module's `LoggingConfig` model to the logging
module's `LoggingConfig`:

```python
from titan.config.models import LoggingConfig as ConfigLoggingConfig

def configure_from_titan_config(self, cfg: ConfigLoggingConfig) -> None:
    level = LogLevel(cfg.level)
    handlers = (
        HandlerConfig(
            handler_type=HandlerType.FILE,
            level=LogLevel.DEBUG,
            file_path=cfg.file,
            max_size_mb=cfg.max_size_mb,
            backup_count=cfg.backup_count,
        ),
    )
    self.configure(LoggingConfig(level=level, handlers=handlers))
```

### Async Handlers

For production deployment with network sinks, async handlers with
batching and backpressure:

```python
class AsyncNetworkHandler(Handler):
    async def emit(self, entry: LogEntry) -> None:
        await self._session.post(self._endpoint, json=entry)
```

This would require an async-compatible `LoggerManager` with
`emit_async()` and `await logger.info_async()`.

## Migration Path

### Phase 1: Parallel Operation (Milestone M6.5.2)

The `titan/logging/` module is introduced alongside the existing
`titan/core/logger.py`. No existing code is changed.

- `LoggerManager` is available for new consumers.
- Legacy `titan/core/logger.py` continues to work.
- Documentation directs all new development to use `LoggerManager`.

### Phase 2: Core Migration (Future Milestone)

Core infrastructure modules migrate to the new framework:

- `titan/execution/orchestrator.py`
- `titan/broker/yfinance/client.py`
- `titan/broker/yfinance/auth.py`
- `titan/cli.py`

Each module receives a `StructuredLogger` via `LoggerManager.get_logger()`.

### Phase 3: Full Adoption (Future Milestone)

All TITAN modules use the new logging framework.

- `titan/core/logger.py` is deprecated.
- Ad-hoc `from loguru import logger` imports are removed.
- The `loguru` dependency is removed.

## Relationship to Other ADRs

### ADR-026 (Configuration System)

The logging framework is configured via its own `LoggingConfig` model.
At integration time, the `ConfigManager` from ADR-026 will provide the
logging section to `LoggerManager.configure()`. No circular dependency
exists — the logging module has its own models and defaults.

### ADR-025 (Live Runtime)

The runtime engine will use `StructuredLogger` for all operational
logging. The `LoggingContext` will propagate `runtime_id` automatically.

### ADR-021 (Execution Orchestrator)

The execution orchestrator will use `StructuredLogger` with trade IDs
and order IDs propagated via `LoggingContext`.

### ADR-022 (Trade Pipeline)

The trade pipeline will log pipeline execution with pipeline IDs,
correlation IDs, and duration metrics via `StructuredLogger`.
