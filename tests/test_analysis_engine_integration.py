from datetime import datetime

from titan.analysis.engine import AnalysisEngine
from titan.market.models import Candle
from titan.market.series import MarketDataSeries


def make_series():
    candles = []

    for i in range(1, 31):
        candles.append(
            Candle(
                timestamp=datetime.now(),
                open=i,
                high=i,
                low=i,
                close=i,
                volume=1000,
            )
        )

    return MarketDataSeries(candles)


def test_complete_analysis():

    engine = AnalysisEngine()

    engine.add_indicator("SMA", period=20)
    engine.add_indicator("EMA", period=20)
    engine.add_indicator("RSI", period=14)

    report = engine.analyze(
        symbol="NIFTY",
        timeframe="15m",
        data=make_series(),
    )

    assert report.symbol == "NIFTY"
    assert report.timeframe == "15m"
    assert report.has("SMA")
    assert report.has("EMA")
    assert report.has("RSI")

    assert report.get("SMA") is not None
    assert report.get("EMA") is not None
    assert report.get("RSI") is not None