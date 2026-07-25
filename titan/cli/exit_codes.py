"""CLI exit code constants.

Standardized exit codes for all TITAN CLI commands.
Follows Unix convention: 0 = success, 1-2 = usage error, 3-125 = runtime errors.
"""

from __future__ import annotations

SUCCESS: int = 0
USAGE_ERROR: int = 1
CONFIG_ERROR: int = 2
RUNTIME_ERROR: int = 3
NETWORK_ERROR: int = 4
AUTH_ERROR: int = 5
DEPLOYMENT_ERROR: int = 6
HEALTH_CHECK_FAILED: int = 7
BACKUP_FAILED: int = 8
AUDIT_ERROR: int = 9
REPORT_ERROR: int = 10
TIMEOUT: int = 11
DEPENDENCY_MISSING: int = 50
INTERRUPTED: int = 130
