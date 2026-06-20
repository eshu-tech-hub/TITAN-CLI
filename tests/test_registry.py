import pytest

from titan.analysis.base import Indicator
from titan.analysis.models import IndicatorResult
from titan.analysis.registry import IndicatorRegistry
from titan.market.models import Candle


class DummyIndicator(Indicator):

    @property
    def name(self) -> str:
        return "Dummy"

    def calculate(self, candles: list[Candle]) -> IndicatorResult:
        return IndicatorResult(
            name=self.name,
            value=100.0,
        )


def test_register_indicator():

    registry = IndicatorRegistry()

    indicator = DummyIndicator()

    registry.register(indicator)

    assert registry.get("Dummy") is indicator


def test_list_indicators():

    registry = IndicatorRegistry()

    registry.register(DummyIndicator())

    assert registry.list() == ["Dummy"]


def test_clear_registry():

    registry = IndicatorRegistry()

    registry.register(DummyIndicator())

    registry.clear()

    assert registry.list() == []


def test_missing_indicator():

    registry = IndicatorRegistry()

    with pytest.raises(KeyError):
        registry.get("RSI")