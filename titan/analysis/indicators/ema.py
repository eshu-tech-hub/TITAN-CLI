from titan.analysis.base import Indicator
from titan.analysis.models import IndicatorResult
from titan.market.series import MarketDataSeries


class EMA(Indicator):
    """
    Exponential Moving Average.
    """

    def __init__(self, period: int):
        if period <= 0:
            raise ValueError("Period must be greater than zero.")

        self.period = period

    @property
    def name(self) -> str:
        return "EMA"

    def calculate(self, data: MarketDataSeries) -> IndicatorResult:

        if len(data) < self.period:
            raise ValueError("Not enough candles.")

        closes = data.closes

        multiplier = 2 / (self.period + 1)

        ema = sum(closes[:self.period]) / self.period

        for price in closes[self.period:]:
            ema = (price - ema) * multiplier + ema

        return IndicatorResult(
            name=self.name,
            value=ema,
        )