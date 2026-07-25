"""
Report generation for the Broker Certification Framework.

Produces immutable matrices and final certification reports.
"""

from typing import List, Optional
from datetime import datetime, timezone

from titan.brokers.certification.models import (
    BrokerCapability,
    BrokerCapabilityMatrix,
    BrokerCertificationReport,
    BrokerCertificationSummary,
    BrokerCertificationMetadata,
    BrokerCertificationResult,
    BrokerValidationResult,
    CertificationStatus,
    CertificationSeverity,
)


class BrokerCapabilityMatrixBuilder:
    """Builds the immutable capability matrix from individual capabilities."""

    def __init__(self, broker_id: str):
        self._broker_id = broker_id
        self._capabilities: List[BrokerCapability] = []

    def add_capability(
        self, capability: BrokerCapability
    ) -> "BrokerCapabilityMatrixBuilder":
        """Adds a capability to the matrix."""
        self._capabilities.append(capability)
        return self

    def build(self) -> BrokerCapabilityMatrix:
        """Constructs and returns the immutable BrokerCapabilityMatrix."""
        return BrokerCapabilityMatrix(
            broker_id=self._broker_id,
            timestamp=datetime.now(timezone.utc),
            capabilities=tuple(self._capabilities),
        )


class CertificationReportBuilder:
    """Builds the final immutable certification report."""

    def __init__(self, report_id: str, broker_id: str, environment: str = "PAPER"):
        self._report_id = report_id
        self._metadata = BrokerCertificationMetadata(
            broker_id=broker_id,
            environment=environment,
            certification_version="1.0",
        )
        self._capability_matrix: Optional[BrokerCapabilityMatrix] = None
        self._scenario_results: List[BrokerCertificationResult] = []
        self._validation_results: List[BrokerValidationResult] = []
        self._warnings: List[str] = []
        self._known_limitations: List[str] = []
        self._recommendations: List[str] = []

    def set_capability_matrix(
        self, matrix: BrokerCapabilityMatrix
    ) -> "CertificationReportBuilder":
        """Sets the capability matrix for the report."""
        self._capability_matrix = matrix
        return self

    def add_scenario_result(
        self, result: BrokerCertificationResult
    ) -> "CertificationReportBuilder":
        """Adds a scenario execution result."""
        self._scenario_results.append(result)
        if (
            result.status == CertificationStatus.FAIL
            and result.scenario.severity == CertificationSeverity.CRITICAL
        ):
            self.add_warning(f"Critical failure in scenario: {result.scenario.name}")
        return self

    def add_validation_result(
        self, result: BrokerValidationResult
    ) -> "CertificationReportBuilder":
        """Adds a static validation result."""
        self._validation_results.append(result)
        if result.status == CertificationStatus.FAIL:
            self.add_warning(f"Validation failure: {result.description}")
        return self

    def add_warning(self, warning: str) -> "CertificationReportBuilder":
        """Adds a general warning."""
        if warning not in self._warnings:
            self._warnings.append(warning)
        return self

    def add_known_limitation(self, limitation: str) -> "CertificationReportBuilder":
        """Adds a known limitation to the report."""
        self._known_limitations.append(limitation)
        return self

    def add_recommendation(self, recommendation: str) -> "CertificationReportBuilder":
        """Adds a recommendation to the report."""
        self._recommendations.append(recommendation)
        return self

    def _calculate_summary(self) -> BrokerCertificationSummary:
        """Calculates the overall summary and final status."""
        total = len(self._scenario_results)
        passed = sum(
            1 for r in self._scenario_results if r.status == CertificationStatus.PASS
        )
        failed = sum(
            1 for r in self._scenario_results if r.status == CertificationStatus.FAIL
        )
        skipped = sum(
            1
            for r in self._scenario_results
            if r.status == CertificationStatus.NOT_APPLICABLE
        )
        partial = sum(
            1 for r in self._scenario_results if r.status == CertificationStatus.PARTIAL
        )
        passed_with_warnings = sum(
            1
            for r in self._scenario_results
            if r.status == CertificationStatus.PASS_WITH_WARNINGS
        )

        critical_failures = sum(
            1
            for r in self._scenario_results
            if r.status == CertificationStatus.FAIL
            and r.scenario.severity == CertificationSeverity.CRITICAL
        )

        score = 0.0
        applicable_scenarios = total - skipped
        if applicable_scenarios > 0:
            # Simple scoring logic
            score = (
                (passed + (passed_with_warnings * 0.9) + (partial * 0.5))
                / applicable_scenarios
            ) * 100.0

        if critical_failures > 0 or score < 50.0:
            final_status = CertificationStatus.FAIL
        elif failed > 0:
            final_status = CertificationStatus.PARTIAL
        elif passed_with_warnings > 0 or partial > 0:
            final_status = CertificationStatus.PASS_WITH_WARNINGS
        else:
            final_status = CertificationStatus.PASS

        return BrokerCertificationSummary(
            status=final_status,
            total_scenarios=total,
            passed_scenarios=passed,
            failed_scenarios=failed,
            skipped_scenarios=skipped,
            partial_scenarios=partial,
            passed_with_warnings=passed_with_warnings,
            score_percentage=round(score, 2),
            critical_failures=critical_failures,
        )

    def build(self) -> BrokerCertificationReport:
        """Constructs and returns the final immutable report."""
        if not self._capability_matrix:
            raise ValueError(
                "Capability matrix must be set before building the report."
            )

        summary = self._calculate_summary()

        return BrokerCertificationReport(
            report_id=self._report_id,
            metadata=self._metadata,
            summary=summary,
            capability_matrix=self._capability_matrix,
            scenario_results=tuple(self._scenario_results),
            validation_results=tuple(self._validation_results),
            warnings=tuple(self._warnings),
            known_limitations=tuple(self._known_limitations),
            recommendations=tuple(self._recommendations),
        )
