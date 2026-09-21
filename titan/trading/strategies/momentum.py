"""Momentum strategy — indicator engine vectorised via polars.

EMA and RSI are computed in a single polars DataFrame pipeline using
``ewm_mean(span=..., adjust=False)`` for O(n) Rust-level performance.
The final-row values are extracted with ``df.row(-1, named=True)`` and
injected into the ``TradeSignal.metadata`` dict for TUI and router use.
"""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl

from titan.market.series import MarketDataSeries
from titan.trading.strategies.base import SignalType, Strategy, TradeSignal


@dataclass
class MomentumStrategy(Strategy):
    """Momentum strategy using fast/slow EMAs and RSI.

    All indicators are computed via polars vectorised expressions,
    replacing the previous Python for-loop implementations.

    Attributes:
        fast_period: Span for the fast EMA (default 9).
        slow_period:  Span for the slow EMA (default 21).
        rsi_period:   Span for the RSI EWM smoothing (default 14).
        stop_loss_pct:   Stop-loss distance as a fraction of price.
        take_profit_pct: Take-profit distance as a fraction of price.
    """

    fast_period: int = 9
    slow_period: int = 21
    rsi_period: int = 14
    stop_loss_pct: float = 0.015
    take_profit_pct: float = 0.03

    def _build_indicators(self, closes: list[float]) -> dict[str, float]:
        """Compute EMA(fast), EMA(slow), RSI in one polars pipeline.

        Returns a dict with the *last-row* values for each indicator,
        ready to be consumed by ``generate_signal`` and packed into
        ``TradeSignal.metadata``.
        """
        df = pl.DataFrame({"close": closes})

        # ── EMA (exponential weighted mean, pandas-compatible) ────────────
        df = df.with_columns(
            [
                pl.col("close")
                .ewm_mean(span=self.fast_period, adjust=False)
                .alias("ema_fast"),
                pl.col("close")
                .ewm_mean(span=self.slow_period, adjust=False)
                .alias("ema_slow"),
            ]
        )

        # ── RSI via EWM gain/loss smoothing ──────────────────────────────
        delta = pl.col("close").diff()
        gain = (
            pl.when(delta > 0)
            .then(delta)
            .otherwise(0.0)
            .ewm_mean(span=self.rsi_period, adjust=False)
        )
        loss = (
            pl.when(delta < 0)
            .then(delta.abs())
            .otherwise(0.0)
            .ewm_mean(span=self.rsi_period, adjust=False)
        )
        rs = gain / loss
        df = df.with_columns(
            (100.0 - (100.0 / (1.0 + rs))).alias("rsi_14"),
        )

        # Extract final row as a named dict
        return df.row(-1, named=True)  # type: ignore[return-value]

    def generate_signal(self, data: MarketDataSeries) -> TradeSignal:
        """Analyse market data and generate a trade signal."""
        closes = data.closes

        if len(closes) < self.slow_period + 1:
            return TradeSignal(
                signal=SignalType.HOLD,
                symbol="",
                price=closes[-1] if closes else 0.0,
            )

        current_price = closes[-1]

        # Run entire indicator suite in one polars pass
        last = self._build_indicators(closes)

        ema_fast: float = last["ema_fast"]
        ema_slow: float = last["ema_slow"]
        rsi_14: float = last.get("rsi_14") or 50.0  # guard against NaN on short series

        # Previous-bar values for crossover detection
        prev = self._build_indicators(closes[:-1])
        prev_fast: float = prev["ema_fast"]
        prev_slow: float = prev["ema_slow"]

        meta = {
            "ema_fast": ema_fast,
            "ema_slow": ema_slow,
            "rsi_14": rsi_14,
            # Legacy key aliases for existing TUI/router consumers
            "fast_ema": ema_fast,
            "slow_ema": ema_slow,
            "rsi": rsi_14,
        }

        symbol = ""

        # BUY: fast crosses above slow AND RSI > 50
        if prev_fast <= prev_slow and ema_fast > ema_slow and rsi_14 > 50:
            sl = current_price * (1.0 - self.stop_loss_pct)
            tp = current_price * (1.0 + self.take_profit_pct)
            return TradeSignal(
                signal=SignalType.BUY,
                symbol=symbol,
                price=current_price,
                stop_loss=sl,
                take_profit=tp,
                metadata=meta,
            )

        # SELL / EXIT: fast crosses below slow OR RSI < 45
        if (prev_fast >= prev_slow and ema_fast < ema_slow) or rsi_14 < 45:
            sl = current_price * (1.0 + self.stop_loss_pct)
            tp = current_price * (1.0 - self.take_profit_pct)
            return TradeSignal(
                signal=SignalType.SELL,
                symbol=symbol,
                price=current_price,
                stop_loss=sl,
                take_profit=tp,
                metadata=meta,
            )

        return TradeSignal(
            signal=SignalType.HOLD,
            symbol=symbol,
            price=current_price,
            metadata=meta,
        )

