from datetime import datetime

from titan.analysis.engine import AnalysisEngine
from titan.market.models import Candle
from titan.market.series import MarketDataSeries


def make_series(prices):
    candles = [
        Candle(
            timestamp=datetime.now(),
            open=p,
            high=p,
            low=p,
            close=p,
            volume=100,
        )
        for p in prices
    ]
    return MarketDataSeries(candles)


def test_analysis_engine():

    engine = AnalysisEngine()

    engine.add_indicator("SMA", period=5)
    engine.add_indicator("EMA", period=5)
    engine.add_indicator("RSI", period=14)

    report = engine.analyze(
        symbol="NIFTY",
        timeframe="15m",
        data=make_series(
            [
                10,
                11,
                12,
                13,
                14,
                15,
                16,
                17,
                18,
                19,
                20,
                21,
                22,
                23,
                24,
                25,
                26,
                27,
                28,
                29,
            ]
        ),
    )

    assert report.has("SMA")
    assert report.has("EMA")
    assert report.has("RSI")
