"""
Tests for Broker Order Lifecycle Certification scenarios.
"""

from tests.mocks.mock_broker_full import MockBrokerFull
from tests.mocks.mock_broker_rejecting import MockBrokerRejecting
from titan.brokers.certification.models import CertificationStatus
from titan.brokers.certification.runner import BrokerCertificationRunner


def test_order_lifecycle_full():
    broker = MockBrokerFull()
    runner = BrokerCertificationRunner(broker_id="MOCK_FULL")
    report = runner.run_certification(broker)

    order_results = [
        r for r in report.scenario_results if r.scenario.category == "Orders"
    ]
    assert any(r.status == CertificationStatus.PASS for r in order_results)


def test_order_lifecycle_rejecting():
    broker = MockBrokerRejecting()
    runner = BrokerCertificationRunner(broker_id="MOCK_REJECTING")
    report = runner.run_certification(broker)

    # We expect the market buy scenario to fail due to exchange rejection simulated
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
        assert "Order rejected by exchange" in order_market_buy.message
