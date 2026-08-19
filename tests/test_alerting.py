from __future__ import annotations

import pytest

from titan.alerting.channels import (
    ChannelConfig,
    ChannelManager,
    ConsoleChannel,
    EmailChannel,
    SlackChannel,
    TelegramChannel,
    WebhookChannel,
)
from titan.alerting.engine import AlertEngine
from titan.alerting.exceptions import (
    AlertingChannelError,
    AlertingDispatchError,
    AlertingEngineError,
    AlertingError,
    AlertingHistoryError,
    AlertingInputError,
    AlertingRuleError,
)
from titan.alerting.history import AlertHistory
from titan.alerting.manager import AlertManager
from titan.alerting.models import (
    Alert,
    AlertHistoryEntry,
    AlertLevel,
    AlertReport,
    AlertRule,
    AlertSource,
    AlertStatus,
    ChannelType,
    NotificationAttempt,
    NotificationResult,
    level_rank,
)
from titan.alerting.rules import AlertRuleEngine

# ── Fixtures ──


def make_alert(
    alert_id: str = "alert:1",
    level: AlertLevel = AlertLevel.WARNING,
    source: AlertSource = AlertSource.MONITORING,
    title: str = "Test Alert",
    message: str = "This is a test alert",
    rule_name: str = "",
) -> Alert:
    return Alert(
        alert_id=alert_id,
        level=level,
        source=source,
        title=title,
        message=message,
        rule_name=rule_name,
    )


def always_match_rule(
    name: str = "always_match",
    level: AlertLevel = AlertLevel.WARNING,
    source: AlertSource | None = None,
) -> AlertRule:
    return AlertRule(
        name=name,
        condition=lambda _: True,
        level=level,
        source=source,
    )


def never_match_rule(
    name: str = "never_match",
    level: AlertLevel = AlertLevel.WARNING,
) -> AlertRule:
    return AlertRule(
        name=name,
        condition=lambda _: False,
        level=level,
    )


# ── Model Tests ──


class TestAlertLevel:
    def test_enum_values(self) -> None:
        assert AlertLevel.INFO.value == "info"
        assert AlertLevel.WARNING.value == "warning"
        assert AlertLevel.ERROR.value == "error"
        assert AlertLevel.CRITICAL.value == "critical"
        assert AlertLevel.EMERGENCY.value == "emergency"

    def test_level_rank(self) -> None:
        assert level_rank(AlertLevel.INFO) == 0
        assert level_rank(AlertLevel.WARNING) == 1
        assert level_rank(AlertLevel.ERROR) == 2
        assert level_rank(AlertLevel.CRITICAL) == 3
        assert level_rank(AlertLevel.EMERGENCY) == 4


class TestAlertSource:
    def test_enum_values(self) -> None:
        assert AlertSource.RUNTIME.value == "runtime"
        assert AlertSource.BROKER.value == "broker"
        assert AlertSource.RISK.value == "risk"


class TestAlertStatus:
    def test_enum_values(self) -> None:
        assert AlertStatus.NEW.value == "new"
        assert AlertStatus.ACKNOWLEDGED.value == "acknowledged"
        assert AlertStatus.RESOLVED.value == "resolved"
        assert AlertStatus.ESCALATED.value == "escalated"


class TestAlert:
    def test_defaults(self) -> None:
        alert = Alert(
            alert_id="a1",
            level=AlertLevel.WARNING,
            source=AlertSource.MONITORING,
            title="Test",
            message="Message",
        )
        assert alert.status == AlertStatus.NEW
        assert alert.escalation_count == 0
        assert alert.rule_name == ""
        assert alert.metadata == {}

    def test_frozen(self) -> None:
        alert = make_alert()
        with pytest.raises(AttributeError):
            alert.level = AlertLevel.INFO  # type: ignore[misc]

    def test_with_all_fields(self) -> None:
        alert = Alert(
            alert_id="a2",
            level=AlertLevel.CRITICAL,
            source=AlertSource.BROKER,
            title="Broker Down",
            message="Connection lost",
            status=AlertStatus.ESCALATED,
            escalation_count=2,
            rule_name="broker_health",
            metadata={"latency_ms": 5000},
            tags=("urgent", "broker"),
        )
        assert alert.level == AlertLevel.CRITICAL
        assert alert.escalation_count == 2
        assert "urgent" in alert.tags


