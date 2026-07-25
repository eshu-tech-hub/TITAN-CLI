from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class ValidationLevel(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """A single validation finding."""

    level: ValidationLevel
    category: str
    message: str
    component: Optional[str] = None
    resolution: Optional[str] = None


@dataclass(frozen=True, slots=True)
class ConfigurationReport:
    """Aggregated report of all configuration validation checks."""

    is_valid: bool
    results: tuple[ValidationResult, ...] = field(default_factory=tuple)

    @property
    def blocking_errors(self) -> List[ValidationResult]:
        return [r for r in self.results if r.level == ValidationLevel.ERROR]

    @property
    def warnings(self) -> List[ValidationResult]:
        return [r for r in self.results if r.level == ValidationLevel.WARNING]

    @property
    def recommendations(self) -> List[ValidationResult]:
        return [r for r in self.results if r.level == ValidationLevel.INFO]


class ValidationSeverity(str, Enum):
    """Severity level of a validation issue."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """A single issue detected during validation."""

    component: str
    severity: ValidationSeverity
    message: str


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """Immutable report containing all pre-flight check results."""

    issues: tuple[ValidationIssue, ...] = field(default_factory=tuple)

    @property
    def is_valid(self) -> bool:
        """Return False if there are any CRITICAL issues."""
        return not any(
            issue.severity == ValidationSeverity.CRITICAL for issue in self.issues
        )

    @property
    def critical_issues(self) -> tuple[ValidationIssue, ...]:
        return tuple(
            issue
            for issue in self.issues
            if issue.severity == ValidationSeverity.CRITICAL
        )

    @property
    def warnings(self) -> tuple[ValidationIssue, ...]:
        return tuple(
            issue
            for issue in self.issues
            if issue.severity == ValidationSeverity.WARNING
        )
