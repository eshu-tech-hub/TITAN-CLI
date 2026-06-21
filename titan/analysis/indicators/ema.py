from titan.analysis.models import IndicatorResult
from titan.analysis.period_indicator import PeriodIndicator
from titan.market.series import MarketDataSeries


class EMA(PeriodIndicator):
    """
    Exponential Moving Average.
    """

    @property
    def name(self) -> str:
        return "EMA"

    def calculate(self, data: MarketDataSeries) -> IndicatorResult:
        self.validate_data(data)

        closes = data.closes

        multiplier = 2 / (self.period + 1)

        ema = sum(closes[: self.period]) / self.period

        for price in closes[self.period :]:
            ema = (price - ema) * multiplier + ema

        return IndicatorResult(
            name=self.name,
            value=ema,
        )
