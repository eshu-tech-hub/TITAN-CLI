# ADR-030: Recovery & Fault Tolerance Framework

## Status

Accepted

## Context

TITAN operates in an environment where failures are inevitable:
network partitions, broker disconnections, resource exhaustion,
process crashes. Without a centralized recovery framework,
each subsystem would implement ad-hoc retry and recovery logic,
leading to inconsistent behaviour, cascading failures, and
difficult debugging.

## Decision

Build a centralized **Recovery & Fault Tolerance Framework** with the
following design:

1. **Single authority** — `RecoveryManager` is the sole entry point
   for all failure recovery. No subsystem implements its own retry,
   reconnect, or recovery logic.

2. **Modular components** — Each responsibility (retry, backoff,
   circuit breaking, checkpointing, state capture, reconnect,
   shutdown, health monitoring) lives in its own class.

3. **Strategy pattern** — Recovery strategies are enum-valued and
   dispatched by the manager. Adding a new strategy requires no
   changes to existing strategies.

4. **Deterministic** — All recovery operations are deterministic.
   No silent failures. Every recovery attempt is recorded in a
   `RecoveryReport`.

5. **Thread-safe** — All mutable state is protected by
   `threading.Lock`. The framework supports concurrent recovery
   requests.

6. **Constructor injection** — All dependencies are injected via
   constructor parameters. No global state, no singletons.

7. **Frozen models** — All model dataclasses use `frozen=True,
   slots=True` for immutability and memory efficiency.

## Consequences

### Positive

- Consistent recovery behaviour across all subsystems
- Single place to configure retry policies, timeouts, thresholds
- Comprehensive recovery history for debugging and auditing
- Easy to add new recovery strategies without changing existing code
- Thread-safe by default — safe for concurrent recovery requests
- No database dependency — checkpoints and state are in-memory by
  default, with a clear extension path for persistent storage

### Negative

- All recovery must route through `RecoveryManager`, adding one
  hop of indirection
- In-memory checkpoints are lost on process restart — persistent
  storage adapter needed for production use

## Future Compatibility

The framework is designed to support distributed recovery without
redesign:

- `RecoveryManager` can be wrapped in a gRPC/REST service
- `CheckpointManager` can be backed by Redis, SQLite, or S3
- Circuit breakers can be shared across nodes via distributed state
- Leader election can be added as a new recovery strategy
- Kubernetes restart policies are a drop-in replacement for the
  shutdown component

## Testing Strategy

- Unit tests for each component in isolation
- All policies and strategies tested with edge cases (zero attempts,
  timeout, exceptions, concurrent access)
- Frozen dataclass immutability verified
- Dependency injection verified
- Concurrent recovery requests tested with threads
