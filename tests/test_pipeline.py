from datetime import datetime

from titan.analysis.indicators import EMA, RSI, SMA
from titan.analysis.pipeline import IndicatorPipeline
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


def test_pipeline():
    data = make_series(
        [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29]
    )

    pipeline = IndicatorPipeline()

    pipeline.add(SMA(5))
    pipeline.add(EMA(5))
    pipeline.add(RSI(14))

    report = pipeline.run(
        symbol="TEST",
        timeframe="1D",
        data=data,
    )

    assert report.has("SMA")
    assert report.has("EMA")
    assert report.has("RSI")


def test_pipeline_count():
    pipeline = IndicatorPipeline()

    pipeline.add(SMA(5))
    pipeline.add(EMA(5))

    assert len(pipeline.indicators) == 2
