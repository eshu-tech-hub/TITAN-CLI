from __future__ import annotations

from titan.config.models import (
    BrokerProvider,
    EnvironmentProfile,
    LogLevel,
)


def profile_defaults(profile: str) -> dict:
    """Return the default configuration overrides for a given profile.

    Each profile returns only the keys that differ from the base defaults.
    """
    registry: dict[str, dict] = {
        EnvironmentProfile.DEVELOPMENT: {
            "app": {"log_level": LogLevel.DEBUG.value},
            "broker": {
                "provider": BrokerProvider.PAPER.value,
                "exchange": "nse",
            },
            "runtime": {
                "pipeline_interval_seconds": 120.0,
                "stream_enabled": False,
            },
            "risk": {
                "max_position_size": 10000,
                "max_drawdown_percent": 25.0,
            },
        },
        EnvironmentProfile.TESTING: {
            "app": {"log_level": LogLevel.DEBUG.value},
            "broker": {"provider": BrokerProvider.PAPER.value},
            "runtime": {
                "pipeline_interval_seconds": 5.0,
                "stream_enabled": False,
                "heartbeat_interval_seconds": 2.0,
            },
            "risk": {
                "max_position_size": 1000000,
                "max_drawdown_percent": 100.0,
                "max_daily_loss": 1000000,
                "max_leverage": 5.0,
            },
            "execution": {
                "max_retries": 1,
                "retry_delay_seconds": 0.1,
            },
            "monitoring": {"enabled": False},
        },
        EnvironmentProfile.PAPER_TRADING: {
            "app": {"log_level": LogLevel.INFO.value},
            "broker": {
                "provider": BrokerProvider.PAPER.value,
                "paper_initial_cash": 100000,
            },
            "runtime": {
                "pipeline_interval_seconds": 60.0,
                "stream_enabled": True,
            },
            "risk": {
                "max_position_size": 50000,
                "max_drawdown_percent": 15.0,
            },
            "execution": {
                "default_slippage_percent": 0.05,
            },
        },
        EnvironmentProfile.BACKTESTING: {
            "app": {"log_level": LogLevel.INFO.value},
            "broker": {"provider": BrokerProvider.PAPER.value},
            "runtime": {
                "pipeline_interval_seconds": 0.0,
                "scheduler_enabled": False,
                "stream_enabled": False,
                "heartbeat_enabled": False,
            },
            "risk": {
                "max_position_size": 1000000,
                "max_drawdown_percent": 100.0,
                "max_daily_loss": 1000000,
            },
            "execution": {
                "max_retries": 0,
            },
            "monitoring": {"enabled": False},
        },
        EnvironmentProfile.PRODUCTION: {
            "app": {"log_level": LogLevel.WARNING.value},
            "broker": {
                "provider": BrokerProvider.PAPER.value,
                "exchange": "nse",
            },
            "runtime": {
                "pipeline_interval_seconds": 60.0,
                "stream_enabled": True,
                "heartbeat_interval_seconds": 5.0,
            },
            "risk": {
                "max_position_size": 50000,
                "max_drawdown_percent": 10.0,
                "max_daily_loss": 25000,
                "max_leverage": 0.5,
                "margin_call_threshold_percent": 30.0,
                "stop_loss_percent": 2.0,
            },
            "execution": {
                "max_retries": 5,
                "retry_delay_seconds": 2.0,
                "default_slippage_percent": 0.05,
            },
            "monitoring": {
                "enabled": True,
                "prometheus_port": 8000,
                "health_check_interval_seconds": 15.0,
            },
        },
    }

    result = registry.get(profile)
    if result is None:
        msg = f"Unknown profile: {profile}. Valid: {list(registry)}"
        raise ValueError(msg)

    return result
