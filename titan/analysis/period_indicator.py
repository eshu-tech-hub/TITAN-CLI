from abc import ABC

from titan.analysis.base import Indicator
from titan.market.series import MarketDataSeries


class PeriodIndicator(Indicator, ABC):
    """
    Base class for indicators that require a period.
    """

    def __init__(self, period: int):
        if period <= 0:
            raise ValueError("Period must be greater than zero.")

        self.period = period

    def validate_data(self, data: MarketDataSeries) -> None:
        """
        Validate sufficient data exists.
        """
        if len(data) < self.period:
            raise ValueError(
                f"Indicator requires at least {self.period} candles."
            )