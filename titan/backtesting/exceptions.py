class BacktestError(Exception):
    """Base exception for backtesting errors."""


class DatasetError(BacktestError):
    """Raised when historical dataset operations fail."""


class DatasetValidationError(DatasetError):
    """Raised when dataset validation fails."""


class ClockError(BacktestError):
    """Raised when simulation clock operations fail."""


class ReplayError(BacktestError):
    """Raised when replay operations fail."""


class EngineError(BacktestError):
    """Raised when backtest engine operations fail."""


class StatisticsError(BacktestError):
    """Raised when statistics computation fails."""


class MetricsError(BacktestError):
    """Raised when metrics computation fails."""
