from datetime import datetime

from titan.market.models import Candle
from titan.market.series import MarketDataSeries


def make_series():
    candles = [
        Candle(
            timestamp=datetime.now(),
            open=10,
            high=15,
            low=9,
            close=12,
            volume=100,
        ),
        Candle(
            timestamp=datetime.now(),
            open=12,
            high=18,
            low=11,
            close=17,
            volume=200,
        ),
    ]
    return MarketDataSeries(candles)


def test_length():
    series = make_series()
    assert len(series) == 2


def test_close_prices():
    series = make_series()
    assert series.closes == [12, 17]


def test_high_prices():
    series = make_series()
    assert series.highs == [15, 18]


def test_low_prices():
    series = make_series()
    assert series.lows == [9, 11]


def test_open_prices():
    series = make_series()
    assert series.opens == [10, 12]


def test_volumes():
    series = make_series()
    assert series.volumes == [100, 200]