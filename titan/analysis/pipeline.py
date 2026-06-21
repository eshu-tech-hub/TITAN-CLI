from titan.analysis.base import Indicator
from titan.analysis.report import AnalysisReport
from titan.market.series import MarketDataSeries


class IndicatorPipeline:
    """
    Executes a sequence of indicators and produces an AnalysisReport.
    """

    def __init__(self):
        self._indicators: list[Indicator] = []

    def add(self, indicator: Indicator) -> None:
        self._indicators.append(indicator)

    def run(
        self,
        symbol: str,
        timeframe: str,
        data: MarketDataSeries,
    ) -> AnalysisReport:
        from datetime import datetime

        report = AnalysisReport(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=datetime.now(),
        )

        for indicator in self._indicators:
            result = indicator.calculate(data)
            report.add(result)

        return report

    @property
    def indicators(self):
        return tuple(self._indicators)
