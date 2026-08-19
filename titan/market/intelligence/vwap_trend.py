"""VWAP Trend Analyzer.

Analyses VWAP slope, direction, and price interactions including
crossovers, reclaims, rejections, and pullbacks.

No broker imports.
No API calls.
"""

from titan.market.intelligence.models import TrendDirection, VWAPTrend
from titan.market.series import MarketDataSeries

TREND_LOOKBACK = 10
CROSSOVER_LOOKBACK = 3
RECLAIM_REJECT_LOOKBACK = 2
PULLBACK_LOOKBACK = 5
SLOPE_CONFIDENCE_HIGH = 0.7
SLOPE_CONFIDENCE_LOW = 0.3
DISTANCE_THRESHOLD = 0.001


class VWAPTrendAnalyzer:
    """Analyse VWAP trend and price interaction dynamics.

    Consumes MarketDataSeries and a pre-computed VWAP array to evaluate
    VWAP slope, direction, crossovers, reclaims, rejections, and pullbacks.
    """

    name = "VWAPTrendAnalyzer"

    def analyze(
        self,
        series: MarketDataSeries,
        vwap_values: list[float],
        vwap_level: float,
    ) -> VWAPTrend:
        """Determine VWAP trend characteristics.

        Args:
            series: Market data series with OHLCV candles.
            vwap_values: Pre-computed per-candle VWAP values.
            vwap_level: The current session VWAP level.

        Returns:
            VWAP trend assessment.
        """

        reasons: list[str] = []
        closes = series.closes

        if len(vwap_values) < TREND_LOOKBACK:
            return VWAPTrend(
                confidence=0.0,
                reasons=(
                    (f"Insufficient data: need {TREND_LOOKBACK} candles, "
                    f"got {len(vwap_values)}."),
                ),
            )

        slope = self._compute_slope(vwap_values)
        direction = self._direction(slope)
        crossover = self._detect_crossover(closes, vwap_values)
        reclaim = self._detect_reclaim(closes, vwap_values)
        rejection = self._detect_rejection(closes, vwap_values, vwap_level)
        pullback = self._detect_pullback(closes, vwap_level)
        confidence = self._confidence(slope, len(vwap_values))

        reasons.extend(
            self._reasons(
                slope=slope,
                direction=direction,
                crossover=crossover,
                reclaim=reclaim,
                rejection=rejection,
                pullback=pullback,
            )
        )

        return VWAPTrend(
            slope=slope,
            direction=direction,
            crossover=crossover,
            reclaim=reclaim,
            rejection=rejection,
            pullback=pullback,
            confidence=confidence,
            reasons=tuple(reasons),
        )

    def _compute_slope(self, vwap_values: list[float]) -> float:
        recent = vwap_values[-TREND_LOOKBACK:]
        n = len(recent)
        x_avg = (n - 1) / 2.0
        y_avg = sum(recent) / n

        num = sum((i - x_avg) * (v - y_avg) for i, v in enumerate(recent))
        den = sum((i - x_avg) ** 2 for i in range(n))

        if den == 0:
            return 0.0
        return num / den

    def _direction(self, slope: float) -> TrendDirection:
        if slope > DISTANCE_THRESHOLD:
            return TrendDirection.BULLISH
        if slope < -DISTANCE_THRESHOLD:
            return TrendDirection.BEARISH
        return TrendDirection.SIDEWAYS

    def _detect_crossover(
        self,
        closes: list[float],
        vwap_values: list[float],
    ) -> bool:
        if len(closes) < CROSSOVER_LOOKBACK:
            return False
        recent = CROSSOVER_LOOKBACK
        prev = closes[-(recent + 1)] - vwap_values[-(recent + 1)]
        curr = closes[-recent] - vwap_values[-recent]
        # Price crossed VWAP if signs differ (prev and curr have opposite
        # signs relative to VWAP)
        if prev * curr < 0:
            return True

        # Track remaining candles in lookback
        for i in range(-recent + 1, 0):
            p = closes[i - 1] - vwap_values[i - 1]
            c = closes[i] - vwap_values[i]
            if p * c < 0:
                return True
        return False

    def _detect_reclaim(
        self,
        closes: list[float],
        vwap_values: list[float],
    ) -> bool:
        if len(closes) < RECLAIM_REJECT_LOOKBACK + 2:
            return False
        recent_closes = closes[-(RECLAIM_REJECT_LOOKBACK + 1) :]
        recent_vwaps = vwap_values[-(RECLAIM_REJECT_LOOKBACK + 1) :]

        all_below = all(c < v for c, v in zip(recent_closes[:-1], recent_vwaps[:-1]))
        last_above = recent_closes[-1] > recent_vwaps[-1]

        return all_below and last_above

    def _detect_rejection(
        self,
        closes: list[float],
        vwap_values: list[float],
        vwap_level: float,
    ) -> bool:
        if len(closes) < RECLAIM_REJECT_LOOKBACK + 2:
            return False
        recent_closes = closes[-(RECLAIM_REJECT_LOOKBACK + 1) :]
        recent_vwaps = vwap_values[-(RECLAIM_REJECT_LOOKBACK + 1) :]

        all_above = all(c > v for c, v in zip(recent_closes[:-1], recent_vwaps[:-1]))
        last_below_or_at = recent_closes[-1] <= vwap_level * (1 + DISTANCE_THRESHOLD)

        return all_above and last_below_or_at

    def _detect_pullback(
        self,
        closes: list[float],
        vwap_level: float,
    ) -> bool:
        if len(closes) < PULLBACK_LOOKBACK:
            return False
        recent = closes[-PULLBACK_LOOKBACK:]

        max_dist = max(abs(c - vwap_level) for c in recent)
        final_dist = abs(recent[-1] - vwap_level)

        if max_dist < vwap_level * DISTANCE_THRESHOLD:
            return False

        return final_dist < vwap_level * DISTANCE_THRESHOLD

    def _confidence(
        self,
        slope: float,
        n: int,
    ) -> float:
        base = min(1.0, n / TREND_LOOKBACK)
        if abs(slope) >= SLOPE_CONFIDENCE_LOW:
            slope_factor = min(1.0, abs(slope) * 10)
            base = base * (0.5 + 0.5 * slope_factor)
        else:
            base = base * 0.3
        return min(1.0, base)

    def _reasons(
        self,
        slope: float,
        direction: TrendDirection,
        crossover: bool,
        reclaim: bool,
        rejection: bool,
        pullback: bool,
    ) -> list[str]:
        reasons: list[str] = []

        reasons.append(f"VWAP slope is {direction.value} ({slope:.6f}).")

        if crossover:
            reasons.append("VWAP crossover detected.")
        if reclaim:
            reasons.append(
                "VWAP reclaim detected — price moved from below to above VWAP."
            )
        if rejection:
            reasons.append("VWAP rejection detected — price reversed at VWAP.")
        if pullback:
            reasons.append(
                "VWAP pullback detected — price returned to VWAP from a distance."
            )

        if not any([crossover, reclaim, rejection, pullback]):
            reasons.append("No significant VWAP price interactions detected.")

        return reasons
