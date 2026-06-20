from datetime import datetime

import pytest

from titan.analysis.indicators import EMA
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


def test_ema_returns_float():

    series = make_series([10, 20, 30, 40, 50])

    indicator = EMA(period=5)

    result = indicator.calculate(series)

    assert isinstance(result.value, float)


def test_invalid_period():

    with pytest.raises(ValueError):
        EMA(0)


def test_not_enough_data():

    series = make_series([10, 20])

    indicator = EMA(period=5)

    with pytest.raises(ValueError):
        indicator.calculate(series)