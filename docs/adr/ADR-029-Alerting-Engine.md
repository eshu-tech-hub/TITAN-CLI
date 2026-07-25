# ADR-029: Alerting & Notification Engine

**Status:** Accepted (Milestone M6.5.4)

**Date:** 2026-07-08

**Author:** TITAN Architecture Team

## Context

Before this ADR, TITAN had no centralized alerting system. Errors,
warnings, and critical events were handled ad-hoc — printed to
console via log messages, logged to files, or silently swallowed.

This created several problems:

- **No structured alerting.** There was no `Alert` dataclass with
  severity, source, title, message, timestamp, and status.
  Operational events were indistinguishable from debug messages.
- **No notification channels.** Operators had no way to receive
  alerts outside of watching the console. Email, Telegram, Slack,
  and webhook notifications required manual integration per module.
- **No alert rules.** There was no rule engine to evaluate conditions,
  suppress duplicates, apply cooldowns, or escalate repeated failures.
- **No alert history.** Past alerts were not stored, queryable, or
  reportable. Operators could not see which alerts fired, when, or
  whether they were acknowledged or resolved.
- **No centralized alert manager.** Every module that wanted to notify
  needed to implement its own notification logic. There was no single
  entry point for firing alerts.

## Problem Statement

TITAN needs an institutional alerting and notification engine that:

1. Provides a centralized `AlertManager` as the single authority for
   dispatching notifications from any subsystem.
2. Supports five alert levels: INFO, WARNING, ERROR, CRITICAL,
   EMERGENCY — ordered for comparison and filtering.
3. Supports twelve alert sources: RUNTIME, PIPELINE, MONITORING,
   BROKER, OMS, EXECUTION, PORTFOLIO, RISK, CONFIGURATION, LOGGING,
   PAPER_TRADING, BACKTESTING, SYSTEM.
4. Tracks alert lifecycle through five states: NEW, ACKNOWLEDGED,
   RESOLVED, SUPPRESSED, ESCALATED.
5. Provides a rule engine that evaluates conditions, enforces
   cooldowns, suppresses duplicates, applies rate limiting, and
   escalates repeated alerts.
6. Supports five notification channels: CONSOLE, EMAIL, TELEGRAM,
   SLACK, WEBHOOK — with future support for SMS, Teams, Discord,
   and push notifications.
7. Stores complete alert history with notification attempts and
   rule evaluation results.
8. Generates `AlertReport` with active alerts, critical counts,
   source and level breakdowns, and operational warnings.
9. Has zero trading logic, zero execution logic, zero market
   analysis — alerting only.
10. Is thread-safe by design.
11. Retries failed notification deliveries with configurable retry
    count.
12. Supports graceful degradation — channel failures do not prevent
    other channels from delivering.

## Decision

We introduce `titan/alerting/` with the following architecture.

### Architecture

```
Subsystems
    │
    ▼
AlertManager (single entry point)
    │
    ├── AlertEngine
    │       │
    │       ├── AlertRuleEngine
    │       │       ├── Threshold evaluation
    │       │       ├── State-change evaluation
    │       │       ├── Duplicate suppression
    │       │       ├── Cooldown enforcement
    │       │       ├── Rate limiting
    │       │       └── Escalation
    │       │
    │       └── AlertHistory
    │               ├── Store / Retrieve
    │               ├── Acknowledge / Resolve
    │               ├── Query by source / level / status
    │               └── Report generation
    │
    └── ChannelManager
            ├── ConsoleChannel
            ├── EmailChannel
            ├── TelegramChannel
            ├── SlackChannel
            └── WebhookChannel
```

### Data Flow

```
Subsystem detects issue
    │
    ▼
AlertManager.fire(level, source, title, message)
    │
    ▼
AlertEngine creates Alert
    │
    ▼
AlertRuleEngine evaluates all registered rules
    ├── Match → proceed
    ├── Suppressed → drop (cooldown/duplicate/rate-limit)
    └── Escalated → mark status ESCALATED
    │
    ▼
ChannelManager.dispatch(alert)
    ├── ConsoleChannel → print
    ├── EmailChannel → SMTP (future)
    ├── TelegramChannel → bot API (future)
    ├── SlackChannel → webhook (future)
    └── WebhookChannel → HTTP POST (future)
    │
    ▼
AlertHistory.store(alert, notifications, rule_results)
    │
    ▼
AlertManager returns Alert to caller
```

