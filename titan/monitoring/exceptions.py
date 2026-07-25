class MonitoringError(Exception):
    """Base exception for monitoring and telemetry errors."""


class MonitoringInputError(MonitoringError, ValueError):
    """Invalid input to a monitoring component."""


class MonitoringCollectionError(MonitoringError):
    """Metric collection failed."""


class MonitoringStorageError(MonitoringError):
    """Metric storage or snapshot retrieval failed."""


class MonitoringHealthError(MonitoringError):
    """Health evaluation or reporting failed."""


class MonitoringDashboardError(MonitoringError):
    """Dashboard generation or update failed."""


class MonitoringExportError(MonitoringError):
    """Metric export to an external system failed."""
