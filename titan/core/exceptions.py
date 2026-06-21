class TitanError(Exception):
    """Base exception for TITAN."""


class ConfigurationError(TitanError):
    """Configuration-related errors."""


class AnalysisError(TitanError):
    """Analysis engine errors."""


class IndicatorError(AnalysisError):
    """Indicator calculation errors."""


class FactoryError(AnalysisError):
    """Indicator factory errors."""


class PipelineError(AnalysisError):
    """Pipeline execution errors."""


class MarketDataError(TitanError):
    """Market data validation errors."""


class BrokerError(TitanError):
    """Broker communication errors."""
