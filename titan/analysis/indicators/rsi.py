from titan.analysis.models import IndicatorResult
from titan.analysis.period_indicator import PeriodIndicator
from titan.market.series import MarketDataSeries


class RSI(PeriodIndicator):
    """
    Relative Strength Index (RSI).
    """

    @property
    def name(self) -> str:
        return "RSI"

    def calculate(self, data: MarketDataSeries) -> IndicatorResult:
        self.validate_data(data)

        closes = data.closes

        gains = []
        losses = []

        for i in range(1, len(closes)):
            change = closes[i] - closes[i - 1]

            gains.append(max(change, 0))
            losses.append(abs(min(change, 0)))

        avg_gain = sum(gains[-self.period:]) / self.period
        avg_loss = sum(losses[-self.period:]) / self.period

        if avg_loss == 0:
            value = 100.0
        else:
            rs = avg_gain / avg_loss
            value = 100 - (100 / (1 + rs))

        return IndicatorResult(
            name=self.name,
            value=value,
        )