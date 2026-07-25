# Audit & Compliance Framework

## Overview

TITAN's centralized Audit & Compliance Framework records immutable audit events for every critical action performed by TITAN. It provides traceability, compliance support, forensic analysis, and post-trade investigation capabilities.

**AuditManager is TITAN's single authority for audit records. No subsystem may write audit records directly. All audit events must pass through AuditManager.**

## Architecture

```
Subsystems
    |
    v
AuditManager  (single authority)
    |
    +-- Event Validation & Hash Computation
    +-- Sequence Number Assignment
    +-- Hash Chain Maintenance
    |
    v
AuditStorage  (persistence layer)
    |
    +-- InMemoryAuditStorage  (testing / dev)
    +-- JsonLinesAuditStorage  (persistent JSONL)
    |
    v
IntegrityEngine  (tamper detection)
    |
    v
AuditQueryEngine  (search & retrieval)
    |
    v
AuditReport  (summary statistics)
```

## Quick Start

```python
from titan.audit import AuditManager, AuditSource, AuditCategory, AuditSeverity

# Create manager (defaults to in-memory storage)
manager = AuditManager()

# Record an audit event
event = manager.record(
    source=AuditSource.EXECUTION,
    category=AuditCategory.ORDER_PLACED,
    severity=AuditSeverity.INFO,
    action="order.place",
    trade_id="tr-001",
    order_id="ord-001",
    metadata={"symbol": "RELIANCE", "quantity": 10},
)

# Verify integrity
report = manager.verify_integrity()
assert report.is_valid

# Generate summary
summary = manager.generate_report()
print(f"Total events: {summary.total_events}")
```

## Persistent Storage

```python
from titan.audit import AuditManager, JsonLinesAuditStorage

storage = JsonLinesAuditStorage("./logs/audit.jsonl")
manager = AuditManager(storage=storage)

# Events are now persisted to disk
manager.record(
    source=AuditSource.RUNTIME,
    category=AuditCategory.SYSTEM_START,
    severity=AuditSeverity.INFO,
    action="system.start",
)
```

## Querying Events

```python
from titan.audit import AuditQuery, AuditSource, AuditCategory

# Search by source
events = manager.search(AuditQuery(source=AuditSource.EXECUTION))

# Search by trade ID
events = manager.query.query_by_trade_id("tr-001")

# Search by time range
from datetime import datetime, timezone
events = manager.query.query_time_range(
    time_from=datetime(2026, 7, 10, tzinfo=timezone.utc),
    time_to=datetime(2026, 7, 11, tzinfo=timezone.utc),
)

# Combined filters
query = AuditQuery(
    source=AuditSource.EXECUTION,
    severity=AuditSeverity.ERROR,
    pipeline_id="pl-001",
)
events = manager.search(query)
```

## Integrity Verification

Every event is SHA-256 hashed. Each event's `previous_hash` links to its predecessor, forming an immutable chain:

```python
report = manager.verify_integrity()
print(f"Chain valid: {report.is_valid}")
print(f"Total events: {report.total_events}")
print(f"Violations: {report.violation_count}")

for violation in report.violations:
    print(f"  {violation.violation_type}: {violation.description}")
```

## Audit Sources

| Source | Description |
|--------|-------------|
| `CONFIGURATION` | Config changes and reloads |
| `RUNTIME` | Runtime lifecycle events |
| `MONITORING` | Health checks and metrics |
| `ALERTING` | Alert triggers and resolutions |
| `RECOVERY` | Recovery and retry operations |
| `PIPELINE` | Pipeline execution events |
| `DECISION` | Trade decision events |
| `RISK` | Risk management events |
| `PORTFOLIO` | Portfolio operations |
| `EXECUTION` | Order execution events |
| `OMS` | Order management system |
| `BROKER` | Broker connectivity |
| `PAPER_TRADING` | Paper trading events |
| `BACKTESTING` | Backtesting events |
| `USER` | User-initiated actions |

## Audit Categories

28 categories covering the full lifecycle: `config_change`, `system_start`, `system_stop`, `connection`, `data_received`, `pipeline_executed`, `order_placed`, `order_filled`, `order_cancelled`, `risk_breach`, `alert_triggered`, `checkpoint_saved`, `user_action`, `error`, and more.

## Severity Levels

| Level | Usage |
|-------|-------|
| `debug` | Verbose diagnostic information |
| `info` | Normal operational events |
| `warning` | Conditions requiring attention |
| `error` | Failed operations |
| `critical` | System-threatening conditions |

## Dependency Injection

AuditManager accepts any `AuditStorage` implementation:

```python
from titan.audit import AuditStorage, AuditEvent

class CustomStorage(AuditStorage):
    def append(self, event: AuditEvent) -> None:
        # Your implementation
        ...
    def append_batch(self, events) -> None:
        ...
    def load_all(self) -> list[AuditEvent]:
        ...
    def count(self) -> int:
        ...
    def clear(self) -> None:
        ...

manager = AuditManager(storage=CustomStorage())
```

## Thread Safety

- `AuditManager.record()` is fully thread-safe.
- `InMemoryAuditStorage` uses a `threading.Lock` for all mutations.
- `JsonLinesAuditStorage` uses a `threading.Lock` for all file I/O.
- Hash chain assignment is atomic.

## Rules

1. **No trading logic** - Audit records actions, never drives them.
2. **No execution logic** - Audit observes, never acts.
3. **Immutable records** - Frozen dataclasses, no mutation.
4. **No event deletion** - Storage is append-only.
5. **Single authority** - All events pass through AuditManager.

## Testing

```bash
pytest tests/test_audit.py -v
```

79 tests covering: event creation, serialization, hash chain integrity, tamper detection, storage backends, query engine, reports, dependency injection, and thread safety.

## CLI Integration

The audit subsystem is exposed through the `titan audit` command group:

```bash
titan audit status             # Show audit subsystem status
titan audit status --json      # Status as JSON
titan audit verify             # Verify audit chain integrity

titan audit search             # Search all events (default limit: 20)
titan audit search --source pipeline  # Filter by source
titan audit search --category system_start  # Filter by category
titan audit search --severity error   # Filter by severity
titan audit search --action "config"  # Filter by action substring
titan audit search --limit 5   # Limit results
titan audit search --json      # Search results as JSON

titan audit export             # Export to audit_export.json
titan audit export -o audit.json  # Custom output path
titan audit export --format csv  # Export as CSV
titan audit export --limit 100  # Limit exported events

titan audit stats              # Show event statistics
titan audit stats --json       # Stats as JSON
```

### Search Filters

All search filters are optional and combined with AND logic:

| Filter | Description |
|--------|-------------|
| `--source` | Filter by event source (e.g., `pipeline`, `execution`) |
| `--category` | Filter by event category (e.g., `system_start`, `order_placed`) |
| `--severity` | Filter by severity (`debug`, `info`, `warning`, `error`, `critical`) |
| `--action` | Filter by action substring (case-insensitive) |
| `--limit` | Maximum number of events to return |