class TestAlertRule:
    def test_defaults(self) -> None:
        rule = AlertRule(
            name="test_rule",
            condition=lambda a: True,
        )
        assert rule.level == AlertLevel.WARNING
        assert rule.source is None
        assert rule.cooldown_seconds == 300.0
        assert rule.enabled

    def test_frozen(self) -> None:
        rule = always_match_rule()
        with pytest.raises(AttributeError):
            rule.name = "new_name"  # type: ignore[misc]


class TestAlertReport:
    def test_defaults(self) -> None:
        report = AlertReport()
        assert report.total_alerts == 0
        assert report.warnings == ()


class TestAlertHistoryEntry:
    def test_defaults(self) -> None:
        entry = AlertHistoryEntry(alert=make_alert())
        assert entry.notifications == ()
        assert entry.rule_results == ()


class TestNotificationAttempt:
    def test_defaults(self) -> None:
        attempt = NotificationAttempt(channel=ChannelType.CONSOLE)
        assert attempt.result == NotificationResult.SUCCESS
        assert attempt.retry_count == 0


# ── Exception Tests ──


class TestExceptions:
    def test_hierarchy(self) -> None:
        assert issubclass(AlertingInputError, AlertingError)
        assert issubclass(AlertingRuleError, AlertingError)
        assert issubclass(AlertingEngineError, AlertingError)
        assert issubclass(AlertingChannelError, AlertingError)
        assert issubclass(AlertingDispatchError, AlertingError)
        assert issubclass(AlertingHistoryError, AlertingError)
        assert issubclass(AlertingInputError, ValueError)

    def test_raise(self) -> None:
        with pytest.raises(AlertingError):
            raise AlertingRuleError("rule failed")
        with pytest.raises(AlertingError):
            raise AlertingDispatchError("dispatch failed")


# ── AlertRuleEngine Tests ──


