from abc import ABC, abstractmethod

from titan.analysis.models import IndicatorResult
from titan.market.series import MarketDataSeries


class Indicator(ABC):
    """
    Base class for all technical indicators.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the indicator name."""

    @abstractmethod
    def calculate(self, data: "MarketDataSeries") -> IndicatorResult:
        """
        Calculate the indicator value.
        """
