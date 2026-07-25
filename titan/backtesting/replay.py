from dataclasses import dataclass, field
from decimal import Decimal

from titan.backtesting.clock import SimulationClock
from titan.backtesting.dataset import HistoricalDataset
from titan.backtesting.exceptions import ReplayError
from titan.backtesting.models import BacktestBar, HistoricalBar
from titan.market.models import Candle as MarketCandle
from titan.market.series import MarketDataSeries


@dataclass(slots=True)
class ReplayEngine:
    """Replays historical data chronologically through the TITAN pipeline.

    Advances one bar at a time, converting historical data into the
    formats expected by the pipeline and paper broker. No look-ahead
    bias by construction — only the current and past bars are exposed.

    Attributes:
        dataset: The historical dataset to replay.
        clock: Simulation clock controlling time progression.
        _current_bar: The current bar being replayed.
    """

    dataset: HistoricalDataset
    clock: SimulationClock = field(default_factory=SimulationClock)
    _current_bar: BacktestBar | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        if not self.dataset.bars:
            raise ReplayError("Dataset has no bars to replay.")

        self.clock.initialize(
            total_bars=len(self.dataset.bars),
            start_time=self.dataset.start_time,
            bar_times=[b.timestamp for b in self.dataset.bars],
        )

    @property
    def current_bar(self) -> BacktestBar | None:
        """The current bar being replayed."""
        return self._current_bar

    @property
    def current_index(self) -> int:
        """Current bar index in the replay."""
        return self.clock.current_index

    @property
    def is_at_end(self) -> bool:
        """Whether the replay has reached the end of data."""
        return self.clock.is_at_end

    @property
    def progress(self) -> float:
        """Replay progress as a ratio (0.0 to 1.0)."""
        return self.clock.progress

    def start(self) -> BacktestBar:
        """Begin replay from the first bar.

        Returns:
            The first BacktestBar.

        Raises:
            ReplayError: If already started.
        """
        if self._current_bar is not None:
            raise ReplayError("Replay has already started. Use advance() to continue.")
        return self._build_bar(0)

    def advance(self) -> BacktestBar | None:
        """Advance to the next bar in the replay.

        Returns:
            The next BacktestBar, or None if at the end of data.

        Raises:
            ReplayError: If advance is called before start().
        """
        if self._current_bar is None:
            raise ReplayError("Replay has not started. Call start() before advance().")
        if not self.clock.next_bar():
            return None
        return self._build_bar(self.clock.current_index)

    def seek(self, index: int) -> BacktestBar:
        """Seek to a specific bar index.

        Args:
            index: Target bar index.

        Returns:
            The BacktestBar at the given index.
        """
        self.clock.seek(index)
        return self._build_bar(index)

    def reset(self) -> None:
        """Reset the replay engine to its initial state."""
        self.clock.reset()
        self._current_bar = None

    def get_market_data(self) -> MarketDataSeries:
        """Get the current bar as a MarketDataSeries for the pipeline.

        Returns:
            A MarketDataSeries containing only the current bar.
        """
        if self._current_bar is None:
            return MarketDataSeries(candles=[])
        return self._bar_to_market_series(self._current_bar)

    def get_bars_since(self, lookback: int) -> MarketDataSeries:
        """Get a window of recent bars as a MarketDataSeries.

        Args:
            lookback: Number of past bars to include (including current).

        Returns:
            A MarketDataSeries with the lookback window.
        """
        start_idx = max(0, self.clock.current_index - lookback + 1)
        candles: list[MarketCandle] = []
        for i in range(start_idx, self.clock.current_index + 1):
            historical = self.dataset.bars[i]
            candles.append(
                MarketCandle(
                    timestamp=historical.timestamp,
                    open=float(historical.open),
                    high=float(historical.high),
                    low=float(historical.low),
                    close=float(historical.close),
                    volume=historical.volume,
                )
            )
        return MarketDataSeries(candles=candles)

    def _build_bar(self, index: int) -> BacktestBar:
        """Build a BacktestBar from dataset at the given index."""
        historical = self.dataset.bars[index]
        timestamp = historical.timestamp

        bar = BacktestBar(
            bar=historical,
            symbol=self.dataset.symbol,
            exchange=self.dataset.exchange,
            option_snapshots=tuple(self.dataset.option_snapshots.get(timestamp, [])),
            news_snapshots=tuple(self.dataset.news_snapshots.get(timestamp, [])),
            event_snapshots=tuple(self.dataset.event_snapshots.get(timestamp, [])),
        )
        self._current_bar = bar
        return bar

    @staticmethod
    def _bar_to_market_series(bar: BacktestBar) -> MarketDataSeries:
        """Convert a BacktestBar to a single-candle MarketDataSeries."""
        h = bar.bar
        candle = MarketCandle(
            timestamp=h.timestamp,
            open=float(h.open),
            high=float(h.high),
            low=float(h.low),
            close=float(h.close),
            volume=h.volume,
        )
        return MarketDataSeries(candles=[candle])

    @staticmethod
    def historical_bar_to_market(bar: HistoricalBar) -> MarketCandle:
        """Convert a HistoricalBar to a market-layer Candle.

        Args:
            bar: Historical bar with Decimal prices.

        Returns:
            Market layer Candle with float prices.
        """
        return MarketCandle(
            timestamp=bar.timestamp,
            open=float(bar.open),
            high=float(bar.high),
            low=float(bar.low),
            close=float(bar.close),
            volume=bar.volume,
        )

    @staticmethod
    def current_price(bar: BacktestBar) -> Decimal:
        """Get the current price from a BacktestBar.

        Uses the close price as the current trading price.
        """
        return bar.bar.close