class TestAlertRuleEngine:
    def test_register_rule(self) -> None:
        engine = AlertRuleEngine()
        engine.register_rule(always_match_rule())
        assert "always_match" in engine.rule_names()

    def test_register_duplicate(self) -> None:
        engine = AlertRuleEngine()
        engine.register_rule(always_match_rule())
        with pytest.raises(AlertingRuleError):
            engine.register_rule(always_match_rule())

    def test_unregister_rule(self) -> None:
        engine = AlertRuleEngine()
        engine.register_rule(always_match_rule())
        engine.unregister_rule("always_match")
        assert engine.rule_names() == ()

    def test_unregister_missing(self) -> None:
        engine = AlertRuleEngine()
        with pytest.raises(AlertingRuleError):
            engine.unregister_rule("nonexistent")

    def test_evaluate_match(self) -> None:
        engine = AlertRuleEngine()
        engine.register_rule(always_match_rule())
        alert = make_alert(rule_name="always_match")
        result = engine.evaluate(alert)
        assert result.matched
        assert not result.suppressed

    def test_evaluate_no_match(self) -> None:
        engine = AlertRuleEngine()
        engine.register_rule(never_match_rule())
        alert = make_alert(rule_name="never_match")
        result = engine.evaluate(alert)
        assert not result.matched

    def test_evaluate_rule_not_found(self) -> None:
        engine = AlertRuleEngine()
        alert = make_alert(rule_name="nonexistent")
        result = engine.evaluate(alert)
        assert not result.matched
        assert result.reason == "Rule not found"

    def test_source_filter_match(self) -> None:
        engine = AlertRuleEngine()
        engine.register_rule(
            AlertRule(
                name="broker_rule",
                condition=lambda a: True,
                source=AlertSource.BROKER,
            )
        )
        alert = make_alert(rule_name="broker_rule", source=AlertSource.BROKER)
        result = engine.evaluate(alert)
        assert result.matched

    def test_source_filter_mismatch(self) -> None:
        engine = AlertRuleEngine()
        engine.register_rule(
            AlertRule(
                name="broker_rule",
                condition=lambda a: True,
                source=AlertSource.BROKER,
            )
        )
        alert = make_alert(rule_name="broker_rule", source=AlertSource.MONITORING)
        result = engine.evaluate(alert)
        assert not result.matched
        assert "Source mismatch" in result.reason

    def test_cooldown(self) -> None:
        engine = AlertRuleEngine()
        engine.register_rule(
            AlertRule(
                name="cooldown_test",
                condition=lambda a: True,
                cooldown_seconds=3600.0,
            )
        )
        alert = make_alert(rule_name="cooldown_test")
        first = engine.evaluate(alert)
        assert first.matched

        second = engine.evaluate(alert)
        assert second.suppressed
        assert "Cooldown" in second.reason

    def test_duplicate_suppression(self) -> None:
        engine = AlertRuleEngine()
        engine.register_rule(
            AlertRule(
                name="dedup_test",
                condition=lambda a: True,
                suppress_duplicates=True,
            )
        )
        alert = make_alert(rule_name="dedup_test", title="Same Title")
        first = engine.evaluate(alert)
        assert first.matched

        second = engine.evaluate(alert)
        assert second.suppressed

    def test_disabled_rule(self) -> None:
        engine = AlertRuleEngine()
        rule = AlertRule(
            name="disabled",
            condition=lambda a: True,
            enabled=False,
        )
        engine.register_rule(rule)
        alert = make_alert(rule_name="disabled")
        result = engine.evaluate(alert)
        assert result.suppressed
        assert "disabled" in result.reason

    def test_enable_disable_rule(self) -> None:
        engine = AlertRuleEngine()
        engine.register_rule(always_match_rule("toggle"))
        engine.disable_rule("toggle")
        alert = make_alert(rule_name="toggle")
        assert engine.evaluate(alert).suppressed
        engine.enable_rule("toggle")
        assert engine.evaluate(alert).matched

    def test_evaluate_all(self) -> None:
        engine = AlertRuleEngine()
        engine.register_rule(always_match_rule("match_1"))
        engine.register_rule(always_match_rule("match_2"))
        alert = make_alert(rule_name="match_1")
        results = engine.evaluate_all(alert)
        assert len(results) == 2

    def test_evaluate_threshold_critical(self) -> None:
        engine = AlertRuleEngine()
        engine.register_rule(always_match_rule("threshold_rule"))
        result = engine.evaluate_threshold(
            name="threshold_rule",
            value=95.0,
            warning_threshold=80.0,
            critical_threshold=90.0,
            source=AlertSource.MONITORING,
            title="High CPU",
            message_template="CPU at {value}%",
        )
        assert result is not None
        assert result.matched
        assert result.alert is not None
        assert result.alert.level == AlertLevel.CRITICAL

    def test_evaluate_threshold_warning(self) -> None:
        engine = AlertRuleEngine()
        engine.register_rule(always_match_rule("threshold_rule"))
        result = engine.evaluate_threshold(
            name="threshold_rule",
            value=85.0,
            warning_threshold=80.0,
            critical_threshold=90.0,
            source=AlertSource.MONITORING,
            title="High CPU",
            message_template="CPU at {value}%",
        )
        assert result is not None
        assert result.matched
        assert result.alert is not None
        assert result.alert.level == AlertLevel.WARNING

    def test_evaluate_threshold_no_alert(self) -> None:
        engine = AlertRuleEngine()
        engine.register_rule(always_match_rule("threshold_rule"))
        result = engine.evaluate_threshold(
            name="threshold_rule",
            value=50.0,
            warning_threshold=80.0,
            critical_threshold=90.0,
            source=AlertSource.MONITORING,
            title="High CPU",
            message_template="CPU at {value}%",
        )
        assert result is None

    def test_evaluate_state_change(self) -> None:
        engine = AlertRuleEngine()
        engine.register_rule(always_match_rule("state_rule"))
        result = engine.evaluate_state_change(
            name="state_rule",
            key="broker:connection",
            new_state="connected",
            source=AlertSource.BROKER,
            title="Broker Connected",
            message="Broker connection established",
        )
        assert result is None

        result = engine.evaluate_state_change(
            name="state_rule",
            key="broker:connection",
            new_state="disconnected",
            source=AlertSource.BROKER,
            title="Broker Disconnected",
            message="Broker connection lost",
        )
        assert result is not None
        assert result.matched

    def test_evaluate_state_change_no_change(self) -> None:
        engine = AlertRuleEngine()
        engine.register_rule(always_match_rule("state_rule"))
        engine.evaluate_state_change(
            name="state_rule",
            key="test",
            new_state="on",
            source=AlertSource.SYSTEM,
            title="State",
            message="State changed",
        )
        result = engine.evaluate_state_change(
            name="state_rule",
            key="test",
            new_state="on",
            source=AlertSource.SYSTEM,
            title="State",
            message="State changed",
        )
        assert result is None

    def test_rate_limit(self) -> None:
        engine = AlertRuleEngine()
        engine.register_rule(
            AlertRule(
                name="rate_limit_test",
                condition=lambda a: True,
                cooldown_seconds=0.0,
            )
        )
        alert = make_alert(rule_name="rate_limit_test")
        for _ in range(10):
            engine.evaluate(alert)
        result = engine.evaluate(alert)
        assert result.suppressed
        assert "Rate limit" in result.reason

    def test_reset(self) -> None:
        engine = AlertRuleEngine()
        engine.register_rule(always_match_rule())
        engine.reset()
        assert engine.rule_names() == ()

    def test_escaltion(self) -> None:
        engine = AlertRuleEngine()
        engine.register_rule(
            AlertRule(
                name="escalation_test",
                condition=lambda a: True,
                max_escalations=1,
            )
        )
        alert = make_alert(rule_name="escalation_test")
        result = engine.evaluate(alert)
        assert not result.escalated

    def test_condition_exception(self) -> None:
        engine = AlertRuleEngine()

        def failing_condition(a: Alert) -> bool:
            msg = "condition error"
            raise RuntimeError(msg)

        engine.register_rule(AlertRule(name="failing", condition=failing_condition))
        alert = make_alert(rule_name="failing")
        with pytest.raises(AlertingRuleError):
            engine.evaluate(alert)


