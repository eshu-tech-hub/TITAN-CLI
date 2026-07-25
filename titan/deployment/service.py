from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from titan.deployment.exceptions import ValidationError
from titan.deployment.models import EnvironmentReport


class ProductionValidator:
    """Pre-flight validation for production deployments.

    Validates configuration, secrets, directories, permissions,
    Python version, dependencies, and broker configuration before
    allowing TITAN to enter production mode.
    """

    def __init__(self, root_dir: str | Path | None = None) -> None:
        self._root = Path(root_dir) if root_dir else Path.cwd()

    def validate_all(self, report: EnvironmentReport) -> list[str]:
        """Run all production validations. Returns list of error messages."""
        errors: list[str] = []

        if not report.python_version_ok:
            errors.append("Python version does not meet minimum requirement")

        if not report.dependencies_ok:
            errors.append("Required dependencies are missing")

        if not report.config_valid:
            errors.extend(
                f"Config: {e}" for e in report.errors if "config" in e.lower()
            )

        if not report.directories_verified:
            errors.append("Required directories are missing or inaccessible")

        perm_errors = self._check_permissions()
        errors.extend(perm_errors)

        return errors

    def validate_strict(self, report: EnvironmentReport) -> None:
        """Raise ValidationError if any production check fails."""
        errors = self.validate_all(report)
        if errors:
            raise ValidationError(
                f"Production validation failed ({len(errors)} error(s)): "
                + "; ".join(errors[:5])
            )

    def _check_permissions(self) -> list[str]:
        errors: list[str] = []

        log_dir = self._root / "logs"
        if log_dir.exists() and not os.access(str(log_dir), os.W_OK):
            errors.append(f"Log directory is not writable: {log_dir}")

        data_dir = self._root / "data"
        if data_dir.exists() and not os.access(str(data_dir), os.W_OK):
            errors.append(f"Data directory is not writable: {data_dir}")

        return errors

    def check_disk_space(self, min_mb: int = 500) -> bool:
        """Check if sufficient disk space is available."""
        try:
            import shutil

            usage = shutil.disk_usage(str(self._root))
            free_mb = usage.free // (1024 * 1024)
            return free_mb >= min_mb
        except OSError:
            return False

    def check_port_available(self, port: int) -> bool:
        """Check if a network port is available."""
        import socket

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("", port))
                return True
            except OSError:
                return False

    def generate_validation_report(self, report: EnvironmentReport) -> dict[str, Any]:
        """Generate a detailed validation report as a dictionary."""
        errors = self.validate_all(report)
        return {
            "valid": len(errors) == 0,
            "environment": report.environment.value,
            "python_ok": report.python_version_ok,
            "dependencies_ok": report.dependencies_ok,
            "config_loaded": report.config_loaded,
            "config_valid": report.config_valid,
            "secrets_available": report.secrets_available,
            "directories_verified": report.directories_verified,
            "broker_configured": report.broker_configured,
            "disk_space_ok": self.check_disk_space(),
            "errors": errors,
            "warnings": list(report.warnings),
        }
