from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock

from titan.alerting.exceptions import AlertingRuleError
from titan.alerting.models import (
    Alert,
    AlertLevel,
    AlertRule,
    AlertRuleResult,
    AlertSource,
)


@dataclass(slots=True)
class AlertRuleEngine:
    _rules: dict[str, AlertRule] = field(default_factory=dict, init=False)
    _cooldowns: dict[str, float] = field(default_factory=dict, init=False)
    _dedup_cache: set[str] = field(default_factory=set, init=False)
    _escalation_counts: dict[str, int] = field(default_factory=dict, init=False)
    _rate_limits: dict[str, list[float]] = field(default_factory=dict, init=False)
    _last_state: dict[str, str] = field(default_factory=dict, init=False)
    _lock: Lock = field(default_factory=Lock, init=False)

    def register_rule(self, rule: AlertRule) -> None:
        with self._lock:
            if rule.name in self._rules:
                raise AlertingRuleError(f"Rule '{rule.name}' is already registered.")
            self._rules[rule.name] = rule

    def unregister_rule(self, name: str) -> None:
        with self._lock:
            if name not in self._rules:
                raise AlertingRuleError(f"Rule '{name}' is not registered.")
            del self._rules[name]

    def enable_rule(self, name: str) -> None:
        with self._lock:
            if name not in self._rules:
                raise AlertingRuleError(f"Rule '{name}' is not registered.")
            r = self._rules[name]
            self._rules[name] = AlertRule(
                name=r.name,
                condition=r.condition,
                level=r.level,
                source=r.source,
                cooldown_seconds=r.cooldown_seconds,
                suppress_duplicates=r.suppress_duplicates,
                max_escalations=r.max_escalations,
                escalation_delay_seconds=r.escalation_delay_seconds,
                enabled=True,
                description=r.description,
            )

    def disable_rule(self, name: str) -> None:
        with self._lock:
            if name not in self._rules:
                raise AlertingRuleError(f"Rule '{name}' is not registered.")
            r = self._rules[name]
            self._rules[name] = AlertRule(
                name=r.name,
                condition=r.condition,
                level=r.level,
                source=r.source,
                cooldown_seconds=r.cooldown_seconds,
                suppress_duplicates=r.suppress_duplicates,
                max_escalations=r.max_escalations,
                escalation_delay_seconds=r.escalation_delay_seconds,
                enabled=False,
                description=r.description,
            )

    def evaluate(self, alert: Alert) -> AlertRuleResult:
        with self._lock:
            rule = self._rules.get(alert.rule_name)
            if rule is None:
                return AlertRuleResult(
                    rule_name=alert.rule_name,
                    matched=False,
                    reason="Rule not found",
                )

            if not rule.enabled:
                return AlertRuleResult(
                    rule_name=rule.name,
                    matched=False,
                    suppressed=True,
                    reason="Rule is disabled",
                )

            if rule.source and alert.source != rule.source:
                return AlertRuleResult(
                    rule_name=rule.name,
                    matched=False,
                    reason=f"Source mismatch: expected {rule.source.value}, got {alert.source.value}",
                )

            now = datetime.now(timezone.utc).timestamp()
            last_time = self._cooldowns.get(rule.name, 0.0)
            if now - last_time < rule.cooldown_seconds:
                return AlertRuleResult(
                    rule_name=rule.name,
                    matched=False,
                    suppressed=True,
                    reason="Cooldown active",
                )

            if not self._check_rate_limit(rule.name):
                return AlertRuleResult(
                    rule_name=rule.name,
                    matched=False,
                    suppressed=True,
                    reason="Rate limit exceeded",
                )

            if rule.suppress_duplicates:
                dedup_key = f"{alert.rule_name}:{alert.title}:{alert.source.value}"
                if dedup_key in self._dedup_cache:
                    return AlertRuleResult(
                        rule_name=rule.name,
                        matched=False,
                        suppressed=True,
                        reason="Duplicate suppressed",
                    )
                self._dedup_cache.add(dedup_key)
                if len(self._dedup_cache) > 1000:
                    self._dedup_cache.clear()

            try:
                condition_result = rule.condition(alert)
            except Exception as exc:
                raise AlertingRuleError(
                    f"Rule '{rule.name}' condition evaluation failed: {exc}"
                ) from exc

            if not condition_result:
                return AlertRuleResult(
                    rule_name=rule.name,
                    matched=False,
                    reason="Condition not met",
                )

            self._cooldowns[rule.name] = now

            escalation_count = self._escalation_counts.get(alert.alert_id, 0)
            should_escalate = escalation_count >= rule.max_escalations

            if should_escalate:
                self._escalation_counts[alert.alert_id] = (
                    self._escalation_counts.get(alert.alert_id, 0) + 1
                )

            return AlertRuleResult(
                rule_name=rule.name,
                matched=True,
                alert=alert,
                escalated=should_escalate,
                suppressed=False,
                reason="Rule matched",
            )

    def evaluate_all(self, alert: Alert) -> tuple[AlertRuleResult, ...]:
        results: list[AlertRuleResult] = []
        with self._lock:
            rule_names = list(self._rules.keys())

        for name in rule_names:
            result = self.evaluate(
                Alert(
                    alert_id=alert.alert_id,
                    level=alert.level,
                    source=alert.source,
                    title=alert.title,
                    message=alert.message,
                    timestamp=alert.timestamp,
                    status=alert.status,
                    rule_name=name,
                    metadata=alert.metadata,
                    tags=alert.tags,
                )
            )
            results.append(result)

        return tuple(results)

    def evaluate_threshold(
        self,
        name: str,
        value: float,
        warning_threshold: float,
        critical_threshold: float,
        source: AlertSource,
        title: str,
        message_template: str,
    ) -> AlertRuleResult | None:
        if value >= critical_threshold:
            alert = Alert(
                alert_id=f"threshold:{name}:{datetime.now(timezone.utc).timestamp()}",
                level=AlertLevel.CRITICAL,
                source=source,
                title=title,
                message=message_template.format(value=value),
                metadata={"value": value, "threshold": critical_threshold},
            )
            return self._evaluate_with_rule(name, alert)

        if value >= warning_threshold:
            alert = Alert(
                alert_id=f"threshold:{name}:{datetime.now(timezone.utc).timestamp()}",
                level=AlertLevel.WARNING,
                source=source,
                title=title,
                message=message_template.format(value=value),
                metadata={"value": value, "threshold": warning_threshold},
            )
            return self._evaluate_with_rule(name, alert)

        return None

    def evaluate_state_change(
        self,
        name: str,
        key: str,
        new_state: str,
        source: AlertSource,
        title: str,
        message: str,
    ) -> AlertRuleResult | None:
        with self._lock:
            old_state = self._last_state.get(key)
            if old_state == new_state:
                return None
            self._last_state[key] = new_state

        if old_state is not None:
            alert = Alert(
                alert_id=f"state_change:{key}:{datetime.now(timezone.utc).timestamp()}",
                level=AlertLevel.WARNING,
                source=source,
                title=title,
                message=message,
                metadata={"old_state": old_state, "new_state": new_state},
            )
            return self._evaluate_with_rule(name, alert)

        return None

    def acknowledge(self, alert_id: str) -> None:
        with self._lock:
            self._dedup_cache.discard(alert_id)
            self._escalation_counts.pop(alert_id, None)

    def reset(self) -> None:
        with self._lock:
            self._rules.clear()
            self._cooldowns.clear()
            self._dedup_cache.clear()
            self._escalation_counts.clear()
            self._rate_limits.clear()
            self._last_state.clear()

    def rule_names(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._rules.keys()))

    def _evaluate_with_rule(self, rule_name: str, alert: Alert) -> AlertRuleResult:
        alert_with_rule = Alert(
            alert_id=alert.alert_id,
            level=alert.level,
            source=alert.source,
            title=alert.title,
            message=alert.message,
            timestamp=alert.timestamp,
            status=alert.status,
            rule_name=rule_name,
            metadata=alert.metadata,
            tags=alert.tags,
        )
        return self.evaluate(alert_with_rule)

    def _check_rate_limit(self, rule_name: str) -> bool:
        now = datetime.now(timezone.utc).timestamp()
        timestamps = self._rate_limits.get(rule_name, [])
        cutoff = now - 60.0
        timestamps = [t for t in timestamps if t > cutoff]
        if len(timestamps) >= 10:
            return False
        timestamps.append(now)
        self._rate_limits[rule_name] = timestamps
        return True
