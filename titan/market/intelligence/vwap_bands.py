"""VWAP Bands Analyzer.

Computes VWAP deviation bands that serve as dynamic support/resistance
levels and volatility context.

No broker imports.
No API calls.
"""

import math

from titan.market.intelligence.models import VWAPBands
from titan.market.series import MarketDataSeries

DEFAULT_DEVIATIONS = 2.0
MIN_CANDLES = 5
BAND_CONFIDENCE_HIGH = 0.7
BAND_CONFIDENCE_LOW = 0.3


class VWAPBandsAnalyzer:
    """Analyse VWAP deviation bands.

    Consumes MarketDataSeries and a pre-computed VWAP array to calculate
    upper and lower deviation bands, current deviation multiple, and
    bandwidth. Bands serve as dynamic support/resistance.
    """

    name = "VWAPBandsAnalyzer"

    def analyze(
        self,
        series: MarketDataSeries,
        vwap_values: list[float],
        vwap_level: float,
        deviations: float = DEFAULT_DEVIATIONS,
    ) -> VWAPBands:
        """Compute VWAP deviation bands.

        Args:
            series: Market data series with OHLCV candles.
            vwap_values: Pre-computed per-candle VWAP values.
            vwap_level: The current session VWAP level.
            deviations: Number of standard deviations for bands.

        Returns:
            VWAP bands assessment.
        """

        reasons: list[str] = []

        if len(vwap_values) < MIN_CANDLES:
            return VWAPBands(
                confidence=0.0,
                reasons=(
                    (f"Insufficient data: need at least {MIN_CANDLES} "
                    f"candles, got {len(vwap_values)}."),
                ),
            )

        std_dev = self._compute_std_dev(series, vwap_values)

        upper = vwap_level + deviations * std_dev if std_dev > 0 else vwap_level
        lower = vwap_level - deviations * std_dev if std_dev > 0 else vwap_level

        current_deviation = self._current_deviation(
            series.closes[-1], vwap_level, std_dev
        )
        bandwidth = (upper - lower) / vwap_level if vwap_level != 0 else 0.0
        confidence = self._confidence(
            n=len(vwap_values), std_dev=std_dev, vwap_level=vwap_level
        )

        reasons.extend(
            self._reasons(
                upper=upper,
                lower=lower,
                std_dev=std_dev,
                deviation_multiple=deviations,
                bandwidth=bandwidth,
            )
        )

        return VWAPBands(
            upper=upper,
            lower=lower,
            deviation=current_deviation,
            bandwidth=bandwidth,
            confidence=confidence,
            reasons=tuple(reasons),
        )

    def _compute_std_dev(
        self,
        series: MarketDataSeries,
        vwap_values: list[float],
    ) -> float:
        diffs = [c - v for c, v in zip(series.closes, vwap_values)]
        n = len(diffs)
        if n == 0:
            return 0.0
        mean = sum(diffs) / n
        variance = sum((d - mean) ** 2 for d in diffs) / n
        return math.sqrt(variance)

    def _current_deviation(
        self,
        current_close: float,
        vwap_level: float,
        std_dev: float,
    ) -> float:
        if std_dev == 0:
            return 0.0
        return (current_close - vwap_level) / std_dev

    def _confidence(
        self,
        n: int,
        std_dev: float,
        vwap_level: float,
    ) -> float:
        if n < MIN_CANDLES:
            return 0.0
        sample_factor = min(1.0, n / 20)
        if vwap_level == 0:
            return sample_factor * BAND_CONFIDENCE_LOW
        relative_std = std_dev / vwap_level
        spread_factor = min(1.0, relative_std * 10)
        return min(1.0, sample_factor * (BAND_CONFIDENCE_LOW + 0.7 * spread_factor))

    def _reasons(
        self,
        upper: float,
        lower: float,
        std_dev: float,
        deviation_multiple: float,
        bandwidth: float,
    ) -> list[str]:
        reasons: list[str] = []

        reasons.append(
            f"Upper band at {upper:.2f} ({deviation_multiple:.1f} deviations)."
        )
        reasons.append(
            f"Lower band at {lower:.2f} ({deviation_multiple:.1f} deviations)."
        )
        reasons.append(f"Standard deviation: {std_dev:.4f}.")
        reasons.append(f"Bandwidth: {bandwidth:.4f} ({bandwidth * 100:.2f}%).")

        return reasons
