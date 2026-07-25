class PaperTradingError(Exception):
    """Base exception for paper trading errors."""


class PaperOrderError(PaperTradingError):
    """Raised when order placement or management fails in paper mode."""


class PaperFillError(PaperTradingError):
    """Raised when fill simulation fails."""


class PaperPortfolioError(PaperTradingError):
    """Raised when portfolio operations fail."""


class PaperJournalError(PaperTradingError):
    """Raised when trade journal operations fail."""


class PaperPerformanceError(PaperTradingError):
    """Raised when performance computation fails."""


class PaperPositionError(PaperTradingError):
    """Raised when position tracking operations fail."""