# ── Channel Tests ──


class TestConsoleChannel:
    def test_send(self) -> None:
        channel = ConsoleChannel()
        alert = make_alert()
        result = channel.send(alert)
        assert result == NotificationResult.SUCCESS

    def test_channel_type(self) -> None:
        channel = ConsoleChannel()
        assert channel.channel_type == ChannelType.CONSOLE


class TestEmailChannel:
    def test_send_graceful_failure(self) -> None:
        channel = EmailChannel()
        alert = make_alert()
        with pytest.raises(AlertingDispatchError):
            channel.send(alert)

    def test_channel_type(self) -> None:
        channel = EmailChannel()
        assert channel.channel_type == ChannelType.EMAIL


class TestTelegramChannel:
    def test_send_graceful_failure(self) -> None:
        channel = TelegramChannel()
        alert = make_alert()
        with pytest.raises(AlertingDispatchError):
            channel.send(alert)

    def test_channel_type(self) -> None:
        channel = TelegramChannel()
        assert channel.channel_type == ChannelType.TELEGRAM


class TestSlackChannel:
    def test_send_graceful_failure(self) -> None:
        channel = SlackChannel()
        alert = make_alert()
        with pytest.raises(AlertingDispatchError):
            channel.send(alert)

    def test_channel_type(self) -> None:
        channel = SlackChannel()
        assert channel.channel_type == ChannelType.SLACK


