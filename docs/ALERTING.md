# TITAN Alerting & Notification Engine

## Overview

The Alerting Engine is TITAN's centralized operational notification
layer. It converts monitoring events, runtime failures, broker issues,
execution failures, and risk events into actionable notifications.

**It does not perform market analysis or trading.**

No subsystem may send notifications directly. Every notification must
pass through `AlertManager`.

## Architecture

```
Subsystems
    │
    ▼
AlertManager
    │
    ├── AlertEngine
    │       ├── AlertRuleEngine (threshold, state-change, dedup, cooldown, escalation)
    │       └── AlertHistory (storage, query, report)
    │
    └── ChannelManager
            ├── ConsoleChannel (default, always active)
            ├── EmailChannel (stub, requires SMTP config)
            ├── TelegramChannel (stub, requires bot token)
            ├── SlackChannel (stub, requires webhook URL)
            └── WebhookChannel (stub, requires URL)
```

## Module Layout

```
titan/alerting/
    __init__.py      Public API exports
    models.py        Frozen dataclasses and enums
    exceptions.py    Exception hierarchy
    rules.py         AlertRuleEngine (conditions, thresholds, state-change)
    engine.py        AlertEngine (alert creation, rule evaluation, dispatch)
    channels.py      NotificationChannel ABC + 5 implementations
    history.py       AlertHistory (storage, query, report)
    manager.py       AlertManager (top-level orchestrator)
```

## Quick Start

### Basic Usage

```python
from titan.alerting import AlertManager, AlertLevel, AlertSource

# Create the manager (auto-registers ConsoleChannel)
manager = AlertManager()

# Fire an alert
alert = manager.fire(
    level=AlertLevel.WARNING,
    source=AlertSource.MONITORING,
    title="High CPU Usage",
    message="CPU at 95% for over 5 minutes",
    metadata={"cpu": 95, "threshold": 90},
)

# Acknowledge an alert
manager.acknowledge(alert.alert_id, acknowledged_by="operator")

# Resolve an alert
manager.resolve(alert.alert_id, resolved_by="system")

# Get active alerts
active = manager.get_active_alerts()

# Generate a report
report = manager.generate_report()
```

### Alert Rules

```python
from titan.alerting import AlertManager, AlertLevel, AlertSource, AlertRule

manager = AlertManager()

# Register a rule with a condition
def high_latency_rule(alert) -> bool:
    return alert.metadata.get("latency_ms", 0) > 1000

manager.register_rule(
    AlertRule(
        name="high_latency",
        condition=high_latency_rule,
        level=AlertLevel.WARNING,
        source=AlertSource.BROKER,
        cooldown_seconds=300,  # 5 minutes between alerts
        suppress_duplicates=True,
        description="Fires when broker latency exceeds 1000ms",
    )
)

# Now fire alerts that will be evaluated against this rule
alert = manager.fire(
    level=AlertLevel.WARNING,
    source=AlertSource.BROKER,
    title="High Broker Latency",
    message="Latency at 1500ms",
    metadata={"latency_ms": 1500},
    rule_name="high_latency",
)
```

### Threshold Alerts

```python
from titan.alerting import AlertRuleEngine, AlertSource

engine = AlertRuleEngine()

# Register a rule for threshold evaluation
engine.register_rule(
    AlertRule(
        name="cpu_threshold",
        condition=lambda a: True,  # Threshold logic is external
        level=AlertLevel.WARNING,
        cooldown_seconds=60,
    )
)

# Evaluate a threshold
result = engine.evaluate_threshold(
    name="cpu_threshold",
    value=95.0,
    warning_threshold=80.0,
    critical_threshold=90.0,
    source=AlertSource.MONITORING,
    title="High CPU Usage",
    message_template="CPU at {value}%",
)
```

### State-Change Alerts

```python
# Track state transitions
result = engine.evaluate_state_change(
    name="broker_connection",
    key="broker:paper:connection",
    new_state="disconnected",
    source=AlertSource.BROKER,
    title="Broker Disconnected",
    message="YFinance broker connection lost",
)
```

### Notification Channels

```python
from titan.alerting import (
    AlertManager, AlertLevel, AlertSource,
    SlackChannel, ChannelConfig, ChannelType,
)

manager = AlertManager()

# Register a Slack channel
manager.register_channel(
    SlackChannel(
        webhook_url="https://hooks.slack.com/services/...",
        channel="#titan-alerts",
    ),
    ChannelConfig(
        channel_type=ChannelType.SLACK,
        min_level=AlertLevel.WARNING,  # Only WARNING+
    ),
)

# Register an Email channel
manager.register_channel(
    EmailChannel(
        to_addresses=("ops@example.com",),
        from_address="titan@example.com",
    ),
    ChannelConfig(
        channel_type=ChannelType.EMAIL,
        min_level=AlertLevel.ERROR,  # Only ERROR+
    ),
)
```

### Alert History

```python
# Query alerts
alert = manager.get_alert("alert:1:1234567890.0")

# Get all active alerts
active = manager.get_active_alerts()

# Get alerts by source
broker_alerts = manager.engine.get_alerts_by_source(AlertSource.BROKER)

# Get alerts by level
critical_alerts = manager.engine.get_alerts_by_level(AlertLevel.CRITICAL)

# Generate a diagnostic report
report = manager.generate_report()
print(f"Total alerts: {report.total_alerts}")
print(f"Active alerts: {report.active_alerts}")
print(f"Critical alerts: {report.critical_alerts}")
print(f"By source: {report.alerts_by_source}")
print(f"By level: {report.alerts_by_level}")
```

## Models

### Alert

