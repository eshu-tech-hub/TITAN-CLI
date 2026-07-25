"""
Mock broker simulating timeouts.
"""

from tests.mocks.mock_broker_full import MockBrokerFull


class MockBrokerTimeout(MockBrokerFull):
    """Simulates network timeout on place_order."""

    def place_order(self):
        raise TimeoutError("Network connection timed out.")
