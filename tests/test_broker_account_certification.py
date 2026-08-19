"""
Tests for Broker Account Certification scenarios.
"""

from tests.mocks.mock_broker_full import MockBrokerFull
from titan.brokers.certification.models import CertificationStatus
from titan.brokers.certification.runner import BrokerCertificationRunner


def test_account_stage():
    broker = MockBrokerFull()
    runner = BrokerCertificationRunner(broker_id="MOCK_FULL")
    report = runner.run_certification(broker)

    funds_results = [
        r for r in report.scenario_results if r.scenario.category == "Funds"
    ]
    assert any(r.status == CertificationStatus.PASS for r in funds_results)