| Field | Type | Default |
|---|---|---|
| `alert_id` | `str` | required |
| `level` | `AlertLevel` | required |
| `source` | `AlertSource` | required |
| `title` | `str` | required |
| `message` | `str` | required |
| `timestamp` | `datetime` | `utcnow()` |
| `status` | `AlertStatus` | `NEW` |
| `acknowledged_at` | `datetime \| None` | `None` |
| `acknowledged_by` | `str` | `""` |
| `resolved_at` | `datetime \| None` | `None` |
| `resolved_by` | `str` | `""` |
| `escalated_at` | `datetime \| None` | `None` |
| `escalation_count` | `int` | `0` |
| `rule_name` | `str` | `""` |
| `metadata` | `Mapping[str, Any]` | `{}` |
| `tags` | `tuple[str, ...]` | `()` |

### AlertLevel

| Level | Rank | Description |
|---|---|---|
| `INFO` | 0 | Informational message |
| `WARNING` | 1 | Requires attention |
| `ERROR` | 2 | Operation failed |
| `CRITICAL` | 3 | Subsystem degraded |
| `EMERGENCY` | 4 | Platform-level failure |

### AlertSource

`RUNTIME`, `PIPELINE`, `MONITORING`, `BROKER`, `OMS`, `EXECUTION`,
`PORTFOLIO`, `RISK`, `CONFIGURATION`, `LOGGING`, `PAPER_TRADING`,
`BACKTESTING`, `SYSTEM`

### AlertStatus

| Status | Description |
|---|---|
| `NEW` | Unacknowledged |
| `ACKNOWLEDGED` | Seen by operator |
| `RESOLVED` | Condition cleared |
| `SUPPRESSED` | Suppressed by rules |
| `ESCALATED` | Repeated matches triggered escalation |

## Rule Engine

The `AlertRuleEngine` provides:

| Feature | Description |
|---|---|
| **Condition evaluation** | `Callable[[Alert], bool]` per rule |
| **Threshold alerts** | Evaluate numeric values against warning/critical thresholds |
| **State-change alerts** | Fire on state transitions with old/new state tracking |
| **Duplicate suppression** | Same rule+title+source suppressed within cache |
| **Cooldown** | Configurable cooldown period per rule (default 300s) |
| **Rate limiting** | Max 10 evaluations per 60 seconds per rule |
| **Escalation** | Repeated matches increment escalation count |
| **Source filtering** | Rules can restrict to specific alert sources |
| **Enable/disable** | Rules can be toggled at runtime |

## Notification Channels

| Channel | Implementation | Status |
|---|---|---|
| **Console** | `print()` to stdout | Production-ready |
| **Email** | SMTP stub (raises DispatchError) | Stub |
| **Telegram** | Bot API stub (raises DispatchError) | Stub |
| **Slack** | Webhook stub (raises DispatchError) | Stub |
| **Webhook** | HTTP POST stub (raises DispatchError) | Stub |

### Adding a New Channel

```python
from titan.alerting import (
    NotificationChannel,
    NotificationResult,
    ChannelType,
    Alert,
)

class MyCustomChannel(NotificationChannel):
    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.WEBHOOK  # Or use a custom type

    def send(self, alert: Alert) -> NotificationResult:
        try:
            # Send the alert to your custom target
            return NotificationResult.SUCCESS
        except Exception as exc:
            raise AlertingDispatchError(f"Custom channel failed: {exc}")
```

## History

The `AlertHistory` provides:

- **Store** alerts with notification attempts and rule results
- **Retrieve** by alert ID
- **Acknowledge / Resolve** — lifecycle management with operator tracking
- **Query** by source, level, or active status
- **Report** — `generate_report()` with counts, breakdowns, and warnings

## Channels from Monitoring

The `fire_from_monitoring()` method bridges the monitoring and
alerting frameworks:

```python
manager.fire_from_monitoring(
    level="critical",      # Maps to AlertLevel
    source="runtime",      # Maps to AlertSource
    title="Runtime Error",
    message="Stream connection lost",
    metric_name="stream.connected",
    metric_value=0.0,
)
```

## Configuration

The `ChannelConfig` dataclass controls per-channel behavior:

```python
@dataclass(frozen=True, slots=True)
class ChannelConfig:
    channel_type: ChannelType
    enabled: bool = True
    min_level: AlertLevel = AlertLevel.WARNING
    config: Mapping[str, Any] = field(default_factory=dict)
```

## Quality

- **Frozen dataclasses** — All models immutable
- **Strict typing** — Full type hints throughout
- **Dependency injection** — Constructor injection for testability
- **Thread-safe** — All mutable state protected by `Lock`
- **Retry failed notifications** — Up to 3 retries per channel
- **Graceful degradation** — Channel failures don't affect others
- **Ruff clean** — Zero linting errors
- **Black clean** — Zero formatting errors
- **MyPy clean** — Zero type errors

## Rules

1. No trading logic
2. No execution logic
3. No market analysis
4. Alerting only
5. No subsystem may send notifications directly
6. Every notification must pass through `AlertManager`

## TUI Integration

The Monitoring & Alerting screen (F6) provides real-time visualization of alerting state:

- **AlertSummaryWidget**: Displays alert counts by status from `AlertManager.generate_report()`
- **ActiveAlertsWidget**: Displays active alerts from `AlertManager.get_active_alerts()`
- **AlertHistoryWidget**: Displays alert history from `AlertManager.history.all_entries()`
- **MonitoringEventsWidget**: Displays alert warnings from `AlertReport.warnings`

Data is read-only. The TUI reads `AlertManager.generate_report()` and `AlertManager.get_active_alerts()` every second via `build_monitoring_state()` in `titan/tui/layout.py`.
