from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any
import os
import sys

from titan.config.validation_models import (
    ValidationIssue,
    ValidationReport,
    ValidationSeverity,
)
from titan.core.config import get_settings

from titan.config.models import (
    BrokerProvider,
    EnvironmentProfile,
    LogLevel,
)


def validate(raw: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Validate a raw configuration dictionary.

    Returns:
        A tuple of ``(warnings, errors)``. Both lists are empty
        for a fully valid configuration.
    """
    warnings: list[str] = []
    errors: list[str] = []

    _validate_profile(raw, warnings, errors)
    _validate_app(raw.get("app", {}), warnings, errors)
    _validate_broker(raw.get("broker", {}), warnings, errors)
    _validate_runtime(raw.get("runtime", {}), warnings, errors)
    _validate_risk(raw.get("risk", {}), warnings, errors)
    _validate_execution(raw.get("execution", {}), warnings, errors)
    _validate_logging(raw.get("logging", {}), warnings, errors)
    _validate_monitoring(raw.get("monitoring", {}), warnings, errors)

    return warnings, errors


# ── Section validators ──


def _validate_profile(
    raw: dict[str, Any], warnings: list[str], errors: list[str]
) -> None:
    profile = raw.get("profile", "development")
    valid = {e.value for e in EnvironmentProfile}
    if profile not in valid:
        errors.append(
            f"Unknown profile '{profile}'. Valid values: {', '.join(sorted(valid))}"
        )


def _validate_app(raw: dict[str, Any], warnings: list[str], errors: list[str]) -> None:
    _check_type(raw, "log_level", str, errors)
    level = raw.get("log_level", "INFO")
    if isinstance(level, str):
        valid_levels = {e.value for e in LogLevel}
        if level.upper() not in valid_levels:
            warnings.append(
                f"Unknown log_level '{level}'. Valid: {', '.join(sorted(valid_levels))}"
            )


def _validate_broker(
    raw: dict[str, Any], warnings: list[str], errors: list[str]
) -> None:
    _check_type(raw, "provider", str, errors)
    provider = raw.get("provider", "paper")
    valid_providers = {e.value for e in BrokerProvider}
    if provider not in valid_providers:
        warnings.append(
            f"Unknown broker provider '{provider}'. "
            f"Valid: {', '.join(sorted(valid_providers))}"
        )

    _check_type(raw, "connection_timeout_seconds", (int, float), errors)
    timeout = raw.get("connection_timeout_seconds", 30.0)
    if isinstance(timeout, (int, float)) and timeout <= 0:
        errors.append("connection_timeout_seconds must be positive")

    _check_type(raw, "max_retries", int, errors)
    retries = raw.get("max_retries", 3)
    if isinstance(retries, int) and retries < 0:
        errors.append("broker max_retries must be non-negative")


def _validate_runtime(
    raw: dict[str, Any], warnings: list[str], errors: list[str]
) -> None:
    _check_type(raw, "pipeline_interval_seconds", (int, float), errors)
    interval = raw.get("pipeline_interval_seconds", 60.0)
    if isinstance(interval, (int, float)) and interval < 0:
        errors.append("pipeline_interval_seconds must be non-negative")

    _check_type(raw, "heartbeat_interval_seconds", (int, float), errors)
    hb = raw.get("heartbeat_interval_seconds", 10.0)
    if isinstance(hb, (int, float)) and hb <= 0:
        errors.append("heartbeat_interval_seconds must be positive")

    _check_type(raw, "max_pipeline_executions", int, errors)
    max_exec = raw.get("max_pipeline_executions", 0)
    if isinstance(max_exec, int) and max_exec < 0:
        errors.append("max_pipeline_executions must be non-negative")


def _validate_risk(raw: dict[str, Any], warnings: list[str], errors: list[str]) -> None:
    _check_number_range(raw, "max_drawdown_percent", 0, 100, errors)
    _check_number_range(raw, "margin_call_threshold_percent", 0, 100, errors)
    _check_number_range(raw, "stop_loss_percent", 0, 100, errors)
    _check_number_range(raw, "max_leverage", 0, 100, errors)

    max_pos = raw.get("max_position_size")
    if max_pos is not None:
        try:
            val = Decimal(str(max_pos))
            if val < 0:
                errors.append("max_position_size must be non-negative")
        except Exception:
            errors.append("max_position_size must be a valid number")


def _validate_execution(
    raw: dict[str, Any], warnings: list[str], errors: list[str]
) -> None:
    _check_type(raw, "max_retries", int, errors)
    retries = raw.get("max_retries", 3)
    if isinstance(retries, int) and retries < 0:
        errors.append("execution max_retries must be non-negative")

    _check_type(raw, "retry_delay_seconds", (int, float), errors)
    delay = raw.get("retry_delay_seconds", 5.0)
    if isinstance(delay, (int, float)) and delay < 0:
        errors.append("retry_delay_seconds must be non-negative")

    _check_type(raw, "order_timeout_seconds", (int, float), errors)
    timeout = raw.get("order_timeout_seconds", 30.0)
    if isinstance(timeout, (int, float)) and timeout <= 0:
        errors.append("order_timeout_seconds must be positive")


def _validate_logging(
    raw: dict[str, Any], warnings: list[str], errors: list[str]
) -> None:
    _check_type(raw, "level", str, errors)
    _check_type(raw, "file", str, errors)
    _check_type(raw, "max_size_mb", int, errors)
    _check_type(raw, "backup_count", int, errors)
    _check_type(raw, "format_template", str, errors)

    log_file = raw.get("file", "")
    if log_file:
        p = Path(log_file)
        parent = p.parent
        if parent and not parent.exists():
            warnings.append(f"Log directory does not exist: {parent}")


def _validate_monitoring(
    raw: dict[str, Any], warnings: list[str], errors: list[str]
) -> None:
    _check_type(raw, "enabled", bool, errors)
    _check_type(raw, "prometheus_port", int, errors)
    port = raw.get("prometheus_port", 8000)
    if isinstance(port, int) and not (0 < port < 65536):
        errors.append(f"prometheus_port {port} is out of valid range (1-65535)")


# ── Helpers ──


def _check_type(
    raw: dict[str, Any],
    key: str,
    expected: type | tuple[type, ...],
    errors: list[str],
) -> None:
    if key not in raw:
        return
    value = raw[key]
    if not isinstance(value, expected):
        type_name = _type_name(expected)
        errors.append(f"'{key}' must be {type_name}, got {type(value).__name__}")


def _check_number_range(
    raw: dict[str, Any],
    key: str,
    minimum: float,
    maximum: float,
    errors: list[str],
) -> None:
    value = raw.get(key)
    if value is None:
        return
    try:
        val = float(value)
        if val < minimum or val > maximum:
            errors.append(f"'{key}' must be between {minimum} and {maximum}")
    except ValueError, TypeError:
        errors.append(f"'{key}' must be a valid number")


def _type_name(expected: type | tuple[type, ...]) -> str:
    if isinstance(expected, tuple):
        return " or ".join(t.__name__ for t in expected)
    return expected.__name__


class ConfigurationValidator:
    """Performs deterministic checks on the TITAN operational environment."""

    def validate_all(self) -> ValidationReport:
        """Run all configured validation checks."""
        issues: list[ValidationIssue] = []
        issues.extend(self.validate_environment())
        issues.extend(self.validate_directories())
        issues.extend(self.validate_broker_config())
        return ValidationReport(issues=tuple(issues))

    def validate_environment(self) -> list[ValidationIssue]:
        """Check for correct Python versions and core environment requirements."""
        issues: list[ValidationIssue] = []
        # TITAN strictly requires Python 3.14+
        if sys.version_info < (3, 14):
            issues.append(
                ValidationIssue(
                    component="Environment",
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Python 3.14+ required. Found {sys.version_info[0]}.{sys.version_info[1]}",
                )
            )
        return issues

    def validate_directories(self) -> list[ValidationIssue]:
        """Verify that necessary data and log directories exist and are writable."""
        issues: list[ValidationIssue] = []
        for dir_name in ["data", "logs"]:
            path = Path(dir_name)
            if not path.exists():
                issues.append(
                    ValidationIssue(
                        component="FileSystem",
                        severity=ValidationSeverity.WARNING,
                        message=f"Directory '{dir_name}' is missing and should be created.",
                    )
                )
            elif not os.access(path, os.W_OK):
                issues.append(
                    ValidationIssue(
                        component="FileSystem",
                        severity=ValidationSeverity.CRITICAL,
                        message=f"Directory '{dir_name}' is not writable.",
                    )
                )
        return issues

    def validate_broker_config(self) -> list[ValidationIssue]:
        """Verify broker keys exist if not running in paper trading mode."""
        issues: list[ValidationIssue] = []
        try:
            settings = get_settings()
            provider = getattr(settings, "broker", "paper").lower()

            if provider != "paper":
                api_key = os.getenv("TITAN_BROKER_API_KEY", "")
                if not api_key:
                    issues.append(
                        ValidationIssue(
                            component="Broker",
                            severity=ValidationSeverity.CRITICAL,
                            message=f"TITAN_BROKER_API_KEY is missing for live provider '{provider}'.",
                        )
                    )
        except Exception as e:
            issues.append(
                ValidationIssue(
                    component="Configuration",
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Failed to load settings during validation: {e}",
                )
            )
        return issues
