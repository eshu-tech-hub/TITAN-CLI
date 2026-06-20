from titan.analysis.indicators import EMA, RSI, SMA


class IndicatorFactory:
    """
    Factory for creating indicator instances.
    """

    _registry = {
        "SMA": SMA,
        "EMA": EMA,
        "RSI": RSI,
    }

    @classmethod
    def create(cls, name: str, **kwargs):
        try:
            indicator_class = cls._registry[name.upper()]
        except KeyError:
            raise ValueError(f"Unknown indicator: {name}")

        return indicator_class(**kwargs)

    @classmethod
    def available(cls):
        return sorted(cls._registry.keys())