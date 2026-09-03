"""Pre-flight orchestration for TITAN OS boot sequence."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from titan.config.validation_models import ValidationReport
    from titan.config.validator import ConfigurationValidator

from titan.core.exceptions import ConfigurationError
from titan.core.logger import logger


class ProductionReadinessReview:
    """Executes strict pre-flight checks before allowing the RuntimeEngine to boot."""

    def __init__(self, validator: ConfigurationValidator | None = None) -> None:
        if validator is None:
            from titan.config.validator import ConfigurationValidator
            validator = ConfigurationValidator()
        self.validator = validator

    def run_pre_flight_checks(self) -> ValidationReport:
        """Run all readiness checks and fail-fast if critical issues are found."""
        logger.info("Initiating Production Readiness Review...")
        report = self.validator.validate_all()

        for warning in report.warnings:
            logger.warning(
                f"Pre-flight Warning [{warning.component}]: {warning.message}"
            )

        if not report.is_valid:
            for critical in report.critical_issues:
                logger.error(
                    f"Pre-flight CRITICAL [{critical.component}]: {critical.message}"
                )

            logger.error("Production Readiness Review FAILED. Boot sequence aborted.")
            raise ConfigurationError(
                "Pre-flight checks failed. Review logs for missing configurations or permissions."
            )

        logger.info("Production Readiness Review PASSED. System cleared for boot.")
        return report
