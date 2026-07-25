"""
Mock broker lacking some optional capabilities.
"""

from tests.mocks.mock_broker import MockBroker


class MockBrokerPartial(MockBroker):
    """Missing optional interfaces like get_positions or get_holdings."""

    def get_funds(self):
        return {"available": 10000.0, "used": 500.0}

    def place_order(self):
        return "ORDER_123"

    def cancel_order(self):
        return True