### Module Layout

```
titan/alerting/
    __init__.py    — Public API exports
    models.py      — All dataclasses and enums
    exceptions.py  — Exception hierarchy
    rules.py       — AlertRuleEngine
    engine.py      — AlertEngine
    channels.py    — NotificationChannel ABC + implementations
    history.py     — AlertHistory
    manager.py     — AlertManager (top-level orchestrator)
```

### Models

All data models are frozen dataclasses with slots:

**Alert** — The core alert with alert_id, level, source, title,
message, timestamp, status, acknowledgement/resolution fields,
escalation count, rule name, metadata, and tags.

**AlertRule** — Rule definition with name, condition (Callable),
level, source filter, cooldown, duplicate suppression, max
escalations, escalation delay, enabled flag, and description.

**AlertRuleResult** — Result of evaluating a rule against an alert
with matched, escalated, suppressed flags and reason.

**ChannelConfig** — Channel configuration with type, enabled flag,
minimum alert level, and type-specific config map.

**NotificationAttempt** — Record of a delivery attempt with channel,
timestamp, result (SUCCESS/FAILED/RETRYING), error message, and
retry count.

**AlertHistoryEntry** — Full history record with alert, notification
attempts, rule results, and timestamp.

**AlertReport** — Diagnostic report with total/active/critical counts,
by-source and by-level breakdowns, and warnings.

### AlertLevel

```python
class AlertLevel(str, Enum):
    INFO = "info"          # Informational message
    WARNING = "warning"    # Requires attention
    ERROR = "error"        # Operation failed
    CRITICAL = "critical"  # Subsystem degraded
    EMERGENCY = "emergency" # Platform-level failure
```

