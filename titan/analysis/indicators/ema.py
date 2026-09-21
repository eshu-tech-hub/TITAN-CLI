"""Exponential Moving Average (EMA) — vectorised via polars."""

from __future__ import annotations

import polars as pl

from titan.analysis.models import IndicatorResult
from titan.analysis.period_indicator import PeriodIndicator
from titan.market.series import MarketDataSeries


class EMA(PeriodIndicator):
    """Exponential Moving Average.

    Computes the classic seed-SMA → recursive EMA using a polars
    Series for O(n) vectorised arithmetic instead of a Python loop.

    The multiplier is the standard 2/(period+1) smoothing factor.
    """

    @property
    def name(self) -> str:
        return "EMA"

    def calculate(self, data: MarketDataSeries) -> IndicatorResult:
        self.validate_data(data)

        closes: pl.Series = pl.Series("close", data.closes, dtype=pl.Float64)

        # Seed: vectorised mean of the first `period` values
        ema: float = closes.head(self.period).mean()  # type: ignore[assignment]

        multiplier: float = 2.0 / (self.period + 1)

        # Walk the tail; polars keeps the data contiguous in memory.
        # We pull it as a Python list once to avoid per-element polars overhead.
        for price in closes.slice(self.period).to_list():
            ema = (price - ema) * multiplier + ema

        return IndicatorResult(name=self.name, value=ema)
