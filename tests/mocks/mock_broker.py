"""
Base mock broker for certification tests.
"""


class MockBroker:
    """Base class for mock brokers."""

    def __init__(self):
        self.rate_limit_calls = 100
        self.connected = False

    def connect(self):
        self.connected = True
        return True

    def disconnect(self):
        self.connected = False
        return True
