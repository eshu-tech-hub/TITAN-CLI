"""
Immutable models for the Broker Certification Framework.

All classes must be:
- JSON serializable
- Immutable
- Versioned
- Timestamped
- Devoid of broker-specific fields
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class CertificationSeverity(Enum):
    """Severity level of a certification scenario or failure."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class CertificationStatus(Enum):
    """Result status for a certification scenario or report."""

    PASS = "PASS"
    PASS_WITH_WARNINGS = "PASS_WITH_WARNINGS"
    PARTIAL = "PARTIAL"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True, slots=True)
class BrokerCertificationMetadata:
    """Metadata regarding the certification process."""

    broker_id: str
    certification_version: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    environment: str = "PAPER"
    framework_version: str = "1.0.0"


@dataclass(frozen=True, slots=True)
class BrokerCapability:
    """Defines a specific capability supported by the broker."""

    capability_id: str
    name: str
    description: str
    is_supported: bool
    requires_approval: bool = False
    limitations: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class BrokerCapabilityMatrix:
    """Matrix of capabilities for a given broker."""

    broker_id: str
    timestamp: datetime
    capabilities: tuple[BrokerCapability, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class BrokerCertificationScenario:
    """Definition of a canonical certification scenario."""

    scenario_id: str
    name: str
    description: str
    category: str
    severity: CertificationSeverity
    expected_behavior: str
    pass_criteria: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class BrokerValidationResult:
    """Result of a single validation step (e.g., interface check, capability check)."""

    validation_id: str
    description: str
    status: CertificationStatus
    details: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class BrokerCertificationResult:
    """Execution result for a specific certification scenario."""

    scenario: BrokerCertificationScenario
    status: CertificationStatus
    execution_time_ms: float
    timestamp: datetime
    message: str = ""
    error_details: str | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class BrokerCertificationSummary:
    """High-level summary of the certification run."""

    status: CertificationStatus
    total_scenarios: int
    passed_scenarios: int
    failed_scenarios: int
    skipped_scenarios: int
    partial_scenarios: int
    passed_with_warnings: int
    score_percentage: float
    critical_failures: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class BrokerCertificationReport:
    """Complete, immutable report for a broker certification run."""

    report_id: str
    metadata: BrokerCertificationMetadata
    summary: BrokerCertificationSummary
    capability_matrix: BrokerCapabilityMatrix
    scenario_results: tuple[BrokerCertificationResult, ...] = field(
        default_factory=tuple
    )
    validation_results: tuple[BrokerValidationResult, ...] = field(
        default_factory=tuple
    )
    warnings: tuple[str, ...] = field(default_factory=tuple)
    known_limitations: tuple[str, ...] = field(default_factory=tuple)
    recommendations: tuple[str, ...] = field(default_factory=tuple)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
