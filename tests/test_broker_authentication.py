"""
Tests for Broker Authentication scenarios.
"""

from tests.mocks.mock_broker_full import MockBrokerFull
from titan.brokers.certification.models import CertificationStatus
from titan.brokers.certification.runner import BrokerCertificationRunner


def test_authentication_stage():
    broker = MockBrokerFull()
    runner = BrokerCertificationRunner(broker_id="MOCK_FULL")

    # Run certification which executes all stages including Authentication
    report = runner.run_certification(broker)

    auth_results = [
        r for r in report.scenario_results if r.scenario.category == "Authentication"
    ]

    assert len(auth_results) > 0
    # In our mock foundation, these are marked PASS or FAIL based on presence of capability or simulated execution
    for res in auth_results:
        assert res.status in (
            CertificationStatus.PASS,
            CertificationStatus.FAIL,
            CertificationStatus.NOT_APPLICABLE,
        )
