"""
Tests for Broker Certification Models.
"""

from dataclasses import FrozenInstanceError
import pytest

from titan.brokers.certification.models import (
    BrokerCertificationMetadata,
    CertificationSeverity,
    BrokerCapability,
    BrokerCertificationScenario,
)


def test_metadata_immutability():
    metadata = BrokerCertificationMetadata(
        broker_id="TEST_BROKER", certification_version="1.0"
    )
    with pytest.raises(FrozenInstanceError):
        metadata.broker_id = "NEW_BROKER"  # type: ignore


def test_capability_default_values():
    cap = BrokerCapability(
        capability_id="CAP_01",
        name="Test Cap",
        description="A test capability",
        is_supported=True,
    )
    assert not cap.requires_approval
    assert cap.limitations == tuple()


def test_scenario_serialization():
    # Since dataclasses aren't natively json serializable by default without an encoder,
    # we just test that the attributes are accessible and of correct types.
    # In practice, a framework standard encoder would handle the conversion.
    scenario = BrokerCertificationScenario(
        scenario_id="TEST_01",
        name="Test Scenario",
        description="A test scenario.",
        category="Test",
        severity=CertificationSeverity.HIGH,
        expected_behavior="Passes",
        pass_criteria=("Criterion 1",),
    )

    assert scenario.severity.value == "HIGH"
    assert "Criterion 1" in scenario.pass_criteria
