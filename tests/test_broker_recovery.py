"""
Tests for Broker Recovery Certification scenarios.
"""

from titan.brokers.certification.runner import BrokerCertificationRunner
from titan.brokers.certification.models import CertificationStatus
from tests.mocks.mock_broker_timeout import MockBrokerTimeout


def test_recovery_timeout():
    broker = MockBrokerTimeout()
    runner = BrokerCertificationRunner(broker_id="MOCK_TIMEOUT")
    report = runner.run_certification(broker)

    # The order placement should timeout and fail, testing recovery visibility
    order_market_buy = next(
        (
            r
            for r in report.scenario_results
            if r.scenario.scenario_id == "ORDER_MARKET_BUY"
        ),
        None,
    )
    if order_market_buy:
        assert order_market_buy.status == CertificationStatus.FAIL
        assert "Network connection timed out" in order_market_buy.message
