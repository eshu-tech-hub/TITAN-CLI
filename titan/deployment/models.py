from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum


class DeploymentEnvironment(StrEnum):
    """Supported deployment environments."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PAPER_TRADING = "paper"
    BACKTESTING = "backtesting"
    PRODUCTION = "production"


class DeploymentStatus(StrEnum):
    """Lifecycle status of the deployment."""

    INITIALIZING = "initializing"
    VALIDATING = "validating"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    RECOVERING = "recovering"


class SubsystemStatus(StrEnum):
    """Health status of a deployment subsystem."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    OFFLINE = "offline"


@dataclass(frozen=True, slots=True)
class VersionInfo:
    """Complete version fingerprint for a TITAN build."""

    version: str = "1.0.0"
    build_number: str = ""
    git_commit: str = ""
    git_branch: str = ""
    build_timestamp: str = ""
    python_version: str = ""
    platform: str = ""
    machine: str = ""


@dataclass(frozen=True, slots=True)
class EnvironmentReport:
    """Snapshot of the resolved deployment environment."""

    environment: DeploymentEnvironment = DeploymentEnvironment.DEVELOPMENT
    config_loaded: bool = False
    config_valid: bool = False
    secrets_available: bool = False
    directories_verified: bool = False
    python_version_ok: bool = False
    dependencies_ok: bool = False
    broker_configured: bool = False
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True, slots=True)
class StartupStep:
    """Record of a single startup step."""

    name: str
    success: bool
    duration_ms: float = 0.0
    message: str = ""


@dataclass(frozen=True, slots=True)
class StartupReport:
    """Report generated after the startup sequence completes."""

    success: bool = False
    steps: tuple[StartupStep, ...] = ()
    total_duration_ms: float = 0.0
    environment: DeploymentEnvironment = DeploymentEnvironment.DEVELOPMENT
    version: str = ""
    errors: tuple[str, ...] = ()
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True, slots=True)
class SubsystemHealth:
    """Health record for a single subsystem."""

    name: str
    status: SubsystemStatus = SubsystemStatus.UNKNOWN
    message: str = ""
    latency_ms: float = 0.0
    last_check: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True, slots=True)
class DeploymentHealthReport:
    """Aggregated health report across all subsystems."""

    overall_status: SubsystemStatus = SubsystemStatus.UNKNOWN
    subsystems: tuple[SubsystemHealth, ...] = ()
    uptime_seconds: float = 0.0
    readiness: bool = False
    liveness: bool = False
    startup_complete: bool = False
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True, slots=True)
class BackupManifest:
    """Manifest describing a backup operation."""

    backup_id: str
    timestamp: datetime
    components: tuple[str, ...]
    total_files: int = 0
    total_size_bytes: int = 0
    destination: str = ""
    success: bool = True
    errors: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DeploymentReport:
    """Top-level deployment status report."""

    status: DeploymentStatus = DeploymentStatus.STOPPED
    environment: DeploymentEnvironment = DeploymentEnvironment.DEVELOPMENT
    version: VersionInfo = field(default_factory=VersionInfo)
    uptime_seconds: float = 0.0
    start_time: datetime | None = None
    health: DeploymentHealthReport = field(default_factory=DeploymentHealthReport)
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
