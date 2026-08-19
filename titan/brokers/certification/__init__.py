"""
Broker Certification Framework Foundation.

Provides a robust, immutable framework for certifying institutional-grade brokers.
"""

from titan.brokers.certification.models import (
    BrokerCapability,
    BrokerCapabilityMatrix,
    BrokerCertificationMetadata,
    BrokerCertificationReport,
    BrokerCertificationResult,
    BrokerCertificationScenario,
    BrokerCertificationSummary,
    BrokerValidationResult,
    CertificationSeverity,
    CertificationStatus,
)
from titan.brokers.certification.report import (
    BrokerCapabilityMatrixBuilder,
    CertificationReportBuilder,
)
from titan.brokers.certification.runner import BrokerCertificationRunner
from titan.brokers.certification.scenarios import ALL_SCENARIOS
from titan.brokers.certification.validator import (
    CapabilityValidator,
    CertificationEngine,
    ComplianceValidator,
    InterfaceValidator,
    ScenarioValidator,
)

__all__ = [
    "ALL_SCENARIOS",
    "BrokerCapability",
    "BrokerCapabilityMatrix",
    "BrokerCapabilityMatrixBuilder",
    "BrokerCertificationMetadata",
    "BrokerCertificationReport",
    "BrokerCertificationResult",
    "BrokerCertificationRunner",
    "BrokerCertificationScenario",
    "BrokerCertificationSummary",
    "BrokerValidationResult",
    "CapabilityValidator",
    "CertificationEngine",
    "CertificationReportBuilder",
    "CertificationSeverity",
    "CertificationStatus",
    "ComplianceValidator",
    "InterfaceValidator",
    "ScenarioValidator",
]
