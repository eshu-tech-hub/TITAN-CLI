from dataclasses import dataclass, field
from datetime import datetime

from titan.backtesting.exceptions import ClockError


@dataclass(slots=True)
class SimulationClock:
    """Controls time progression during a backtest simulation.

    Supports pause, resume, seek, and step operations.
    Tracks the current position within a range of bar indices.

    Attributes:
        _current_index: Index of the current bar.
        _total_bars: Total number of bars in the simulation.
        _paused: Whether the clock is paused.
        _start_time: Start timestamp of the simulation.
        _current_time: Current simulation timestamp.
        _bar_times: List of bar timestamps for time lookups.
    """

    _current_index: int = 0
    _total_bars: int = 0
    _paused: bool = False
    _start_time: datetime | None = field(default=None)
    _current_time: datetime | None = field(default=None)
    _bar_times: list[datetime] = field(default_factory=list)

    def initialize(
        self,
        total_bars: int,
        start_time: datetime,
        bar_times: list[datetime],
    ) -> None:
        """Initialize the clock for a simulation run.

        Args:
            total_bars: Total number of bars to simulate.
            start_time: Timestamp of the first bar.
            bar_times: List of all bar timestamps for navigation.

        Raises:
            ClockError: If parameters are invalid.
        """
        if total_bars <= 0:
            raise ClockError("Total bars must be positive.")
        if not bar_times:
            raise ClockError("Bar times list must not be empty.")
        if len(bar_times) != total_bars:
            raise ClockError(
                f"Bar times length ({len(bar_times)}) "
                f"must equal total bars ({total_bars})."
            )

        self._current_index = 0
        self._total_bars = total_bars
        self._paused = False
        self._start_time = start_time
        self._current_time = start_time
        self._bar_times = list(bar_times)

    @property
    def current_index(self) -> int:
        """Current bar index (0-based)."""
        return self._current_index

    @property
    def current_time(self) -> datetime | None:
        """Current simulation timestamp."""
        return self._current_time

    @property
    def start_time(self) -> datetime | None:
        """Start timestamp of the simulation."""
        return self._start_time

    @property
    def is_paused(self) -> bool:
        """Whether the clock is paused."""
        return self._paused

    @property
    def is_at_end(self) -> bool:
        """Whether the clock has reached the end of data."""
        return self._current_index >= self._total_bars - 1

    @property
    def progress(self) -> float:
        """Simulation progress as a ratio (0.0 to 1.0)."""
        if self._total_bars <= 1:
            return 1.0
        return self._current_index / (self._total_bars - 1)

    def next_bar(self) -> bool:
        """Advance to the next bar.

        Returns:
            True if there are more bars, False if at the end.

        Raises:
            ClockError: If already at the end.
        """
        if self._paused:
            return True
        if self._current_index >= self._total_bars - 1:
            return False
        self._current_index += 1
        self._current_time = self._bar_times[self._current_index]
        return True

    def previous_bar(self) -> bool:
        """Go back to the previous bar.

        Returns:
            True if successful, False if already at the first bar.
        """
        if self._current_index <= 0:
            return False
        self._current_index -= 1
        self._current_time = self._bar_times[self._current_index]
        return True

    def seek(self, index: int) -> None:
        """Seek to a specific bar index.

        Args:
            index: Target bar index.

        Raises:
            ClockError: If index is out of range.
        """
        if index < 0 or index >= self._total_bars:
            raise ClockError(f"Index {index} out of range [0, {self._total_bars - 1}].")
        self._current_index = index
        self._current_time = self._bar_times[index]

    def pause(self) -> None:
        """Pause the clock."""
        self._paused = True

    def resume(self) -> None:
        """Resume the clock."""
        self._paused = False

    def reset(self) -> None:
        """Reset the clock to its initial state."""
        self._current_index = 0
        self._paused = False
        self._current_time = self._start_time
