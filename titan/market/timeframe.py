from __future__ import annotations

from enum import Enum


class Timeframe(str, Enum):
    """Canonical candle intervals supported by the market data layer."""

    ONE_MINUTE = "1m"
    THREE_MINUTES = "3m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    ONE_HOUR = "1h"
    ONE_DAY = "1d"
    ONE_WEEK = "1w"
    ONE_MONTH = "1mo"

    @classmethod
    def from_value(cls, value: str | "Timeframe") -> "Timeframe":
        """Return a timeframe from a canonical enum or string value.

        Args:
            value: Existing timeframe enum or canonical string value.

        Raises:
            ValueError: If the value is not a supported timeframe.
        """

        if isinstance(value, cls):
            return value
        return cls(value)
