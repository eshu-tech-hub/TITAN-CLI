# Recovery & Fault Tolerance Framework

TITAN's centralized Recovery & Fault Tolerance Framework automatically detects
failures, applies recovery strategies, preserves runtime state, and safely
resumes operation.

## Architecture

```
Monitoring
    |
    v
Alerting
    |
    v
Recovery Manager
    |
    +-- Retry Engine
    +-- Circuit Breaker
    +-- Checkpoint Manager
    +-- State Manager
    +-- Broker Reconnector
    +-- Graceful Shutdown
    +-- Health Recovery
    |
    v
Recovered Runtime
```

## Core Components

### RecoveryManager

Central orchestrator for all failure recovery. No subsystem should implement
its own retry, reconnect, or recovery logic.

```python
from titan.recovery import RecoveryManager, ComponentType, RecoveryStrategy

mgr = RecoveryManager()

# Request recovery for a failed component
report = mgr.request_recovery(
    component=ComponentType.PIPELINE,
    failure_reason="Stage 3 timed out",
    strategy=RecoveryStrategy.RETRY,
)
```

### RetryEngine

Configurable retry engine with multiple backoff modes:

- `IMMEDIATE` — no delay between attempts
- `FIXED_DELAY` — constant delay between attempts
- `LINEAR_BACKOFF` — delay = base_delay * attempt_number
- `EXPONENTIAL_BACKOFF` — delay = base_delay * 2^(attempt-1)
- `EXPONENTIAL_JITTER` — exponential + random jitter

```python
from titan.recovery import RetryEngine, RetryPolicy, RetryMode

policy = RetryPolicy(
    mode=RetryMode.EXPONENTIAL_BACKOFF,
    max_attempts=5,
    base_delay_seconds=1.0,
    max_delay_seconds=30.0,
)
engine = RetryEngine(policy)
status = engine.execute(lambda: try_operation())
```

### CircuitBreaker

Three-state circuit breaker (CLOSED → OPEN → HALF_OPEN) with configurable
thresholds and automatic reset.

```python
from titan.recovery import CircuitBreaker, CircuitBreakerConfig

cb = CircuitBreaker(
    CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout_seconds=30.0,
        success_threshold=3,
    )
)
result = cb.call(lambda: check_service())
```

### CheckpointManager

Persists runtime state for recovery across components.

```python
from titan.recovery import CheckpointManager, ComponentType

mgr = CheckpointManager()
mgr.save("cp1", ComponentType.PIPELINE, {"stage": "qualification"})
cp = mgr.load("cp1")
```

### StateManager

Captures and restores runtime state snapshots with pluggable capture/restore
functions.

```python
from titan.recovery import StateManager

mgr = StateManager()
mgr.register_capture("pipeline_progress", lambda: {"stage": "running"})
snapshot = mgr.capture()
mgr.restore(snapshot)
```

### BrokerReconnector

Handles broker session reconnection with heartbeat verification and
subscription restoration.

```python
from titan.recovery import BrokerReconnector

reconnector = BrokerReconnector()
status = reconnector.reconnect(
    action=lambda: broker.login(),
    heartbeat=lambda: broker.is_alive(),
    subscriptions=("NSE", "BSE"),
    restore_subscriptions=lambda subs: broker.subscribe(subs),
)
```

### GracefulShutdown

Orchestrates multi-stage shutdown with timeout per stage, hooks, and abort
capability.

```python
from titan.recovery import GracefulShutdown, ShutdownStage

shutdown = GracefulShutdown()
shutdown.register_hook(
    ShutdownStage.FLUSHING_LOGS,
    lambda: logger.flush(),
)
shutdown.execute()
```

### HealthRecovery

Monitors component health and triggers automatic recovery.

```python
from titan.recovery import HealthRecovery, ComponentType

hr = HealthRecovery()
hr.register_health_check("pipeline_health", lambda: check_pipeline(), ComponentType.PIPELINE)
results = hr.run_health_checks()
```

## Recovery Strategies

| Strategy | Description |
|----------|-------------|
| `RETRY` | Retry the failed operation with backoff |
| `RESTART` | Restore state and restart the component |
| `RECONNECT` | Reconnect to external service/broker |
| `SHUTDOWN` | Gracefully shut down the system |
| `FAILOVER` | Fail over to backup instance |
| `ESCALATE` | Escalate to higher-level recovery |

## Quality

- Frozen dataclasses throughout immutable models
- Strict typing with comprehensive type hints
- Constructor injection (dependency injection)
- Thread-safe via `threading.Lock` on all mutable state
- Deterministic recovery — no silent failures
- All recovery flows through `RecoveryManager`

## CLI Integration

The recovery subsystem is exposed through the `titan recovery` command group:

```bash
titan recovery status          # Show recovery status
titan recovery status --json   # Status as JSON
titan recovery status --verbose  # With recent history

titan recovery retry <component> <reason>  # Trigger recovery
titan recovery retry pipeline "connection lost" --json

titan recovery checkpoint save --component pipeline --id cp-1  # Save checkpoint
titan recovery checkpoint list   # List all checkpoints
titan recovery checkpoint latest --component pipeline  # Latest checkpoint
titan recovery restore <checkpoint_id>  # Restore from checkpoint

titan recovery circuit list    # List circuit breakers
titan recovery circuit reset --name <name>  # Reset a circuit breaker
```

### Supported Components

Use any `ComponentType` value: `pipeline`, `broker_session`, `market_stream`, `execution_engine`, `portfolio`, `monitoring`, `alerting`, `risk_module`, `configuration`, `backtesting`, `paper_trading`, `logging`.

## TUI Integration

The Monitoring & Alerting screen (F6) provides real-time visualization of recovery state:

- **RecoveryStatusWidget**: Displays recovery status, attempt counts, last strategy, and recovered components from `RecoveryManager.generate_report()`
- **MonitoringEventsWidget**: Displays recent recovery events from `RecoveryManager.get_recovery_history()`

Data is read-only. The TUI reads `RecoveryManager.generate_report()` and `RecoveryManager.get_recovery_history()` every second via `build_monitoring_state()` in `titan/tui/layout.py`.
