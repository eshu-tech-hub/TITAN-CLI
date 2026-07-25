"""
Fully compliant mock broker.
"""

from tests.mocks.mock_broker import MockBroker


class MockBrokerFull(MockBroker):
    """Fully compliant broker implementing all required interfaces."""

    def get_funds(self):
        return {"available": 10000.0, "used": 500.0}

    def place_order(self):
        return "ORDER_123"

    def cancel_order(self):
        return True

    def get_positions(self):
        return []

    def get_holdings(self):
        return []

    def get_ltp(self):
        return 150.0
