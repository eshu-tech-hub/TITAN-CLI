from titan.analysis.base import Indicator


class IndicatorRegistry:
    """
    Registry for all technical indicators.
    """

    def __init__(self) -> None:
        self._indicators: dict[str, Indicator] = {}

    def register(self, indicator: Indicator) -> None:
        """
        Register an indicator.
        """
        self._indicators[indicator.name] = indicator

    def get(self, name: str) -> Indicator:
        """
        Get an indicator by name.
        """
        if name not in self._indicators:
            raise KeyError(f"Indicator '{name}' is not registered.")

        return self._indicators[name]

    def list(self) -> list[str]:
        """
        Return a sorted list of registered indicators.
        """
        return sorted(self._indicators.keys())

    def clear(self) -> None:
        """
        Remove all registered indicators.
        """
        self._indicators.clear()