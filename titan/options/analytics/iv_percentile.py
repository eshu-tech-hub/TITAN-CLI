from titan.options.analytics.models import (
    IVRankLevel,
    VolatilitySnapshot,
)

MAX_PERCENTILE = 100.0
MIN_PERCENTILE = 0.0
VERY_HIGH_PERCENTILE_THRESHOLD = 80.0
HIGH_PERCENTILE_THRESHOLD = 60.0
LOW_PERCENTILE_THRESHOLD = 40.0


class IVPercentileAnalyzer:
    """Analyze supplied IV percentile values.

    IV percentile indicates the percentage of days IV was lower than
    the current reading over the lookback period. Uses same thresholds
    as IV rank for consistency.
    """

    name = "IVPercentileAnalyzer"

    def analyze(
        self, snapshot: VolatilitySnapshot
    ) -> tuple[IVRankLevel, float | None, float]:
        """Classify IV percentile level.

        Args:
            snapshot: Volatility data snapshot containing iv_percentile.

        Returns:
            (percentile_level, percentile_value, confidence) tuple.
        """

        percentile = snapshot.iv_percentile

        if percentile is None:
            return IVRankLevel.UNKNOWN, None, 0.0

        if percentile < MIN_PERCENTILE or percentile > MAX_PERCENTILE:
            return IVRankLevel.UNKNOWN, percentile, 0.0

        level = self._classify(percentile)

        return level, percentile, 0.6

    def _classify(self, percentile: float) -> IVRankLevel:
        if percentile >= VERY_HIGH_PERCENTILE_THRESHOLD:
            return IVRankLevel.VERY_HIGH
        if percentile >= HIGH_PERCENTILE_THRESHOLD:
            return IVRankLevel.HIGH
        if percentile >= LOW_PERCENTILE_THRESHOLD:
            return IVRankLevel.NEUTRAL
        return IVRankLevel.LOW
