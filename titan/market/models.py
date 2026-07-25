from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class HistoricalCandle(Protocol):
    """Interface for one broker-normalized historical OHLCV candle."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@runtime_checkable
class SymbolIdentifier(Protocol):
    """Interface for a broker-independent tradable instrument identity."""

    @property
    def exchange(self) -> str: ...
    @property
    def ticker(self) -> str: ...


@dataclass(frozen=True, slots=True)
class Symbol:
    """Broker-independent tradable instrument.

    Attributes:
        exchange: Exchange or venue code, such as NSE or NASDAQ.
        ticker: Exchange-level ticker or trading symbol.
        instrument_token: Optional provider-specific identifier.
        name: Optional human-readable instrument name.
    """

    exchange: str
    ticker: str
    instrument_token: str | None = None
    name: str | None = None


@dataclass(slots=True)
class Candle:
    """Represents one normalized OHLCV candle.

    Attributes:
        timestamp: Candle timestamp.
        open: Opening price.
        high: Highest traded price.
        low: Lowest traded price.
        close: Closing price.
        volume: Traded quantity.
    """

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
