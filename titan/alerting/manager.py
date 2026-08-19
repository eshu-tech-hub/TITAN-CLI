from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from typing import Any

from titan.alerting.channels import (
    ChannelConfig,
    ChannelManager,
    ConsoleChannel,
    NotificationChannel,
)
from titan.alerting.engine import AlertEngine
from titan.alerting.history import AlertHistory
from titan.alerting.models import (
    Alert,
    AlertLevel,
    AlertReport,
    AlertRule,
    AlertSource,
    ChannelType,
)
from titan.alerting.rules import AlertRuleEngine


@dataclass(slots=True)
class AlertManager:
    _engine: AlertEngine = field(default_factory=AlertEngine)
    _start_time: datetime = field(default_factory=lambda: datetime.now(UTC), init=False)
    _lock: Lock = field(default_factory=Lock, init=False)

    def __post_init__(self) -> None:
        self._register_default_channel()

    def _register_default_channel(self) -> None:
        self._engine.channels.register_channel(
            ConsoleChannel(),
            ChannelConfig(
                channel_type=ChannelType.CONSOLE,
                enabled=True,
                min_level=AlertLevel.INFO,
            ),
        )

    @property
    def engine(self) -> AlertEngine:
        return self._engine

    @property
    def rules(self) -> AlertRuleEngine:
        return self._engine.rules

    @property
    def channels(self) -> ChannelManager:
        return self._engine.channels

    @property
    def history(self) -> AlertHistory:
        return self._engine.history

    def register_rule(self, rule: AlertRule) -> None:
        self._engine.rules.register_rule(rule)

    def unregister_rule(self, name: str) -> None:
        self._engine.rules.unregister_rule(name)

    def register_channel(
        self,
        channel: NotificationChannel,
        config: ChannelConfig | None = None,
    ) -> None:
        self._engine.channels.register_channel(channel, config)

    def unregister_channel(self, channel_type: ChannelType) -> None:
        self._engine.channels.unregister_channel(channel_type)

    def fire(
        self,
        level: AlertLevel,
        source: AlertSource,
        title: str,
        message: str,
        rule_name: str = "",
        metadata: Mapping[str, Any] | None = None,
        tags: tuple[str, ...] = (),
    ) -> Alert:
        return self._engine.fire(
            level=level,
            source=source,
            title=title,
            message=message,
            rule_name=rule_name,
            metadata=metadata,
            tags=tags,
        )

    def fire_from_monitoring(
        self,
        level: str,
        source: str,
        title: str,
        message: str,
        metric_name: str = "",
        metric_value: float = 0.0,
    ) -> Alert:
        return self._engine.fire_from_monitoring(
            level=level,
            source=source,
            title=title,
            message=message,
            metric_name=metric_name,
            metric_value=metric_value,
        )

    def acknowledge(self, alert_id: str, acknowledged_by: str = "") -> None:
        self._engine.acknowledge(alert_id, acknowledged_by)

    def resolve(self, alert_id: str, resolved_by: str = "") -> None:
        self._engine.resolve(alert_id, resolved_by)

    def get_alert(self, alert_id: str) -> Alert | None:
        return self._engine.get_alert(alert_id)

    def get_active_alerts(self) -> tuple[Alert, ...]:
        return self._engine.get_active_alerts()

    def generate_report(self) -> AlertReport:
        return self._engine.generate_report()

    def reset(self) -> None:
        self._engine.reset()
        self._start_time = datetime.now(UTC)
        self._register_default_channel()
