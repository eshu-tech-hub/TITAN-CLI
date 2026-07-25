class AlertingError(Exception):
    """Base exception for alerting and notification errors."""


class AlertingInputError(AlertingError, ValueError):
    """Invalid input to an alerting component."""


class AlertingRuleError(AlertingError):
    """Alert rule evaluation or configuration failed."""


class AlertingEngineError(AlertingError):
    """Alert engine operation failed."""


class AlertingChannelError(AlertingError):
    """Notification channel operation failed."""


class AlertingDispatchError(AlertingError):
    """Alert dispatch to a channel failed."""


class AlertingHistoryError(AlertingError):
    """Alert history storage or retrieval failed."""
