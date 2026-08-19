"""
Adapters and inspectors for broker capabilities and interfaces.
"""

from typing import Any

from titan.brokers.certification.models import BrokerCapability
from titan.brokers.certification.validator import InterfaceValidator


class BrokerAdapterInspector:
    """Inspects a broker adapter instance for features and attributes."""

    def __init__(self, broker: Any):
        self._broker = broker

    def has_method(self, method_name: str) -> bool:
        """Checks if the broker has a specific callable method."""
        attr = getattr(self._broker, method_name, None)
        return callable(attr)

    def has_attribute(self, attr_name: str) -> bool:
        """Checks if the broker has a specific attribute."""
        return hasattr(self._broker, attr_name)


class BrokerInterfaceComplianceChecker:
    """Verifies interface compliance using the underlying InterfaceValidator to avoid duplication."""

    def __init__(self):
        self._validator = InterfaceValidator()

    def check_compliance(self, broker: Any) -> bool:
        """Checks if the broker complies with the required interfaces."""
        result = self._validator.validate(broker)
        # Using string comparison as status might be an Enum
        return bool(result.status.name == "PASS")


class BrokerFeatureDiscovery:
    """Dynamically identifies capabilities supported by a broker."""

    @staticmethod
    def discover_capabilities(broker: Any) -> list[BrokerCapability]:
        """Inspects the broker and builds a list of its supported capabilities."""
        inspector = BrokerAdapterInspector(broker)
        capabilities = []

        # Determine capabilities based on method presence

        # Authentication is assumed if connect is present
        if inspector.has_method("connect"):
            capabilities.append(
                BrokerCapability(
                    "AUTH", "Authentication", "Login and logout operations", True
                )
            )

        # Orders
        if inspector.has_method("place_order") and inspector.has_method("cancel_order"):
            capabilities.append(
                BrokerCapability(
                    "ORDERS", "Order Management", "Order lifecycle management", True
                )
            )

        # Account / Funds
        if inspector.has_method("get_funds"):
            capabilities.append(
                BrokerCapability(
                    "FUNDS", "Funds Retrieval", "Account balances and margins", True
                )
            )

        # Market Data
        if inspector.has_method("get_ltp") or inspector.has_method("get_quote"):
            capabilities.append(
                BrokerCapability(
                    "MARKET_DATA", "Market Data", "Real-time market quotes", True
                )
            )

        # Positions
        if inspector.has_method("get_positions"):
            capabilities.append(
                BrokerCapability(
                    "POSITIONS", "Positions", "Retrieval of open positions", True
                )
            )

        # Holdings
        if inspector.has_method("get_holdings"):
            capabilities.append(
                BrokerCapability(
                    "HOLDINGS", "Holdings", "Retrieval of portfolio holdings", True
                )
            )

        return capabilities