class TestWebhookChannel:
    def test_send_graceful_failure(self) -> None:
        channel = WebhookChannel()
        alert = make_alert()
        with pytest.raises(AlertingDispatchError):
            channel.send(alert)

    def test_channel_type(self) -> None:
        channel = WebhookChannel()
        assert channel.channel_type == ChannelType.WEBHOOK


# ── ChannelManager Tests ──


class TestChannelManager:
    def test_register_channel(self) -> None:
        mgr = ChannelManager()
        mgr.register_channel(ConsoleChannel())
        assert ChannelType.CONSOLE in mgr.registered_channels()

    def test_register_duplicate(self) -> None:
        mgr = ChannelManager()
        mgr.register_channel(ConsoleChannel())
        with pytest.raises(AlertingChannelError):
            mgr.register_channel(ConsoleChannel())

    def test_unregister_channel(self) -> None:
        mgr = ChannelManager()
        mgr.register_channel(ConsoleChannel())
        mgr.unregister_channel(ChannelType.CONSOLE)
        assert mgr.registered_channels() == ()

    def test_unregister_missing(self) -> None:
        mgr = ChannelManager()
        with pytest.raises(AlertingChannelError):
            mgr.unregister_channel(ChannelType.CONSOLE)

    def test_get_channel(self) -> None:
        mgr = ChannelManager()
        channel = ConsoleChannel()
        mgr.register_channel(channel)
        assert mgr.get_channel(ChannelType.CONSOLE) is channel

    def test_get_channel_missing(self) -> None:
        mgr = ChannelManager()
        assert mgr.get_channel(ChannelType.EMAIL) is None

    def test_dispatch(self) -> None:
        mgr = ChannelManager()
        mgr.register_channel(
            ConsoleChannel(),
            ChannelConfig(
                channel_type=ChannelType.CONSOLE,
                min_level=AlertLevel.INFO,
            ),
        )
        alert = make_alert(level=AlertLevel.WARNING)
        attempts = mgr.dispatch(alert)
        assert len(attempts) == 1
        assert attempts[0].result == NotificationResult.SUCCESS

    def test_dispatch_level_filter(self) -> None:
        mgr = ChannelManager()
        mgr.register_channel(
            ConsoleChannel(),
            ChannelConfig(
                channel_type=ChannelType.CONSOLE,
                min_level=AlertLevel.ERROR,
            ),
        )
        alert = make_alert(level=AlertLevel.INFO)
        attempts = mgr.dispatch(alert)
        assert len(attempts) == 0

    def test_dispatch_disabled_channel(self) -> None:
        mgr = ChannelManager()
        mgr.register_channel(
            ConsoleChannel(),
            ChannelConfig(
                channel_type=ChannelType.CONSOLE,
                enabled=False,
            ),
        )
        alert = make_alert()
        attempts = mgr.dispatch(alert)
        assert len(attempts) == 0

    def test_dispatch_failure(self) -> None:
        mgr = ChannelManager()
        mgr.register_channel(
            EmailChannel(),
            ChannelConfig(
                channel_type=ChannelType.EMAIL,
                min_level=AlertLevel.INFO,
            ),
        )
        alert = make_alert(level=AlertLevel.WARNING)
        attempts = mgr.dispatch(alert)
        assert len(attempts) == 1
        assert attempts[0].result == NotificationResult.FAILED

    def test_reset(self) -> None:
        mgr = ChannelManager()
        mgr.register_channel(ConsoleChannel())
        mgr.reset()
        assert mgr.registered_channels() == ()


# ── AlertHistory Tests ──


