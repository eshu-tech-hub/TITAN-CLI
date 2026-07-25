from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Iterator

from titan.backtesting.exceptions import DatasetValidationError
from titan.backtesting.models import (
    EventSnapshot,
    HistoricalBar,
    NewsSnapshot,
    OptionSnapshot,
)
from titan.brokers.models import Candle, Exchange


@dataclass(slots=True)
class HistoricalDataset:
    """Container for historical market data used in backtesting.

    Stores OHLCV bars along with optional option chain, news,
    and event snapshots indexed by timestamp. Provides validation
    and conversion helpers.

    Attributes:
        symbol: Trading symbol.
        exchange: Exchange.
        bars: Ordered historical OHLCV bars (must be ascending by timestamp).
        option_snapshots: Option chain snapshots keyed by timestamp.
        news_snapshots: News snapshots keyed by timestamp.
        event_snapshots: Event snapshots keyed by timestamp.
    """

    symbol: str
    exchange: Exchange
    bars: list[HistoricalBar] = field(default_factory=list)
    option_snapshots: dict[datetime, list[OptionSnapshot]] = field(default_factory=dict)
    news_snapshots: dict[datetime, list[NewsSnapshot]] = field(default_factory=dict)
    event_snapshots: dict[datetime, list[EventSnapshot]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if not self.symbol:
            raise DatasetValidationError("Symbol must not be empty.")
        if not isinstance(self.exchange, Exchange):
            raise DatasetValidationError("Exchange must be a valid Exchange.")
        if not self.bars:
            raise DatasetValidationError("Dataset must contain at least one bar.")

        for i, bar in enumerate(self.bars):
            if bar.open < Decimal("0") or bar.high < Decimal("0"):
                raise DatasetValidationError(f"Negative price at bar index {i}: {bar}")
            if bar.low < Decimal("0") or bar.close < Decimal("0"):
                raise DatasetValidationError(f"Negative price at bar index {i}: {bar}")
            if bar.high < bar.low:
                raise DatasetValidationError(f"High < Low at bar index {i}: {bar}")
            if bar.open < Decimal("0") or bar.close < Decimal("0"):
                raise DatasetValidationError(f"Negative price at bar index {i}: {bar}")
            if bar.volume < 0:
                raise DatasetValidationError(f"Negative volume at bar index {i}: {bar}")

            if i > 0 and bar.timestamp <= self.bars[i - 1].timestamp:
                raise DatasetValidationError(
                    f"Bars must be in ascending chronological order "
                    f"at index {i}: {bar.timestamp} <= "
                    f"{self.bars[i - 1].timestamp}"
                )

    def __len__(self) -> int:
        return len(self.bars)

    def __iter__(self) -> Iterator[HistoricalBar]:
        return iter(self.bars)

    def __getitem__(self, index: int) -> HistoricalBar:
        return self.bars[index]

    @property
    def start_time(self) -> datetime:
        """Earliest timestamp in the dataset."""
        return self.bars[0].timestamp if self.bars else datetime.min

    @property
    def end_time(self) -> datetime:
        """Latest timestamp in the dataset."""
        return self.bars[-1].timestamp if self.bars else datetime.min

    @property
    def bar_count(self) -> int:
        """Number of bars in the dataset."""
        return len(self.bars)

    @property
    def closes(self) -> list[Decimal]:
        """List of closing prices."""
        return [b.close for b in self.bars]

    @property
    def highs(self) -> list[Decimal]:
        """List of high prices."""
        return [b.high for b in self.bars]

    @property
    def lows(self) -> list[Decimal]:
        """List of low prices."""
        return [b.low for b in self.bars]

    @property
    def opens(self) -> list[Decimal]:
        """List of open prices."""
        return [b.open for b in self.bars]

    @property
    def volumes(self) -> list[int]:
        """List of volumes."""
        return [b.volume for b in self.bars]

    @staticmethod
    def from_broker_candles(
        symbol: str,
        exchange: Exchange,
        candles: list[Candle],
    ) -> "HistoricalDataset":
        """Create a dataset from broker-layer Candle objects.

        Args:
            symbol: Trading symbol.
            exchange: Exchange.
            candles: List of broker Candle objects (must be ordered).

        Returns:
            A new HistoricalDataset instance.

        Raises:
            DatasetValidationError: If candle data is invalid.
        """
        bars: list[HistoricalBar] = []
        for c in candles:
            bars.append(
                HistoricalBar(
                    timestamp=c.datetime,
                    open=c.open,
                    high=c.high,
                    low=c.low,
                    close=c.close,
                    volume=c.volume,
                    open_interest=c.oi,
                )
            )
        return HistoricalDataset(symbol=symbol, exchange=exchange, bars=bars)

    def to_broker_candles(self) -> list[Candle]:
        """Convert bars to broker-layer Candle objects.

        Returns:
            List of broker Candle objects.
        """
        return [
            Candle(
                datetime=b.timestamp,
                open=b.open,
                high=b.high,
                low=b.low,
                close=b.close,
                volume=b.volume,
                oi=b.open_interest,
            )
            for b in self.bars
        ]

    def resample(self, interval_minutes: int) -> "HistoricalDataset":
        """Resample bars to a larger timeframe (future-ready).

        Args:
            interval_minutes: Target interval in minutes.

        Returns:
            A new HistoricalDataset with resampled bars.
        """
        if interval_minutes <= 0:
            raise DatasetValidationError("Interval must be positive.")
        if not self.bars:
            return HistoricalDataset(
                symbol=self.symbol, exchange=self.exchange, bars=[]
            )

        resampled: list[HistoricalBar] = []
        group: list[HistoricalBar] = [self.bars[0]]

        for bar in self.bars[1:]:
            diff_minutes = (bar.timestamp - group[0].timestamp).total_seconds() / 60.0
            if diff_minutes < interval_minutes:
                group.append(bar)
            else:
                resampled.append(self._merge_group(group))
                group = [bar]

        if group:
            resampled.append(self._merge_group(group))

        return HistoricalDataset(
            symbol=self.symbol,
            exchange=self.exchange,
            bars=resampled,
        )

    @staticmethod
    def _merge_group(group: list[HistoricalBar]) -> HistoricalBar:
        """Merge a group of bars into a single OHLCV bar."""
        return HistoricalBar(
            timestamp=group[0].timestamp,
            open=group[0].open,
            high=max(b.high for b in group),
            low=min(b.low for b in group),
            close=group[-1].close,
            volume=sum(b.volume for b in group),
            open_interest=group[-1].open_interest,
        )
