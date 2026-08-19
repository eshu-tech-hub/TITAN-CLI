"""Trend Analyzer.

Determines primary and secondary market trend direction and strength
from supplied MarketDataSeries.

No broker imports.
No API calls.
"""

from titan.market.intelligence.models import TrendDirection, TrendStructure
from titan.market.series import MarketDataSeries

SHORT_PERIOD = 20
LONG_PERIOD = 50
ABOVE_SMA_THRESHOLD = 1.005
BELOW_SMA_THRESHOLD = 0.995
STRENGTH_HIGH = 0.7
STRENGTH_MODERATE = 0.5
STRENGTH_LOW = 0.3


class TrendAnalyzer:
    """Analyse market trend from price data.

    Consumes MarketDataSeries to determine primary (longer-term) and
    secondary (shorter-term) trend direction and strength using moving
    average price position and slope.
    """

    name = "TrendAnalyzer"

    def analyze(
        self,
        series: MarketDataSeries,
        short_period: int = SHORT_PERIOD,
        long_period: int = LONG_PERIOD,
    ) -> TrendStructure:
        """Determine market trend.

        Args:
            series: Market data series with OHLCV candles.
            short_period: Period for secondary (short-term) trend.
            long_period: Period for primary (long-term) trend.

        Returns:
            Trend structure assessment.
        """

        reasons: list[str] = []

        if len(series) < long_period:
            return TrendStructure(
                primary=TrendDirection.UNKNOWN,
                secondary=TrendDirection.UNKNOWN,
                strength=0.0,
                confidence=0.0,
                reasons=(
                    (f"Insufficient data: need {long_period} candles, "
                    f"got {len(series)}."),
                ),
            )

        closes = series.closes

        short_sma = self._sma(closes, short_period)
        long_sma = self._sma(closes, long_period)

        if short_sma is None or long_sma is None:
            return TrendStructure(
                primary=TrendDirection.UNKNOWN,
                secondary=TrendDirection.UNKNOWN,
                strength=0.0,
                confidence=0.0,
                reasons=("Could not compute moving averages.",),
            )

        primary = self._direction(closes, long_sma, long_period)
        secondary = self._direction(closes, short_sma, short_period)

        strength = self._strength(closes, long_sma, long_period)
        confidence = self._confidence(
            closes, long_sma, short_sma, long_period, short_period
        )

        reasons.extend(self._reasons(primary, secondary, strength, long_sma, short_sma))

        return TrendStructure(
            primary=primary,
            secondary=secondary,
            strength=strength,
            confidence=confidence,
            reasons=tuple(reasons),
        )

    def _sma(self, values: list[float], period: int) -> float | None:
        if len(values) < period:
            return None
        return sum(values[-period:]) / period

    def _direction(
        self,
        closes: list[float],
        sma: float,
        period: int,
    ) -> TrendDirection:
        above = sum(1 for c in closes[-period:] if c > sma * ABOVE_SMA_THRESHOLD)
        below = sum(1 for c in closes[-period:] if c < sma * BELOW_SMA_THRESHOLD)
        threshold = period * 0.6

        if above >= threshold:
            return TrendDirection.BULLISH
        if below >= threshold:
            return TrendDirection.BEARISH
        return TrendDirection.SIDEWAYS

    def _strength(
        self,
        closes: list[float],
        sma: float,
        period: int,
    ) -> float:
        deviations = [abs(c - sma) / sma for c in closes[-period:]]
        avg_deviation = sum(deviations) / len(deviations) if deviations else 0.0

        score = min(1.0, avg_deviation * 20)
        return score

    def _confidence(
        self,
        closes: list[float],
        long_sma: float,
        short_sma: float,
        long_period: int,
        short_period: int,
    ) -> float:
        factors: list[float] = []

        alignment = 0.0
        above_long = sum(1 for c in closes[-long_period:] if c > long_sma)
        ratio_long = above_long / long_period
        alignment += 0.5 * (1.0 - abs(ratio_long - 0.5) * 2)
        factors.append(alignment)

        sma_distance = abs(long_sma - short_sma) / long_sma
        if sma_distance > 0.02:
            factors.append(0.8)
        elif sma_distance > 0.01:
            factors.append(0.5)
        else:
            factors.append(0.3)

        if not factors:
            return 0.0

        return min(1.0, sum(factors) / len(factors))

    def _reasons(
        self,
        primary: TrendDirection,
        secondary: TrendDirection,
        strength: float,
        long_sma: float,
        short_sma: float,
    ) -> list[str]:
        reasons: list[str] = []

        reasons.append(f"Primary trend is {primary.value}.")
        reasons.append(f"Secondary trend is {secondary.value}.")

        if strength >= STRENGTH_HIGH:
            reasons.append("Trend strength is high.")
        elif strength >= STRENGTH_MODERATE:
            reasons.append("Trend strength is moderate.")
        elif strength >= STRENGTH_LOW:
            reasons.append("Trend strength is low.")
        else:
            reasons.append("Trend strength is minimal.")

        reasons.append(f"Long-term SMA ({long_sma:.2f}).")
        reasons.append(f"Short-term SMA ({short_sma:.2f}).")

        return reasons
