from dataclasses import dataclass
from typing import Iterator

from titan.market.models import Candle


@dataclass(slots=True)
class MarketDataSeries:
    """
    Standardized market data container.

    This class wraps a sequence of Candle objects and provides
    a consistent interface for indicators, strategies, scanners,
    and future analysis engines.
    """

    candles: list[Candle]

    def __len__(self) -> int:
        return len(self.candles)

    def __iter__(self) -> Iterator[Candle]:
        return iter(self.candles)

    @property
    def closes(self) -> list[float]:
        return [c.close for c in self.candles]

    @property
    def highs(self) -> list[float]:
        return [c.high for c in self.candles]

    @property
    def lows(self) -> list[float]:
        return [c.low for c in self.candles]

    @property
    def opens(self) -> list[float]:
        return [c.open for c in self.candles]

    @property
    def volumes(self) -> list[float]:
        return [c.volume for c in self.candles]
