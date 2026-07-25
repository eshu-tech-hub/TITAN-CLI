import sys
from unittest.mock import patch

import pytest

from titan.config.validation_models import (
    ValidationIssue,
    ValidationReport,
    ValidationSeverity,
)
from titan.config.validator import ConfigurationValidator
from titan.core.exceptions import ConfigurationError
from titan.core.readiness import ProductionReadinessReview


def test_validation_report_logic():
    """Verify the report correctly identifies critical failures."""
    clean_report = ValidationReport(issues=())
    assert clean_report.is_valid is True

    warning_issue = ValidationIssue("Test", ValidationSeverity.WARNING, "Warning")
    warning_report = ValidationReport(issues=(warning_issue,))
    assert warning_report.is_valid is True

    critical_issue = ValidationIssue("Test", ValidationSeverity.CRITICAL, "Fatal")
    critical_report = ValidationReport(issues=(warning_issue, critical_issue))
    assert critical_report.is_valid is False
    assert len(critical_report.critical_issues) == 1


def test_python_version_validator():
    """Ensure older Python versions trigger a critical failure."""
    validator = ConfigurationValidator()

    # Mock a Python 3.10 environment
    with patch.object(sys, "version_info", (3, 10)):
        issues = validator.validate_environment()
        assert len(issues) > 0
        assert issues[0].severity == ValidationSeverity.CRITICAL
        assert "Python 3.14+ required" in issues[0].message


def test_readiness_review_success():
    """Ensure a clean report permits boot."""
    review = ProductionReadinessReview()

    with patch.object(
        ConfigurationValidator, "validate_all", return_value=ValidationReport(issues=())
    ):
        report = review.run_pre_flight_checks()
        assert report.is_valid is True


def test_readiness_review_fail_fast():
    """Ensure critical issues correctly abort the boot sequence."""
    review = ProductionReadinessReview()
    critical_issue = ValidationIssue(
        "Core", ValidationSeverity.CRITICAL, "Fatal Setup Error"
    )

    with patch.object(
        ConfigurationValidator,
        "validate_all",
        return_value=ValidationReport(issues=(critical_issue,)),
    ):
        with pytest.raises(ConfigurationError, match="Pre-flight checks failed"):
            review.run_pre_flight_checks()