class TestAlertHistory:
    def test_store_and_get(self) -> None:
        history = AlertHistory()
        alert = make_alert()
        history.store(alert)
        retrieved = history.get(alert.alert_id)
        assert retrieved is not None
        assert retrieved.title == "Test Alert"

    def test_get_missing(self) -> None:
        history = AlertHistory()
        assert history.get("nonexistent") is None

    def test_get_entry(self) -> None:
        history = AlertHistory()
        alert = make_alert()
        history.store(alert)
        entry = history.get_entry(alert.alert_id)
        assert entry is not None
        assert entry.alert.title == "Test Alert"

    def test_acknowledge(self) -> None:
        history = AlertHistory()
        alert = make_alert()
        history.store(alert)
        history.acknowledge(alert.alert_id, "operator")
        updated = history.get(alert.alert_id)
        assert updated is not None
        assert updated.status == AlertStatus.ACKNOWLEDGED
        assert updated.acknowledged_by == "operator"

    def test_acknowledge_missing(self) -> None:
        history = AlertHistory()
        with pytest.raises(AlertingHistoryError):
            history.acknowledge("nonexistent")

    def test_resolve(self) -> None:
        history = AlertHistory()
        alert = make_alert()
        history.store(alert)
        history.resolve(alert.alert_id, "system")
        updated = history.get(alert.alert_id)
        assert updated is not None
        assert updated.status == AlertStatus.RESOLVED
        assert updated.resolved_by == "system"

    def test_resolve_missing(self) -> None:
        history = AlertHistory()
        with pytest.raises(AlertingHistoryError):
            history.resolve("nonexistent")

    def test_get_active(self) -> None:
        history = AlertHistory()
        history.store(make_alert("a1"))
        history.store(make_alert("a2"))
        history.acknowledge("a2")
        history.store(
            Alert(
                alert_id="a3",
                level=AlertLevel.INFO,
                source=AlertSource.SYSTEM,
                title="Resolved",
                message="Done",
                status=AlertStatus.RESOLVED,
            )
        )
        active = history.get_active()
        assert len(active) == 2

    def test_get_by_source(self) -> None:
        history = AlertHistory()
        history.store(make_alert("a1", source=AlertSource.BROKER))
        history.store(make_alert("a2", source=AlertSource.RISK))
        broker_alerts = history.get_by_source(AlertSource.BROKER)
        assert len(broker_alerts) == 1

    def test_get_by_level(self) -> None:
        history = AlertHistory()
        history.store(make_alert("a1", level=AlertLevel.CRITICAL))
        history.store(make_alert("a2", level=AlertLevel.INFO))
        critical = history.get_by_level(AlertLevel.CRITICAL)
        assert len(critical) == 1

    def test_count(self) -> None:
        history = AlertHistory()
        assert history.count() == 0
        history.store(make_alert())
        assert history.count() == 1

    def test_generate_report(self) -> None:
        history = AlertHistory()
        report = history.generate_report()
        assert isinstance(report, AlertReport)
        assert report.total_alerts == 0

        history.store(make_alert("a1", level=AlertLevel.CRITICAL))
        report = history.generate_report()
        assert report.total_alerts == 1
        assert report.critical_alerts == 1

    def test_reset(self) -> None:
        history = AlertHistory()
        history.store(make_alert())
        history.reset()
        assert history.count() == 0


# ── AlertEngine Tests ──


