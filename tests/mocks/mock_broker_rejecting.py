"""
Mock broker simulating exchange rejections.
"""

from tests.mocks.mock_broker_full import MockBrokerFull


class MockBrokerRejecting(MockBrokerFull):
    """Simulates exchange rejecting an order."""

    def place_order(self):
        raise ValueError("Order rejected by exchange: Invalid price limit.")
