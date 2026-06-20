from titan.analysis.models import IndicatorResult
from titan.analysis.period_indicator import PeriodIndicator
from titan.market.series import MarketDataSeries


class SMA(PeriodIndicator):
    """
    Simple Moving Average.
    """

    @property
    def name(self) -> str:
        return "SMA"

    def calculate(self, data: MarketDataSeries) -> IndicatorResult:
        self.validate_data(data)

        closes = data.closes
        value = sum(closes[-self.period :]) / self.period

        return IndicatorResult(
            name=self.name,
            value=value,
        )