class TestAlertEngine:
    def test_fire_without_rules(self) -> None:
        engine = AlertEngine()
        alert = engine.fire(
            level=AlertLevel.WARNING,
            source=AlertSource.MONITORING,
            title="Test",
            message="Test message",
        )
        assert alert.title == "Test"

    def test_fire_with_matching_rule(self) -> None:
        engine = AlertEngine()
        engine.rules.register_rule(always_match_rule("test_rule"))
        alert = engine.fire(
            level=AlertLevel.WARNING,
            source=AlertSource.MONITORING,
            title="Test",
            message="Test message",
            rule_name="test_rule",
        )
        assert alert is not None

    def test_fire_with_console_channel(self) -> None:
        engine = AlertEngine()
        engine.channels.register_channel(
            ConsoleChannel(),
            ChannelConfig(
                channel_type=ChannelType.CONSOLE,
                min_level=AlertLevel.INFO,
            ),
        )
        alert = engine.fire(
            level=AlertLevel.WARNING,
            source=AlertSource.MONITORING,
            title="Console Test",
            message="This should print to console",
        )
        assert alert.title == "Console Test"

    def test_fire_from_monitoring(self) -> None:
        engine = AlertEngine()
        alert = engine.fire_from_monitoring(
            level="warning",
            source="broker",
            title="Broker Latency",
            message="High latency detected",
            metric_name="broker.latency",
            metric_value=500.0,
        )
        assert alert.source == AlertSource.BROKER
        assert alert.level == AlertLevel.WARNING
        assert alert.metadata.get("metric_name") == "broker.latency"

    def test_acknowledge(self) -> None:
        engine = AlertEngine()
        alert = engine.fire(
            level=AlertLevel.WARNING,
            source=AlertSource.MONITORING,
            title="Test",
            message="Test",
        )
        engine.acknowledge(alert.alert_id, "operator")
        retrieved = engine.get_alert(alert.alert_id)
        assert retrieved is not None
        assert retrieved.status == AlertStatus.ACKNOWLEDGED

    def test_resolve(self) -> None:
        engine = AlertEngine()
        alert = engine.fire(
            level=AlertLevel.WARNING,
            source=AlertSource.MONITORING,
            title="Test",
            message="Test",
        )
        engine.resolve(alert.alert_id, "system")
        retrieved = engine.get_alert(alert.alert_id)
        assert retrieved is not None
        assert retrieved.status == AlertStatus.RESOLVED

    def test_get_active_alerts(self) -> None:
        engine = AlertEngine()
        engine.fire(
            level=AlertLevel.WARNING,
            source=AlertSource.MONITORING,
            title="Active 1",
            message="Test",
        )
        active = engine.get_active_alerts()
        assert len(active) == 1

    def test_get_alerts_by_source(self) -> None:
        engine = AlertEngine()
        engine.fire(
            level=AlertLevel.WARNING,
            source=AlertSource.BROKER,
            title="Broker Alert",
            message="Test",
        )
        alerts = engine.get_alerts_by_source(AlertSource.BROKER)
        assert len(alerts) == 1

    def test_get_alerts_by_level(self) -> None:
        engine = AlertEngine()
        engine.fire(
            level=AlertLevel.CRITICAL,
            source=AlertSource.MONITORING,
            title="Critical Alert",
            message="Test",
        )
        alerts = engine.get_alerts_by_level(AlertLevel.CRITICAL)
        assert len(alerts) == 1

    def test_generate_report(self) -> None:
        engine = AlertEngine()
        engine.fire(
            level=AlertLevel.CRITICAL,
            source=AlertSource.MONITORING,
            title="Critical",
            message="Test",
        )
        report = engine.generate_report()
        assert isinstance(report, AlertReport)
        assert report.total_alerts >= 1

    def test_reset(self) -> None:
        engine = AlertEngine()
        engine.fire(
            level=AlertLevel.WARNING,
            source=AlertSource.MONITORING,
            title="Test",
            message="Test",
        )
        engine.reset()
        assert engine.get_active_alerts() == ()


# ── AlertManager Tests ──


