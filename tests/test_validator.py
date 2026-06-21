from datetime import datetime

import pytest

from titan.market.models import Candle
from titan.market.validator import validate_candles


def test_valid_candles():

    candles = [
        Candle(
            timestamp=datetime.now(),
            open=100,
            high=110,
            low=95,
            close=105,
            volume=1000,
        )
    ]

    validate_candles(candles)


def test_empty_candle_list():

    with pytest.raises(ValueError):
        validate_candles([])


def test_invalid_high_low():

    candles = [
        Candle(
            timestamp=datetime.now(),
            open=100,
            high=90,
            low=95,
            close=92,
            volume=1000,
        )
    ]

    with pytest.raises(ValueError):
        validate_candles(candles)
