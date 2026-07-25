"""
Tests for Broker Account Certification scenarios.
"""

from titan.brokers.certification.runner import BrokerCertificationRunner
from titan.brokers.certification.models import CertificationStatus
from tests.mocks.mock_broker_full import MockBrokerFull


def test_account_stage():
    broker = MockBrokerFull()
    runner = BrokerCertificationRunner(broker_id="MOCK_FULL")
    report = runner.run_certification(broker)

    funds_results = [
        r for r in report.scenario_results if r.scenario.category == "Funds"
    ]
    assert any(r.status == CertificationStatus.PASS for r in funds_results)