Ordered via `level_rank()`: INFO=0, WARNING=1, ERROR=2, CRITICAL=3,
EMERGENCY=4. Used for channel filtering (e.g., "only dispatch
CRITICAL+ to PagerDuty").

### AlertSource

```python
class AlertSource(str, Enum):
    RUNTIME = "runtime"
    PIPELINE = "pipeline"
    MONITORING = "monitoring"
    BROKER = "broker"
    OMS = "oms"
    EXECUTION = "execution"
    PORTFOLIO = "portfolio"
    RISK = "risk"
    CONFIGURATION = "configuration"
    LOGGING = "logging"
    PAPER_TRADING = "paper_trading"
    BACKTESTING = "backtesting"
    SYSTEM = "system"
```

### AlertStatus

```python
class AlertStatus(str, Enum):
    NEW = "new"               # Unacknowledged
    ACKNOWLEDGED = "acknowledged"  # Seen by operator
    RESOLVED = "resolved"     # Condition cleared
    SUPPRESSED = "suppressed" # Rules suppressed this alert
    ESCALATED = "escalated"   # Escalated after repeated matches
```

### AlertRuleEngine

The rule engine provides:

- **Threshold evaluation** — `evaluate_threshold(value, warning, critical)`
  creates alerts when a metric crosses warning or critical thresholds.
- **State-change evaluation** — `evaluate_state_change(key, new_state)`
  creates alerts when a tracked state transitions.
- **Condition evaluation** — `evaluate(alert)` runs the registered
  rule's condition callable and checks constraints.
- **Duplicate suppression** — Identical alerts (same rule, title,
  source) are suppressed within the dedup cache window.
- **Cooldown** — After a rule matches, further matches are suppressed
  for `cooldown_seconds`.
- **Rate limiting** — Maximum 10 matches per 60 seconds per rule.
- **Escalation** — Repeated matches increment escalation count and
  mark the alert as ESCALATED.
- **Source filtering** — Rules can restrict to specific sources.
- **Enable/disable** — Rules can be enabled or disabled at runtime.

### AlertEngine

Orchestrates rule evaluation and notification:

- `fire(level, source, title, message)` — creates an Alert, evaluates
  all rules, dispatches via ChannelManager, stores in history.
- `fire_from_monitoring(level, source, title, message, metric_name,
  metric_value)` — bridge from the monitoring framework.
- `acknowledge(alert_id)`, `resolve(alert_id)` — lifecycle management.
- `get_alert()`, `get_active_alerts()`, `get_alerts_by_source()`,
  `get_alerts_by_level()` — query methods.
- `generate_report()` — delegates to AlertHistory.

### NotificationChannel ABC

```python
class NotificationChannel(ABC):
    @abstractmethod
    def send(self, alert: Alert) -> NotificationResult: ...
    @property
    @abstractmethod
    def channel_type(self) -> ChannelType: ...
```

Five implementations:

| Channel | Implementation | Production |
|---|---|---|
| `ConsoleChannel` | `print()` to stdout | Full |
| `EmailChannel` | SMTP stub (no-op) | Stub |
| `TelegramChannel` | Bot API stub (no-op) | Stub |
| `SlackChannel` | Webhook stub (no-op) | Stub |
| `WebhookChannel` | HTTP POST stub (no-op) | Stub |

Channels with network I/O use `try/except` for graceful failure.
The `ChannelManager` retries failed deliveries up to 3 times.

### ChannelManager

- `register_channel(channel, config)` — register a channel with
  optional configuration.
- `unregister_channel(channel_type)` — remove a channel.
- `dispatch(alert)` — iterate registered channels, filter by
  `enabled` and `min_level`, send with retry, collect
  `NotificationAttempt` results.
- `registered_channels()` — list active channel types.

### AlertHistory

- `store(alert, notifications, rule_results)` — persist an alert
  with its delivery and evaluation metadata.
- `get(alert_id)`, `get_entry(alert_id)` — retrieve.
- `acknowledge(alert_id, by)`, `resolve(alert_id, by)` — status
  transitions (creates new frozen Alert).
- `get_active()`, `get_by_source()`, `get_by_level()` — queries.
- `generate_report()` — produces `AlertReport` with statistics.

### AlertManager

Top-level orchestrator that:

- Defaults with a `ConsoleChannel` registered at INFO level.
- Provides `fire()`, `fire_from_monitoring()`, `register_rule()`,
  `register_channel()`, `acknowledge()`, `resolve()`, `get_alert()`,
  `get_active_alerts()`, `generate_report()`, `reset()`.
- Exposes `engine`, `rules`, `channels`, `history` properties.

### Exception Hierarchy

```
AlertingError (Exception)
├── AlertingInputError (ValueError)
├── AlertingRuleError
├── AlertingEngineError
├── AlertingChannelError
├── AlertingDispatchError
└── AlertingHistoryError
```

## Alternatives Considered

### 1. Monitoring Framework Extension

We considered adding alerting to the monitoring framework
(`titan/monitoring/`) as an AlertLevel and AlertSource on the
HealthEngine.

**Rejected because:**
- Monitoring collects metrics and evaluates health. Alerting
  dispatches notifications. These are distinct concerns with
  different lifecycle, state, and extensibility requirements.
- The alerting module has its own rule engine, channel management,
  retry logic, and history — none of which belong in a metrics
  collector.
- Separation allows each framework to evolve independently.
  Monitoring can add new metric types without affecting alerting,
  and alerting can add new channels without affecting monitoring.

### 2. External Alerting Service

We considered using an external service like PagerDuty, Opsgenie,
or Sentry for all alert management.

**Rejected because:**
- TITAN is a desktop/CLI application that must operate offline.
  An external dependency for core alerting is unacceptable.
- Local alerting (console) must always work regardless of network
  connectivity.
- External services are valuable as notification channel targets
  (future export), not as the primary alerting infrastructure.

### 3. Rule Engine with External DSL

We considered using a rules engine with a DSL (e.g., JSON rules,
Python `ast` evaluation, or a custom expression language).

**Rejected because:**
- TITAN's rules are Python conditions evaluated against Python
  objects. A DSL adds complexity, parsing overhead, and a
  learning curve for zero benefit.
- The `Callable[[Alert], bool]` interface is the simplest possible
  rule condition — it is type-safe, testable, and familiar to every
  Python developer.
- JSON rules would lose type safety and require a condition parser
  that maps to Python predicates.

### 4. Singleton Channel Manager

We considered making `ChannelManager` a singleton with global state.

**Rejected because:**
- Singleton global state makes testing impossible without teardown.
- Dependency injection through the constructor is the established
  TITAN pattern.
- `AlertManager` is the singleton entry point; `ChannelManager` is
  a replaceable component within it.

## Consequences

### Positive

1. **Single alerting authority.** `AlertManager` is the sole entry
   point for all notifications. No subsystem may send notifications
   directly.

2. **Comprehensive rule engine.** Threshold alerts, state-change
   alerts, duplicate suppression, cooldown, rate limiting, and
   escalation are built-in and configurable per rule.

3. **Pluggable channels.** Adding SMS, Teams, Discord, or push
   notifications requires only a new `NotificationChannel` subclass
   and registration with `ChannelManager`.

4. **Thread-safe by design.** All mutable state is protected by
   `Lock`.

5. **Graceful degradation.** Channel failures are caught and reported
   as `NotificationAttempt` entries. Other channels continue to
   deliver. The `EmailChannel`, `TelegramChannel`, `SlackChannel`,
   and `WebhookChannel` gracefully handle missing configuration with
   typed exceptions.

6. **Retry logic.** Failed channel deliveries are retried up to 3
   times with full error reporting.

7. **Complete history.** Every alert, every notification attempt, and
   every rule evaluation result is stored and queryable.

8. **Diagnostic reporting.** `generate_report()` provides machine-
   readable diagnostics: total/active/critical alerts, breakdowns by
   source and level, and operational warnings.

9. **Monitoring bridge.** `fire_from_monitoring()` provides a direct
   integration path from the monitoring framework's health engine to
   the alerting engine.

10. **Frozen dataclasses.** All model classes are immutable,
    providing thread safety and hashability guarantees.

11. **Constructor injection.** All components accept their
    dependencies via the constructor, supporting testing and
    customization.

### Negative

1. **No production channel implementations.** `EmailChannel`,
   `TelegramChannel`, `SlackChannel`, and `WebhookChannel` are
   stubs that raise `AlertingDispatchError`. Production-ready
   implementations require SMTP/bot/webhook SDK integration with
   proper configuration.

2. **No escalation policies.** The current escalation model is a
   simple counter on the alert. There is no configurable escalation
   policy (e.g., "alert level increases after N matches" or "route
   to different channels after escalation").

3. **No alert grouping.** Related alerts (e.g., "broker connection
   lost" repeated 10 times) are not grouped into a single incident.
   Each alert is independent.

4. **No scheduled maintenance mode.** There is no mechanism to
   suppress alerts during scheduled downtime or maintenance windows.

### Neutral

1. **Console default.** `AlertManager` registers a `ConsoleChannel`
   at INFO level by default. This ensures alerts are visible without
   configuration, matching the existing `print()`-based logging
   behavior.

2. **Condition callables.** Alert rule conditions are `Callable[[Alert], bool]`.
   This is flexible but relies on the caller to provide a correct
   predicate. There is no compile-time validation of rule conditions.

3. **In-memory history.** Alert history is stored in memory. Long-term
   persistence requires an exporter (similar to the monitoring
   framework's exporter pattern).

## Trade-offs

| Trade-off | Choice | Rationale |
|---|---|---|
| Frozen vs mutable models | Frozen | Thread safety, hashability, immutability guarantees |
| `Callable[[Alert], bool]` vs DSL | Callable | Type-safe, testable, familiar to Python developers |
| In-memory vs database history | In-memory | Simplicity; persistence is a future concern |
| Constructor injection vs singleton | Constructor | Testability, explicit dependencies |
| Retry with backoff vs simple retry | Simple retry | 3 retries with no delay; backoff adds complexity |
| Network channels as stubs vs exc | Stubs raise DispatchError | Clean failure semantics; production impl adds SDK |
| Monitoring bridge vs direct import | Bridge in AlertEngine | Decouples alerting from monitoring module |
| 5 alert levels vs 3 or 7 | 5 levels | Matches common practice (INFO through EMERGENCY) |

## Future Evolution

### PagerDuty Integration

A `PagerDutyChannel` can implement `NotificationChannel`:

```python
class PagerDutyChannel(NotificationChannel):
    def __init__(self, api_key: str, service_id: str):
        self._api_key = api_key
        self._service_id = service_id

    def send(self, alert: Alert) -> NotificationResult:
        payload = {
            "routing_key": self._api_key,
            "event_action": "trigger",
            "payload": {
                "summary": alert.title,
                "severity": alert.level.value,
                "source": alert.source.value,
                "custom_details": dict(alert.metadata),
            },
        }
        requests.post("https://events.pagerduty.com/v2/enqueue", json=payload)
        return NotificationResult.SUCCESS
```

### Opsgenie / ServiceNow / Incident.io

Each follows the same pattern — implement `NotificationChannel`,
call the target API, return `NotificationResult`.

### OpenTelemetry Events

An `OTelEventChannel` can convert alerts to OpenTelemetry events
and export via OTLP:

```python
class OTelEventChannel(NotificationChannel):
    def send(self, alert: Alert) -> NotificationResult:
        event = Event(
            name=f"titan.alert.{alert.level.value}",
            timestamp=alert.timestamp,
            attributes={
                "alert.id": alert.alert_id,
                "alert.title": alert.title,
                "alert.source": alert.source.value,
                "alert.level": alert.level.value,
            },
        )
        self._provider.add_event(event)
        return NotificationResult.SUCCESS
```

### Cloud Alert Providers

AWS CloudWatch Alarms, Azure Monitor Alerts, and GCP Cloud
Monitoring can be notification targets via webhook channel or
dedicated implementations.

### SMS / Teams / Discord / Push

Each requires a new `NotificationChannel` subclass:

```python
class SMSPChannel(NotificationChannel): ...
class TeamsChannel(NotificationChannel): ...
class DiscordChannel(NotificationChannel): ...
class PushChannel(NotificationChannel): ...
```

### Alert Correlation

Future alert correlation can group related alerts into incidents:

```python
class Incident:
    incident_id: str
    alerts: list[Alert]
    status: IncidentStatus
    created_at: datetime
    resolved_at: datetime | None
```

### Persistence

Alert history can be persisted to SQLite or DuckDB:

```python
class PersistentAlertHistory(AlertHistory):
    def __init__(self, db_path: str = "./data/alerts.db"):
        self._conn = sqlite3.connect(db_path)
        self._create_tables()

    def store(self, alert, notifications, rule_results):
        self._conn.execute("INSERT INTO alerts ...")
```

## Migration Path

### Phase 1: Introduction (Milestone M6.5.4)

The `titan/alerting/` module is introduced. The `AlertManager` is
available for use by all subsystems. Console notifications work
immediately. Network channels are stubs.

### Phase 2: Monitoring Integration (Future Milestone)

The monitoring framework's `MonitoringManager` calls
`AlertManager.fire_from_monitoring()` when health status changes
or metrics cross thresholds:

```python
# In MonitoringManager
if system_health.overall == HealthStatus.CRITICAL:
    self._alert_manager.fire_from_monitoring(
        level="critical",
        source="monitoring",
        title="System Health Critical",
        message=f"{system_health.critical_count} subsystems critical",
    )
```

### Phase 3: Subsystem Adoption (Future Milestone)

Each subsystem registers rules and fires alerts through
`AlertManager`:

```python
# In Broker health check
if not broker.is_connected():
    alert_manager.fire(
        level=AlertLevel.CRITICAL,
        source=AlertSource.BROKER,
        title="Broker Disconnected",
        message=f"{broker.name} connection lost at {timestamp}",
        metadata={"broker": broker.name, "last_connected": str(last_connected)},
    )
```

### Phase 4: Production Channels (Future Milestone)

Network channel implementations are added for Email, Telegram,
Slack, and Webhook with proper configuration and credential
management.

## Relationship to Other ADRs

### ADR-028 (Monitoring & Telemetry)

The monitoring framework collects metrics and evaluates health.
The alerting framework converts health degradation and metric
threshold breaches into actionable notifications.
`AlertEngine.fire_from_monitoring()` bridges the two frameworks.

### ADR-027 (Logging Framework)

The logging framework captures structured diagnostic events. The
alerting framework captures operational alerts. Both use frozen
dataclasses, dependency injection, and thread safety. Alerts can
be logged as structured entries via the logging framework.

### ADR-026 (Configuration System)

The alerting framework's channel configuration belongs in
`TitanConfig`. A future `AlertingConfig` dataclass will hold
channel endpoints, credentials, and default levels.
