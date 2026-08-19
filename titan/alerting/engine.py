from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from typing import Any

from titan.alerting.channels import ChannelManager
from titan.alerting.history import AlertHistory
from titan.alerting.models import (
    Alert,
    AlertLevel,
    AlertReport,
    AlertSource,
    AlertStatus,
)
from titan.alerting.rules import AlertRuleEngine


@dataclass(slots=True)
class AlertEngine:
    _rules: AlertRuleEngine = field(default_factory=AlertRuleEngine)
    _channels: ChannelManager = field(default_factory=ChannelManager)
    _history: AlertHistory = field(default_factory=AlertHistory)
    _alert_id_counter: int = 0
    _lock: Lock = field(default_factory=Lock, init=False)

    @property
    def rules(self) -> AlertRuleEngine:
        return self._rules

    @property
    def channels(self) -> ChannelManager:
        return self._channels

    @property
    def history(self) -> AlertHistory:
        return self._history

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
        alert = self._create_alert(
            level=level,
            source=source,
            title=title,
            message=message,
            rule_name=rule_name,
            metadata=metadata,
            tags=tags,
        )

        rule_results = self._rules.evaluate_all(alert)

        matched = [r for r in rule_results if r.matched]
        suppressed = [r for r in rule_results if r.suppressed]

        should_suppress = bool(suppressed) and not bool(matched)

        final_status = AlertStatus.NEW
        if matched:
            for result in matched:
                if result.escalated:
                    final_status = AlertStatus.ESCALATED
        elif should_suppress:
            final_status = AlertStatus.SUPPRESSED

        alert = Alert(
            alert_id=alert.alert_id,
            level=alert.level,
            source=alert.source,
            title=alert.title,
            message=alert.message,
            timestamp=alert.timestamp,
            status=final_status,
            rule_name=alert.rule_name,
            metadata=alert.metadata,
            tags=alert.tags,
        )

        if not should_suppress and matched:
            notifications = self._channels.dispatch(alert)
        else:
            notifications = ()

        self._history.store(
            alert=alert,
            notifications=notifications,
            rule_results=rule_results,
        )

        return alert

    def fire_from_monitoring(
        self,
        level: str,
        source: str,
        title: str,
        message: str,
        metric_name: str = "",
        metric_value: float = 0.0,
    ) -> Alert:
        alert_level = AlertLevel.WARNING
        for lvl in AlertLevel:
            if lvl.value == level:
                alert_level = lvl
                break

        alert_source = AlertSource.MONITORING
        for src in AlertSource:
            if src.value == source:
                alert_source = src
                break

        metadata: dict[str, Any] = {}
        if metric_name:
            metadata["metric_name"] = metric_name
            metadata["metric_value"] = metric_value

        return self.fire(
            level=alert_level,
            source=alert_source,
            title=title,
            message=message,
            metadata=metadata,
        )

    def acknowledge(self, alert_id: str, acknowledged_by: str = "") -> None:
        self._history.acknowledge(alert_id, acknowledged_by)
        self._rules.acknowledge(alert_id)

    def resolve(self, alert_id: str, resolved_by: str = "") -> None:
        self._history.resolve(alert_id, resolved_by)

    def get_alert(self, alert_id: str) -> Alert | None:
        return self._history.get(alert_id)

    def get_active_alerts(self) -> tuple[Alert, ...]:
        return self._history.get_active()

    def get_alerts_by_source(self, source: AlertSource) -> tuple[Alert, ...]:
        return self._history.get_by_source(source)

    def get_alerts_by_level(self, level: AlertLevel) -> tuple[Alert, ...]:
        return self._history.get_by_level(level)

    def generate_report(self) -> AlertReport:
        return self._history.generate_report()

    def reset(self) -> None:
        self._rules.reset()
        self._channels.reset()
        self._history.reset()
        with self._lock:
            self._alert_id_counter = 0

    def _create_alert(
        self,
        level: AlertLevel,
        source: AlertSource,
        title: str,
        message: str,
        rule_name: str = "",
        metadata: Mapping[str, Any] | None = None,
        tags: tuple[str, ...] = (),
    ) -> Alert:
        with self._lock:
            self._alert_id_counter += 1
            alert_id = f"alert:{self._alert_id_counter}:{datetime.now(UTC).timestamp()}"

        return Alert(
            alert_id=alert_id,
            level=level,
            source=source,
            title=title,
            message=message,
            rule_name=rule_name,
            metadata=metadata or {},
            tags=tags,
        )
