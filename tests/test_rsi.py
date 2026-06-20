from datetime import datetime

import pytest

from titan.analysis.indicators import RSI
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


def test_rsi_returns_float():
    series = make_series(
        [44, 45, 46, 44, 43, 45, 48, 50, 49, 51, 53, 55, 54, 56, 58]
    )

    indicator = RSI(period=14)
    result = indicator.calculate(series)

    assert isinstance(result.value, float)


def test_rsi_range():
    series = make_series(
        [44, 45, 46, 44, 43, 45, 48, 50, 49, 51, 53, 55, 54, 56, 58]
    )

    indicator = RSI(period=14)
    result = indicator.calculate(series)

    assert 0 <= result.value <= 100


def test_invalid_period():
    with pytest.raises(ValueError):
        RSI(0)