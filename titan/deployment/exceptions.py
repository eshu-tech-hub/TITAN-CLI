from __future__ import annotations


class DeploymentError(Exception):
    """Base exception for deployment framework errors."""


class EnvironmentError(DeploymentError):
    """Environment validation or resolution failed."""


class StartupError(DeploymentError):
    """Startup sequence failed."""


class ShutdownError(DeploymentError):
    """Shutdown sequence failed."""


class ValidationError(DeploymentError):
    """Production validation failed."""


class HealthCheckError(DeploymentError):
    """Health check evaluation failed."""


class BackupError(DeploymentError):
    """Backup operation failed."""


class RestoreError(DeploymentError):
    """Restore operation failed."""


class ServiceError(DeploymentError):
    """Service management operation failed."""
