"""Simple Moving Average (SMA) — vectorised via polars."""

from __future__ import annotations

import polars as pl

from titan.analysis.models import IndicatorResult
from titan.analysis.period_indicator import PeriodIndicator
from titan.market.series import MarketDataSeries


class SMA(PeriodIndicator):
    """Simple Moving Average.

    Computes the mean of the last `period` close prices using a single
    polars vectorised expression rather than a Python sum/division.
    """

    @property
    def name(self) -> str:
        return "SMA"

    def calculate(self, data: MarketDataSeries) -> IndicatorResult:
        self.validate_data(data)

        closes: pl.Series = pl.Series("close", data.closes, dtype=pl.Float64)

        # Single vectorised op: tail(period).mean()
        value: float = closes.tail(self.period).mean()  # type: ignore[assignment]

        return IndicatorResult(name=self.name, value=value)

