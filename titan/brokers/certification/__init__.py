"""
Broker Certification Framework Foundation.

Provides a robust, immutable framework for certifying institutional-grade brokers.
"""

from titan.brokers.certification.models import (
    BrokerCertificationReport,
    BrokerCertificationSummary,
    BrokerCertificationScenario,
    BrokerCertificationResult,
    BrokerCapability,
    BrokerCapabilityMatrix,
    BrokerValidationResult,
    CertificationSeverity,
    CertificationStatus,
    BrokerCertificationMetadata,
)
from titan.brokers.certification.runner import BrokerCertificationRunner
from titan.brokers.certification.validator import (
    CertificationEngine,
    CapabilityValidator,
    InterfaceValidator,
    ScenarioValidator,
    ComplianceValidator,
)
from titan.brokers.certification.report import (
    CertificationReportBuilder,
    BrokerCapabilityMatrixBuilder,
)
from titan.brokers.certification.scenarios import ALL_SCENARIOS

__all__ = [
    "BrokerCertificationReport",
    "BrokerCertificationSummary",
    "BrokerCertificationScenario",
    "BrokerCertificationResult",
    "BrokerCapability",
    "BrokerCapabilityMatrix",
    "BrokerValidationResult",
    "CertificationSeverity",
    "CertificationStatus",
    "BrokerCertificationMetadata",
    "BrokerCertificationRunner",
    "CertificationEngine",
    "CapabilityValidator",
    "InterfaceValidator",
    "ScenarioValidator",
    "ComplianceValidator",
    "CertificationReportBuilder",
    "BrokerCapabilityMatrixBuilder",
    "ALL_SCENARIOS",
]
