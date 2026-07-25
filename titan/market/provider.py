from abc import ABC, abstractmethod
from datetime import datetime
from typing import Sequence

from titan.market.models import Candle, Symbol
from titan.market.timeframe import Timeframe


class MarketDataProvider(ABC):
    """Abstract contract implemented by broker or vendor data adapters."""

    @abstractmethod
    def get_historical_candles(
        self,
        symbol: Symbol,
        timeframe: Timeframe,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
    ) -> Sequence[Candle]:
        """Fetch normalized historical candles.

        Args:
            symbol: Broker-independent instrument identity.
            timeframe: Canonical candle interval.
            start: Optional inclusive start timestamp.
            end: Optional inclusive end timestamp.
            limit: Optional maximum number of candles to return.

        Returns:
            A sequence of normalized candles ordered by time.
        """
