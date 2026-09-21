"""Relative Strength Index (RSI) — vectorised via polars."""

from __future__ import annotations

import polars as pl

from titan.analysis.models import IndicatorResult
from titan.analysis.period_indicator import PeriodIndicator
from titan.market.series import MarketDataSeries


class RSI(PeriodIndicator):
    """Relative Strength Index (RSI).

    Computes RSI using polars vectorised diff/clip expressions,
    eliminating the Python for-loop entirely. Wilder's initial
    simple average is used for the first period of gains/losses.
    """

    @property
    def name(self) -> str:
        return "RSI"

    def calculate(self, data: MarketDataSeries) -> IndicatorResult:
        self.validate_data(data)

        closes: pl.Series = pl.Series("close", data.closes, dtype=pl.Float64)

        # Vectorised price differences (drops the leading null automatically)
        delta: pl.Series = closes.diff().drop_nulls()

        # Separate gains (positive) and losses (absolute value of negative)
        gains: pl.Series = delta.clip(lower_bound=0.0)
        losses: pl.Series = (-delta).clip(lower_bound=0.0)

        # Wilder's simple average over the last `period` bars
        avg_gain: float = gains.tail(self.period).mean()  # type: ignore[assignment]
        avg_loss: float = losses.tail(self.period).mean()  # type: ignore[assignment]

        if avg_loss == 0.0:
            value = 100.0
        else:
            rs = avg_gain / avg_loss
            value = 100.0 - (100.0 / (1.0 + rs))

        return IndicatorResult(name=self.name, value=value)

