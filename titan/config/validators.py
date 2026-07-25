import os
import sys
from pathlib import Path
from typing import List

from titan.config.manager import ConfigManager
from titan.config.validation_models import (
    ConfigurationReport,
    ValidationLevel,
    ValidationResult,
)


class EnvironmentValidator:
    @staticmethod
    def validate() -> List[ValidationResult]:
        results: List[ValidationResult] = []
        # Python version check
        if sys.version_info < (3, 14):
            results.append(
                ValidationResult(
                    level=ValidationLevel.ERROR,
                    category="Environment",
                    message=f"Python 3.14+ required, found {sys.version_info[0]}.{sys.version_info[1]}",
                    component="python",
                    resolution="Upgrade Python to version 3.14 or higher.",
                )
            )
        return results


class DirectoryValidator:
    @staticmethod
    def validate(config_manager: ConfigManager) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        # Check required directories exist and are writable
        # Use paths from config manager
        titan_home = Path(os.getenv("TITAN_HOME", Path.home() / ".titan"))
        required_dirs = ["config", "logs", "data", "reports", "checkpoints"]

        for dir_name in required_dirs:
            dir_path = titan_home / dir_name
            if not dir_path.exists():
                results.append(
                    ValidationResult(
                        level=ValidationLevel.WARNING,
                        category="Storage",
                        message=f"Required directory does not exist: {dir_path}",
                        component="directories",
                        resolution="Directory will be created on startup.",
                    )
                )
            elif not os.access(dir_path, os.W_OK):
                results.append(
                    ValidationResult(
                        level=ValidationLevel.ERROR,
                        category="Storage",
                        message=f"Directory is not writable: {dir_path}",
                        component="directories",
                        resolution="Check file permissions.",
                    )
                )
        return results


class ConfigurationValidator:
    """Master validator that orchestrates all sub-validators."""

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager

    def validate_all(self) -> ConfigurationReport:
        results: List[ValidationResult] = []

        results.extend(EnvironmentValidator.validate())
        results.extend(DirectoryValidator.validate(self.config_manager))

        # Add basic profile validation
        active_profile = self.config_manager.profile
        if not active_profile:
            results.append(
                ValidationResult(
                    level=ValidationLevel.ERROR,
                    category="Configuration",
                    message="No active configuration profile found.",
                    component="profiles",
                    resolution="Create or activate a configuration profile.",
                )
            )

        has_errors = any(r.level == ValidationLevel.ERROR for r in results)

        return ConfigurationReport(is_valid=not has_errors, results=tuple(results))
