"""
Tests for Broker Certification Runner.
"""

from titan.brokers.certification.models import (
    BrokerCapability,
    CertificationStatus,
)
from titan.brokers.certification.runner import BrokerCertificationRunner


class MockBroker:
    def connect(self):
        pass

    def disconnect(self):
        pass

    def get_funds(self):
        pass

    def place_order(self):
        pass

    def cancel_order(self):
        pass

    rate_limit_calls = 100


def test_runner_orchestration():
    runner = BrokerCertificationRunner(broker_id="MOCK_BROKER")
    broker = MockBroker()

    caps = [
        BrokerCapability("ORDER_MANAGEMENT", "Order Management", "Allows orders", True),
        BrokerCapability("MARKET_DATA", "Market Data", "Real-time data", True),
    ]

    report = runner.run_certification(broker, caps)

    assert report.metadata.broker_id == "MOCK_BROKER"
    assert report.summary.total_scenarios > 0
    assert report.capability_matrix.broker_id == "MOCK_BROKER"
    assert len(report.capability_matrix.capabilities) == 2
    assert report.summary.status in (
        CertificationStatus.PASS,
        CertificationStatus.PASS_WITH_WARNINGS,
        CertificationStatus.PARTIAL,
        CertificationStatus.FAIL,
    )
