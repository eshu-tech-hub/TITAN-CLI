import pytest

from titan.analysis.factory import IndicatorFactory
from titan.analysis.indicators import EMA, RSI, SMA


def test_create_sma():
    indicator = IndicatorFactory.create("SMA", period=20)
    assert isinstance(indicator, SMA)


def test_create_ema():
    indicator = IndicatorFactory.create("EMA", period=20)
    assert isinstance(indicator, EMA)


def test_create_rsi():
    indicator = IndicatorFactory.create("RSI", period=14)
    assert isinstance(indicator, RSI)


def test_unknown_indicator():
    with pytest.raises(ValueError):
        IndicatorFactory.create("XYZ")


def test_available():
    names = IndicatorFactory.available()

    assert "SMA" in names
    assert "EMA" in names
    assert "RSI" in names