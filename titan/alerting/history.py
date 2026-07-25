from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock

from titan.alerting.exceptions import AlertingHistoryError
from titan.alerting.models import (
    Alert,
    AlertHistoryEntry,
    AlertLevel,
    AlertReport,
    AlertRuleResult,
    AlertSource,
    AlertStatus,
    NotificationAttempt,
)


@dataclass(slots=True)
class AlertHistory:
    _entries: dict[str, AlertHistoryEntry] = field(default_factory=dict, init=False)
    _lock: Lock = field(default_factory=Lock, init=False)

    def store(
        self,
        alert: Alert,
        notifications: tuple[NotificationAttempt, ...] = (),
        rule_results: tuple[AlertRuleResult, ...] = (),
    ) -> AlertHistoryEntry:
        entry = AlertHistoryEntry(
            alert=alert,
            notifications=notifications,
            rule_results=rule_results,
        )
        with self._lock:
            self._entries[alert.alert_id] = entry
        return entry

    def get(self, alert_id: str) -> Alert | None:
        with self._lock:
            entry = self._entries.get(alert_id)
            if entry is None:
                return None
            return entry.alert

    def get_entry(self, alert_id: str) -> AlertHistoryEntry | None:
        with self._lock:
            return self._entries.get(alert_id)

    def acknowledge(self, alert_id: str, acknowledged_by: str = "") -> None:
        with self._lock:
            entry = self._entries.get(alert_id)
            if entry is None:
                raise AlertingHistoryError(f"Alert '{alert_id}' not found in history.")

            old_alert = entry.alert
            updated_alert = Alert(
                alert_id=old_alert.alert_id,
                level=old_alert.level,
                source=old_alert.source,
                title=old_alert.title,
                message=old_alert.message,
                timestamp=old_alert.timestamp,
                status=AlertStatus.ACKNOWLEDGED,
                acknowledged_at=datetime.now(timezone.utc),
                acknowledged_by=acknowledged_by,
                resolved_at=old_alert.resolved_at,
                resolved_by=old_alert.resolved_by,
                escalated_at=old_alert.escalated_at,
                escalation_count=old_alert.escalation_count,
                rule_name=old_alert.rule_name,
                metadata=old_alert.metadata,
                tags=old_alert.tags,
            )
            self._entries[alert_id] = AlertHistoryEntry(
                alert=updated_alert,
                notifications=entry.notifications,
                rule_results=entry.rule_results,
            )

    def resolve(self, alert_id: str, resolved_by: str = "") -> None:
        with self._lock:
            entry = self._entries.get(alert_id)
            if entry is None:
                raise AlertingHistoryError(f"Alert '{alert_id}' not found in history.")

            old_alert = entry.alert
            updated_alert = Alert(
                alert_id=old_alert.alert_id,
                level=old_alert.level,
                source=old_alert.source,
                title=old_alert.title,
                message=old_alert.message,
                timestamp=old_alert.timestamp,
                status=AlertStatus.RESOLVED,
                acknowledged_at=old_alert.acknowledged_at,
                acknowledged_by=old_alert.acknowledged_by,
                resolved_at=datetime.now(timezone.utc),
                resolved_by=resolved_by,
                escalated_at=old_alert.escalated_at,
                escalation_count=old_alert.escalation_count,
                rule_name=old_alert.rule_name,
                metadata=old_alert.metadata,
                tags=old_alert.tags,
            )
            self._entries[alert_id] = AlertHistoryEntry(
                alert=updated_alert,
                notifications=entry.notifications,
                rule_results=entry.rule_results,
            )

    def get_active(self) -> tuple[Alert, ...]:
        with self._lock:
            active: list[Alert] = []
            for entry in self._entries.values():
                if entry.alert.status in (
                    AlertStatus.NEW,
                    AlertStatus.ACKNOWLEDGED,
                    AlertStatus.ESCALATED,
                ):
                    active.append(entry.alert)
            return tuple(active)

    def get_by_source(self, source: AlertSource) -> tuple[Alert, ...]:
        with self._lock:
            return tuple(
                entry.alert
                for entry in self._entries.values()
                if entry.alert.source == source
            )

    def get_by_level(self, level: AlertLevel) -> tuple[Alert, ...]:
        with self._lock:
            return tuple(
                entry.alert
                for entry in self._entries.values()
                if entry.alert.level == level
            )

    def all_entries(self) -> tuple[AlertHistoryEntry, ...]:
        with self._lock:
            return tuple(self._entries.values())

    def all_alerts(self) -> tuple[Alert, ...]:
        with self._lock:
            return tuple(entry.alert for entry in self._entries.values())

    def count(self) -> int:
        with self._lock:
            return len(self._entries)

    def generate_report(self) -> AlertReport:
        with self._lock:
            alerts = [entry.alert for entry in self._entries.values()]
            total = len(alerts)
            active = sum(
                1
                for a in alerts
                if a.status
                in (AlertStatus.NEW, AlertStatus.ACKNOWLEDGED, AlertStatus.ESCALATED)
            )
            critical = sum(1 for a in alerts if a.level == AlertLevel.CRITICAL)
            acknowledged = sum(
                1 for a in alerts if a.status == AlertStatus.ACKNOWLEDGED
            )
            resolved = sum(1 for a in alerts if a.status == AlertStatus.RESOLVED)
            suppressed = sum(1 for a in alerts if a.status == AlertStatus.SUPPRESSED)
            escalated = sum(1 for a in alerts if a.status == AlertStatus.ESCALATED)

            by_source: dict[str, int] = {}
            by_level: dict[str, int] = {}
            for a in alerts:
                by_source[a.source.value] = by_source.get(a.source.value, 0) + 1
                by_level[a.level.value] = by_level.get(a.level.value, 0) + 1

            warnings_list: list[str] = []
            if critical > 0:
                warnings_list.append(f"{critical} critical alert(s) unresolved.")
            if escalated > 0:
                warnings_list.append(f"{escalated} alert(s) have been escalated.")

            return AlertReport(
                total_alerts=total,
                active_alerts=active,
                critical_alerts=critical,
                acknowledged_alerts=acknowledged,
                resolved_alerts=resolved,
                suppressed_alerts=suppressed,
                escalated_alerts=escalated,
                alerts_by_source=by_source,
                alerts_by_level=by_level,
                warnings=tuple(warnings_list),
                timestamp=datetime.now(timezone.utc),
            )

    def reset(self) -> None:
        with self._lock:
            self._entries.clear()
