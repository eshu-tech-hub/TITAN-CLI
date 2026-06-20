from titan.analysis.factory import IndicatorFactory
from titan.analysis.pipeline import IndicatorPipeline
from titan.analysis.report import AnalysisReport
from titan.market.series import MarketDataSeries


class AnalysisEngine:
    """
    Executes a complete technical analysis.
    """

    def __init__(self):
        self.pipeline = IndicatorPipeline()

    def add_indicator(self, name: str, **kwargs):
        indicator = IndicatorFactory.create(name, **kwargs)
        self.pipeline.add(indicator)

    def analyze(
        self,
        symbol: str,
        timeframe: str,
        data: MarketDataSeries,
    ) -> AnalysisReport:

        return self.pipeline.run(
            symbol=symbol,
            timeframe=timeframe,
            data=data,
        )