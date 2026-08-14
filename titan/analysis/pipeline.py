from titan.analysis.base import Indicator
from titan.analysis.report import AnalysisReport
from titan.market.series import MarketDataSeries


class IndicatorPipeline:
    """
    Executes a sequence of indicators and produces an AnalysisReport.
    """

    def __init__(self) -> None:
        self._indicators: list[Indicator] = []

    @property
    def indicators(self) -> list[Indicator]:
        """Read-only access to the indicator list."""
        return self._indicators

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
            timestamp=datetime.utcnow(),
        )

        for indicator in self._indicators:
            try:
                result = indicator.calculate(data)
                report.add(result)
            except Exception:
                pass

        return report
