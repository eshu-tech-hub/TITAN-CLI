"""
Faulty mock broker missing mandatory interfaces.
"""

from tests.mocks.mock_broker import MockBroker


class MockBrokerFaulty(MockBroker):
    """Missing mandatory interfaces (e.g., place_order)."""

    def get_funds(self):
        return {"available": 10000.0, "used": 500.0}