class TestAlertManager:
    def test_initialization(self) -> None:
        mgr = AlertManager()
        assert mgr.engine is not None
        assert mgr.rules is not None
        assert mgr.channels is not None
        assert mgr.history is not None

    def test_default_console_channel(self) -> None:
        mgr = AlertManager()
        assert ChannelType.CONSOLE in mgr.channels.registered_channels()

    def test_register_rule(self) -> None:
        mgr = AlertManager()
        mgr.register_rule(always_match_rule())
        assert "always_match" in mgr.rules.rule_names()

    def test_register_channel(self) -> None:
        mgr = AlertManager()
        mgr.register_channel(
            EmailChannel(),
            ChannelConfig(channel_type=ChannelType.EMAIL),
        )
        assert ChannelType.EMAIL in mgr.channels.registered_channels()

    def test_fire(self) -> None:
        mgr = AlertManager()
        alert = mgr.fire(
            level=AlertLevel.WARNING,
            source=AlertSource.MONITORING,
            title="Manager Test",
            message="Test via manager",
        )
        assert alert.title == "Manager Test"

    def test_fire_from_monitoring(self) -> None:
        mgr = AlertManager()
        alert = mgr.fire_from_monitoring(
            level="critical",
            source="runtime",
            title="Runtime Error",
            message="Runtime failure",
        )
        assert alert.level == AlertLevel.CRITICAL
        assert alert.source == AlertSource.RUNTIME

    def test_acknowledge(self) -> None:
        mgr = AlertManager()
        alert = mgr.fire(
            level=AlertLevel.WARNING,
            source=AlertSource.MONITORING,
            title="Ack Test",
            message="Test",
        )
        mgr.acknowledge(alert.alert_id, "admin")
        retrieved = mgr.get_alert(alert.alert_id)
        assert retrieved is not None
        assert retrieved.status == AlertStatus.ACKNOWLEDGED

    def test_resolve(self) -> None:
        mgr = AlertManager()
        alert = mgr.fire(
            level=AlertLevel.WARNING,
            source=AlertSource.MONITORING,
            title="Resolve Test",
            message="Test",
        )
        mgr.resolve(alert.alert_id, "admin")
        retrieved = mgr.get_alert(alert.alert_id)
        assert retrieved is not None
        assert retrieved.status == AlertStatus.RESOLVED

    def test_get_active_alerts(self) -> None:
        mgr = AlertManager()
        mgr.fire(
            level=AlertLevel.WARNING,
            source=AlertSource.MONITORING,
            title="Active",
            message="Test",
        )
        active = mgr.get_active_alerts()
        assert len(active) == 1

    def test_generate_report(self) -> None:
        mgr = AlertManager()
        mgr.fire(
            level=AlertLevel.CRITICAL,
            source=AlertSource.BROKER,
            title="Critical",
            message="Test",
        )
        report = mgr.generate_report()
        assert isinstance(report, AlertReport)
        assert report.total_alerts >= 1

    def test_reset(self) -> None:
        mgr = AlertManager()
        mgr.fire(
            level=AlertLevel.WARNING,
            source=AlertSource.MONITORING,
            title="Reset Test",
            message="Test",
        )
        mgr.reset()
        assert mgr.get_active_alerts() == ()
        assert ChannelType.CONSOLE in mgr.channels.registered_channels()


# ── Frozen / Serialization Tests ──


class TestFrozenInstances:
    def test_alert_frozen(self) -> None:
        alert = make_alert()
        with pytest.raises(AttributeError):
            alert.title = "changed"  # type: ignore[misc]

    def test_rule_frozen(self) -> None:
        rule = always_match_rule()
        with pytest.raises(AttributeError):
            rule.name = "changed"  # type: ignore[misc]

    def test_report_frozen(self) -> None:
        report = AlertReport()
        with pytest.raises(AttributeError):
            report.total_alerts = 5  # type: ignore[misc]


# ── Dependency Injection Tests ──


class TestDependencyInjection:
    def test_engine_rules_injection(self) -> None:
        rules = AlertRuleEngine()
        engine = AlertEngine(_rules=rules)
        assert engine._rules is rules

    def test_engine_channels_injection(self) -> None:
        channels = ChannelManager()
        engine = AlertEngine(_channels=channels)
        assert engine._channels is channels

    def test_engine_history_injection(self) -> None:
        history = AlertHistory()
        engine = AlertEngine(_history=history)
        assert engine._history is history

    def test_alert_manager_engine_injection(self) -> None:
        engine = AlertEngine()
        mgr = AlertManager(_engine=engine)
        assert mgr._engine is engine
