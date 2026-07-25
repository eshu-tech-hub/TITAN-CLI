from typing import Type
from titan.analysis.base import Indicator
from titan.analysis.indicators import EMA, RSI, SMA


class IndicatorFactory:
    """
    Factory for creating indicator instances.
    """

    _registry: dict[str, Type[Indicator]] = {
        "SMA": SMA,
        "EMA": EMA,
        "RSI": RSI,
    }

    @classmethod
    def create(cls, name: str, **kwargs) -> Indicator:
        try:
            indicator_class = cls._registry[name.upper()]
        except KeyError:
            raise ValueError(f"Unknown indicator: {name}")

        return indicator_class(**kwargs)

    @classmethod
    def available(cls) -> list[str]:
        return sorted(cls._registry.keys())
