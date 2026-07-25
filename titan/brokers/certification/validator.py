"""
Validation logic and the core Certification Engine for the framework.

Validators do NOT perform actual live operations or connect to brokers.
They inspect capabilities, interfaces, and expected behaviors.
"""

from typing import List, Any

from titan.brokers.certification.models import (
    BrokerValidationResult,
    CertificationStatus,
    BrokerCapability,
)
from titan.brokers.certification.scenarios import ALL_SCENARIOS


class CapabilityValidator:
    """Validates if a broker correctly defines its capabilities."""

    def validate(self, capabilities: List[BrokerCapability]) -> BrokerValidationResult:
        """Validates capability definitions."""
        if not capabilities:
            return BrokerValidationResult(
                validation_id="CAP_VAL_01",
                description="Check if capabilities are provided",
                status=CertificationStatus.FAIL,
                details="No capabilities provided.",
            )

        warnings = []
        for cap in capabilities:
            if not cap.capability_id or not cap.name:
                return BrokerValidationResult(
                    validation_id="CAP_VAL_02",
                    description="Check capability required fields",
                    status=CertificationStatus.FAIL,
                    details=f"Capability missing ID or name: {cap}",
                )
            if cap.is_supported and len(cap.limitations) > 5:
                warnings.append(f"Capability {cap.capability_id} has many limitations.")

        return BrokerValidationResult(
            validation_id="CAP_VAL_OK",
            description="Validate capability completeness",
            status=(
                CertificationStatus.PASS_WITH_WARNINGS
                if warnings
                else CertificationStatus.PASS
            ),
            details="Capabilities are well-defined.",
            warnings=tuple(warnings),
        )


class InterfaceValidator:
    """Validates if a broker implements the required interfaces correctly."""

    def validate(self, broker_instance: Any) -> BrokerValidationResult:
        """Validates that the broker implements all mandatory base methods."""
        required_methods = [
            "connect",
            "disconnect",
            "get_funds",
            "place_order",
            "cancel_order",
        ]
        missing = []
        for method in required_methods:
            if not hasattr(broker_instance, method) or not callable(
                getattr(broker_instance, method)
            ):
                missing.append(method)

        if missing:
            return BrokerValidationResult(
                validation_id="INT_VAL_01",
                description="Check required interfaces",
                status=CertificationStatus.FAIL,
                details=f"Missing required methods: {', '.join(missing)}",
            )

        return BrokerValidationResult(
            validation_id="INT_VAL_OK",
            description="Check required interfaces",
            status=CertificationStatus.PASS,
            details="All required methods are implemented.",
        )


class ScenarioValidator:
    """Validates scenario applicability for a given broker."""

    def validate(
        self, capabilities: List[BrokerCapability]
    ) -> List[BrokerValidationResult]:
        """Maps capabilities to scenarios and determines if they should be run."""
        results = []
        # This is a static validation ensuring the scenarios match declared capabilities
        # In a real implementation, this would map specific capabilities to scenario IDs

        supported_caps = {cap.capability_id for cap in capabilities if cap.is_supported}

        for scenario in ALL_SCENARIOS:
            # Simplified mock logic for mapping
            if "Orders" in scenario.category and "ORDERS" not in supported_caps:
                results.append(
                    BrokerValidationResult(
                        validation_id=f"SCEN_VAL_{scenario.scenario_id}",
                        description=f"Validate scenario {scenario.scenario_id} applicability",
                        status=CertificationStatus.NOT_APPLICABLE,
                        details="Broker does not support Order Management.",
                    )
                )
            else:
                results.append(
                    BrokerValidationResult(
                        validation_id=f"SCEN_VAL_{scenario.scenario_id}",
                        description=f"Validate scenario {scenario.scenario_id} applicability",
                        status=CertificationStatus.PASS,
                        details="Scenario is applicable.",
                    )
                )

        return results


class ComplianceValidator:
    """Validates compliance aspects like rate limiting configurations."""

    def validate(self, broker_instance: Any) -> BrokerValidationResult:
        """Validates broker compliance configurations."""
        if not hasattr(broker_instance, "rate_limit_calls"):
            return BrokerValidationResult(
                validation_id="COMP_VAL_01",
                description="Check rate limit configuration",
                status=CertificationStatus.PASS_WITH_WARNINGS,
                details="Broker instance does not explicitly define rate limits.",
                warnings=("No strict rate limits defined on broker instance.",),
            )

        return BrokerValidationResult(
            validation_id="COMP_VAL_OK",
            description="Check rate limit configuration",
            status=CertificationStatus.PASS,
            details="Rate limit configuration present.",
        )


class CertificationEngine:
    """Core engine that orchestrates validators to assess a broker."""

    def __init__(self):
        from titan.brokers.certification.adapters import (
            BrokerInterfaceComplianceChecker,
        )

        self.capability_validator = CapabilityValidator()
        self.interface_checker = BrokerInterfaceComplianceChecker()
        self.scenario_validator = ScenarioValidator()
        self.compliance_validator = ComplianceValidator()

    def run_validations(
        self, broker_instance: Any, capabilities: List[BrokerCapability]
    ) -> List[BrokerValidationResult]:
        """Runs all passive validators against the broker."""
        results = []

        results.append(self.capability_validator.validate(capabilities))

        # BrokerInterfaceComplianceChecker returns bool. Wrap it into a ValidationResult
        is_compliant = self.interface_checker.check_compliance(broker_instance)
        results.append(
            BrokerValidationResult(
                validation_id="INT_VAL_COMPLIANCE",
                description="Interface Compliance Check",
                status=(
                    CertificationStatus.PASS
                    if is_compliant
                    else CertificationStatus.FAIL
                ),
                details=(
                    "Broker interface is compliant."
                    if is_compliant
                    else "Broker interface violates requirements."
                ),
            )
        )

        scenario_results = self.scenario_validator.validate(capabilities)
        results.extend(scenario_results)

        results.append(self.compliance_validator.validate(broker_instance))

        return results
