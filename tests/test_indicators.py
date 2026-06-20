from datetime import datetime

from titan.analysis.indicators import ema, sma
from titan.market.models import Candle


def make_candles(prices):
    return [
        Candle(
            timestamp=datetime.now(),
            open=p,
            high=p,
            low=p,
            close=p,
            volume=1000,
        )
        for p in prices
    ]


def test_sma():
    candles = make_candles([10, 20, 30, 40, 50])

    assert sma(candles, 5) == 30


def test_ema():
    candles = make_candles([10, 20, 30, 40, 50])

    value = ema(candles, 5)

    assert isinstance(value, float)


def test_invalid_period():
    candles = make_candles([10, 20])

    try:
        sma(candles, 5)
        assert False
    except ValueError:
        assert True