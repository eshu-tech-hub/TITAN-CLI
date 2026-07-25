"""Volume Trend Analyzer.

Analyses volume slope, expansion, and contraction patterns.

No broker imports.
No API calls.
"""

from titan.market.intelligence.models import VolumeTrend
from titan.market.series import MarketDataSeries

TREND_LOOKBACK = 10
AVG_LOOKBACK = 5
MIN_CANDLES = 5
EXPANSION_THRESHOLD = 1.25
CONTRACTION_THRESHOLD = 0.75


class VolumeTrendAnalyzer:
    """Analyse volume trend, expansion, and contraction.

    Consumes MarketDataSeries to evaluate whether volume is rising,
    falling, expanding, or contracting over the lookback period.
    """

    name = "VolumeTrendAnalyzer"

    def analyze(
        self,
        series: MarketDataSeries,
    ) -> VolumeTrend:
        """Determine volume trend characteristics.

        Args:
            series: Market data series with OHLCV candles.

        Returns:
            Volume trend assessment.
        """

        reasons: list[str] = []
        volumes = series.volumes

        if len(volumes) < MIN_CANDLES:
            return VolumeTrend(
                confidence=0.0,
                reasons=(
                    f"Insufficient data: need at least {MIN_CANDLES} "
                    f"candles, got {len(volumes)}.",
                ),
            )

        slope = self._compute_slope(volumes)

        recent = volumes[-AVG_LOOKBACK:]
        prior = volumes[-(AVG_LOOKBACK + TREND_LOOKBACK) : -AVG_LOOKBACK]

        recent_avg = sum(recent) / len(recent) if recent else 0.0
        prior_avg = sum(prior) / len(prior) if prior else 0.0

        expansion_ratio = recent_avg / prior_avg if prior_avg > 0 else 1.0

        expanding = expansion_ratio >= EXPANSION_THRESHOLD
        contracting = expansion_ratio <= CONTRACTION_THRESHOLD

        confidence = self._confidence(volumes, slope, expansion_ratio)

        reasons.extend(
            self._reasons(
                slope=slope,
                expanding=expanding,
                contracting=contracting,
                expansion_ratio=expansion_ratio,
                recent_avg=recent_avg,
                prior_avg=prior_avg,
            )
        )

        return VolumeTrend(
            slope=slope,
            expanding=expanding,
            contracting=contracting,
            expansion_ratio=expansion_ratio,
            confidence=confidence,
            reasons=tuple(reasons),
        )

    def _compute_slope(self, volumes: list[int]) -> float:
        lookback = min(TREND_LOOKBACK, len(volumes))
        recent = volumes[-lookback:]
        n = len(recent)
        if n < 2:
            return 0.0
        x_avg = (n - 1) / 2.0
        y_avg = sum(recent) / n
        num = sum((i - x_avg) * (v - y_avg) for i, v in enumerate(recent))
        den = sum((i - x_avg) ** 2 for i in range(n))
        if den == 0:
            return 0.0
        return num / den

    def _confidence(
        self,
        volumes: list[int],
        slope: float,
        expansion_ratio: float,
    ) -> float:
        n = len(volumes)
        sample_factor = min(1.0, n / 20)

        if abs(expansion_ratio - 1.0) > 0.2:
            signal = 0.7
        else:
            signal = 0.3

        return min(1.0, sample_factor * (0.3 + 0.7 * signal))

    def _reasons(
        self,
        slope: float,
        expanding: bool,
        contracting: bool,
        expansion_ratio: float,
        recent_avg: float,
        prior_avg: float,
    ) -> list[str]:
        reasons: list[str] = []

        slope_dir = "rising" if slope > 0 else ("falling" if slope < 0 else "flat")
        reasons.append(f"Volume slope is {slope_dir} ({slope:.2f}).")

        if expanding:
            reasons.append(
                f"Volume expanding — recent avg ({recent_avg:.0f}) is "
                f"{expansion_ratio:.2f}x prior avg ({prior_avg:.0f})."
            )
        elif contracting:
            reasons.append(
                f"Volume contracting — recent avg ({recent_avg:.0f}) is "
                f"{expansion_ratio:.2f}x prior avg ({prior_avg:.0f})."
            )
        else:
            reasons.append(
                f"Volume is stable — recent avg ({recent_avg:.0f}), "
                f"prior avg ({prior_avg:.0f})."
            )

        return reasons
