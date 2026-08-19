"""Shared CLI utilities: lazy-loaded singletons and error handling."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from titan.core.config import get_settings
from titan.core.display import console
from titan.core.logger import logger

if TYPE_CHECKING:
    from titan.alerting.manager import AlertManager
    from titan.audit.manager import AuditManager
    from titan.brokers.broker import Broker
    from titan.config.manager import ConfigManager
    from titan.config.models import TitanConfig
    from titan.deployment.manager import DeploymentManager
    from titan.monitoring.manager import MonitoringManager
    from titan.recovery.manager import RecoveryManager
    from titan.runtime.runtime import RuntimeEngine


@lru_cache(maxsize=1)
def _config_manager() -> ConfigManager:
    from titan.config.manager import ConfigManager

    return ConfigManager()


@lru_cache(maxsize=1)
def _deployment_manager() -> DeploymentManager:
    from titan.deployment.manager import DeploymentManager

    return DeploymentManager.instance()


@lru_cache(maxsize=1)
def _monitoring_manager() -> MonitoringManager:
    from titan.monitoring.manager import MonitoringManager

    return MonitoringManager()


@lru_cache(maxsize=1)
def _alert_manager() -> AlertManager:
    from titan.alerting.manager import AlertManager

    return AlertManager()


_runtime_engine: RuntimeEngine | None = None


def get_runtime_engine() -> RuntimeEngine:
    global _runtime_engine
    if _runtime_engine is None:
        from decimal import Decimal

        from titan.paper.broker import PaperBroker
        from titan.runtime.runtime import RuntimeEngine

        broker = PaperBroker(initial_cash=Decimal(100000))
        _runtime_engine = RuntimeEngine(broker=broker)
    return _runtime_engine


def set_runtime_engine(engine: RuntimeEngine) -> None:
    global _runtime_engine
    _runtime_engine = engine


@lru_cache(maxsize=1)
def _recovery_manager() -> RecoveryManager:
    from titan.recovery.manager import RecoveryManager

    return RecoveryManager()


def get_recovery_manager() -> RecoveryManager:
    return _recovery_manager()


def get_config_manager() -> ConfigManager:
    return _config_manager()


def get_deployment_manager() -> DeploymentManager:
    return _deployment_manager()


def get_monitoring_manager() -> MonitoringManager:
    return _monitoring_manager()


def get_alert_manager() -> AlertManager:
    return _alert_manager()


@lru_cache(maxsize=1)
def _audit_manager() -> AuditManager:
    from titan.audit.manager import AuditManager

    return AuditManager()


def get_audit_manager() -> AuditManager:
    return _audit_manager()


def reset_alert_manager() -> None:
    """Reset the shared AlertManager (for testing)."""
    _alert_manager.cache_clear()
    manager = _alert_manager()
    manager.reset()


_PROVIDER_MAP: dict[str, str] = {
    "paper": "PAPER",
    "angel_one": "ANGEL_ONE",
    "zerodha": "ZERODHA",
    "dhan": "DHAN",
    "upstox": "UPSTOX",
}


def create_broker(config: TitanConfig) -> Broker:
    provider = config.broker.provider.lower()
    broker_type_str = _PROVIDER_MAP.get(provider, provider.upper())

    from titan.brokers.models import BrokerType

    try:
        broker_type = BrokerType(broker_type_str)
    except ValueError:
        from titan.brokers.models import BrokerType as BT

        broker_type = BT.PAPER

    if broker_type_str == "PAPER" or broker_type.name == "PAPER":
        from decimal import Decimal

        from titan.paper.broker import PaperBroker

        return PaperBroker(initial_cash=Decimal(str(config.broker.paper_initial_cash)))

    if broker_type.name == "ANGEL_ONE":
        try:
            from titan.brokers.angelone.adapter import AngelOneBroker

            return AngelOneBroker(
                api_key=config.broker.api_key,
                client_id=config.broker.client_id,
                pin=config.broker.pin,
                totp_secret=config.broker.totp_secret,
            )
        except ImportError:
            pass

    from decimal import Decimal

    from titan.paper.broker import PaperBroker

    return PaperBroker(initial_cash=Decimal(str(config.broker.paper_initial_cash)))


def create_runtime_engine(config: TitanConfig) -> RuntimeEngine:
    from titan.runtime.runtime import RuntimeEngine

    broker = create_broker(config)
    return RuntimeEngine(broker=broker)


__all__ = [
    "console",
    "create_broker",
    "create_runtime_engine",
    "get_alert_manager",
    "get_audit_manager",
    "get_config_manager",
    "get_deployment_manager",
    "get_monitoring_manager",
    "get_recovery_manager",
    "get_runtime_engine",
    "get_settings",
    "logger",
    "set_runtime_engine",
]
