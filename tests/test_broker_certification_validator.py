"""
Tests for Broker Certification Validator / Engine.
"""

from titan.brokers.certification.models import (
    BrokerCapability,
    CertificationStatus,
)
from titan.brokers.certification.validator import (
    CapabilityValidator,
    CertificationEngine,
    InterfaceValidator,
)


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


def test_capability_validator_missing_fields():
    validator = CapabilityValidator()
    cap = BrokerCapability(capability_id="", name="", description="", is_supported=True)
    result = validator.validate([cap])

    assert result.status == CertificationStatus.FAIL
    assert "missing ID or name" in result.details


def test_interface_validator_success():
    validator = InterfaceValidator()
    broker = MockBroker()

    result = validator.validate(broker)
    assert result.status == CertificationStatus.PASS


def test_certification_engine():
    engine = CertificationEngine()
    broker = MockBroker()
    caps = [BrokerCapability("ORDER_MANAGEMENT", "Orders", "Desc", True)]

    results = engine.run_validations(broker, caps)

    assert len(results) > 3  # Cap, Interface, Scenarios..., Compliance
    # Just checking that it runs without error and returns results
    assert all(
        r.status != CertificationStatus.FAIL
        for r in results
        if not r.validation_id.startswith("SCEN_VAL")
    )
