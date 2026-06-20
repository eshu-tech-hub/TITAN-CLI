from titan.analysis.base import Indicator
from titan.analysis.models import IndicatorResult
from titan.market.series import MarketDataSeries


class SMA(Indicator):
    """
    Simple Moving Average indicator.
    """

    def __init__(self, period: int):
        if period <= 0:
            raise ValueError("Period must be greater than zero.")
        self.period = period

    @property
    def name(self) -> str:
        return "SMA"

    def calculate(self, data: MarketDataSeries) -> IndicatorResult:
        if len(data) < self.period:
            raise ValueError("Not enough candles.")

        closes = data.closes
        value = sum(closes[-self.period:]) / self.period

        return IndicatorResult(
            name=self.name,
            value=value,
        )