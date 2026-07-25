# ADR-031: Audit & Compliance Framework

## Status

Accepted

## Date

2026-07-10

## Context

TITAN requires a centralized, immutable audit trail for every critical action across all subsystems. This is necessary for:

- **Traceability**: Post-trade investigation and forensics.
- **Compliance**: Regulatory requirements for Indian markets (SEBI).
- **Integrity**: Tamper detection for audit records.
- **Operational visibility**: Understanding system behavior over time.

No existing TITAN subsystem provides centralized audit logging. The logging framework (`titan.logging`) handles operational logs but is not designed for immutable, hash-chained audit records.

## Decision

Build `titan/audit/` as a standalone module with the following design:

### Single Authority

`AuditManager` is the sole entry point for all audit events. No subsystem writes audit records directly. This guarantees:

- Consistent sequence numbering.
- Unbroken hash chains.
- Centralized validation.

### Immutable Events

`AuditEvent` is a frozen dataclass. Once constructed, it cannot be modified. This prevents accidental or malicious alteration of audit records.

### Hash Chain Integrity

Each event's SHA-256 hash includes its `previous_hash`, forming a blockchain-like chain. Any modification to a persisted event breaks the chain and is detected by `IntegrityEngine.verify()`.

### Storage Abstraction

`AuditStorage` is an abstract interface with two implementations:

- `InMemoryAuditStorage`: Thread-safe, for testing and short-lived sessions.
- `JsonLinesAuditStorage`: Persistent, append-only JSONL format.

Future implementations (SQLite, PostgreSQL, cloud storage) can be added without modifying the core framework.

### Query Engine

`AuditQueryEngine` provides declarative filtering across all stored events. Filters are composable and use AND logic. The engine works against any `AuditStorage` backend.

## Consequences

### Positive

- Immutable audit trail with tamper detection.
- Clean separation from trading and execution logic.
- Thread-safe for concurrent subsystem access.
- Storage-agnostic design allows backend evolution.
- Comprehensive test coverage (79 tests).

### Negative

- In-memory storage loses data on restart (mitigated by JsonLinesAuditStorage).
- Hash computation adds small overhead per event (SHA-256 is fast; negligible).
- Query engine scans all events in memory (acceptable for current scale; database-backed storage planned for future).

### Risks

- Hash chain corruption if sequence numbering fails (mitigated by thread-safe atomic counter).
- JSONL file growth without rotation (future: add rotation policy).

## Alternatives Considered

1. **Python `logging` with custom handler**: Rejected. Logging is designed for operational messages, not immutable audit records with hash chains.

2. **SQLite-backed storage from day one**: Rejected. Adds external dependency. JsonLines is sufficient for initial deployment; SQLite can be added later via the `AuditStorage` interface.

3. **Blockchain library**: Rejected. Over-engineered for TITAN's requirements. A simple hash chain provides sufficient tamper detection.

## Module Structure

```
titan/audit/
    __init__.py       # Public API with __all__
    models.py         # AuditEvent, enums, AuditReport (frozen dataclasses)
    exceptions.py     # AuditError hierarchy
    event.py          # Event creation, validation, hash computation
    storage.py        # AuditStorage ABC + implementations
    integrity.py      # IntegrityEngine (hash chain verification)
    query.py          # AuditQueryEngine + AuditQuery
    manager.py        # AuditManager (single authority)
```

## Testing

79 tests covering:

- Event creation and serialization round-trip.
- Hash chain correctness and tamper detection.
- In-memory and JSONL storage operations.
- Query engine with all filter types.
- Report generation.
- Dependency injection with custom storage.
- Thread safety under concurrent recording.
- Exception hierarchy validation.
