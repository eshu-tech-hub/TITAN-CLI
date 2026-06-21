from abc import ABC, abstractmethod

from titan.analysis.models import IndicatorResult
from titan.market.models import Candle


class Indicator(ABC):
    """
    Base class for all technical indicators.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the indicator name."""

    @abstractmethod
    def calculate(self, candles: list[Candle]) -> IndicatorResult:
        """
        Calculate the indicator value.
        """
