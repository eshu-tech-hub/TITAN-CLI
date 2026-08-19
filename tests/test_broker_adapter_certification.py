"""
Tests for Broker Adapter Certification (Capability & Interface).
"""

from tests.mocks.mock_broker_faulty import MockBrokerFaulty
from tests.mocks.mock_broker_full import MockBrokerFull
from tests.mocks.mock_broker_partial import MockBrokerPartial
from titan.brokers.certification.adapters import (
    BrokerAdapterInspector,
    BrokerFeatureDiscovery,
    BrokerInterfaceComplianceChecker,
)


def test_inspector():
    broker = MockBrokerFull()
    inspector = BrokerAdapterInspector(broker)
    assert inspector.has_method("place_order")
    assert not inspector.has_method("does_not_exist")


def test_interface_compliance_full():
    broker = MockBrokerFull()
    checker = BrokerInterfaceComplianceChecker()
    assert checker.check_compliance(broker)


def test_interface_compliance_faulty():
    broker = MockBrokerFaulty()
    checker = BrokerInterfaceComplianceChecker()
    assert not checker.check_compliance(broker)


def test_feature_discovery_full():
    broker = MockBrokerFull()
    caps = BrokerFeatureDiscovery.discover_capabilities(broker)
    cap_ids = [c.capability_id for c in caps]
    assert "AUTH" in cap_ids
    assert "ORDERS" in cap_ids
    assert "POSITIONS" in cap_ids


def test_feature_discovery_partial():
    broker = MockBrokerPartial()
    caps = BrokerFeatureDiscovery.discover_capabilities(broker)
    cap_ids = [c.capability_id for c in caps]
    assert "ORDERS" in cap_ids
    assert "POSITIONS" not in cap_ids
