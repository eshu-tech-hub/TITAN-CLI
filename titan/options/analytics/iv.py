from titan.options.analytics.models import (
    IVLevel,
    IVTrend,
    VolatilitySnapshot,
)

HIGH_IV_THRESHOLD = 0.40
LOW_IV_THRESHOLD = 0.15
TREND_MIN_OBSERVATIONS = 2


class IVAnalyzer:
    """Analyze supplied implied volatility values.

    Determines whether IV is high, low, or normal relative to configured
    thresholds. Detects IV trend when historical values are available.
    """

    name = "IVAnalyzer"

    def analyze(self, snapshot: VolatilitySnapshot) -> tuple[IVLevel, IVTrend, float]:
        """Classify implied volatility level and trend.

        Args:
            snapshot: Volatility data snapshot.

        Returns:
            (iv_level, iv_trend, confidence) tuple.
        """

        iv = snapshot.implied_volatility

        if iv is None:
            return IVLevel.UNKNOWN, IVTrend.UNKNOWN, 0.0

        level = self._classify_level(iv)
        trend = self._detect_trend(snapshot.implied_volatilities)
        confidence = self._confidence(snapshot)

        return level, trend, confidence

    def _classify_level(self, iv: float) -> IVLevel:
        if iv >= HIGH_IV_THRESHOLD:
            return IVLevel.HIGH
        if iv <= LOW_IV_THRESHOLD:
            return IVLevel.LOW
        return IVLevel.NORMAL

    def _detect_trend(self, values: tuple[float, ...]) -> IVTrend:
        if len(values) < TREND_MIN_OBSERVATIONS:
            return IVTrend.UNKNOWN

        recent = values[-TREND_MIN_OBSERVATIONS:]

        if recent[-1] > recent[0] * 1.05:
            return IVTrend.RISING
        if recent[-1] < recent[0] * 0.95:
            return IVTrend.FALLING
        return IVTrend.FLAT

    def _confidence(self, snapshot: VolatilitySnapshot) -> float:
        if snapshot.implied_volatility is None:
            return 0.0
        if snapshot.implied_volatilities:
            return 0.7
        return 0.5
