from datetime import datetime

import pytest

from titan.analysis.indicators import SMA
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


def test_sma_value():
    series = make_series([10, 20, 30, 40, 50])

    indicator = SMA(period=5)

    result = indicator.calculate(series)

    assert result.value == 30.0


def test_invalid_period():
    with pytest.raises(ValueError):
        SMA(0)


def test_not_enough_data():
    series = make_series([10, 20])

    indicator = SMA(period=5)

    with pytest.raises(ValueError):
        indicator.calculate(series)