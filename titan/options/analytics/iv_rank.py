from titan.options.analytics.models import (
    IVRankLevel,
    VolatilitySnapshot,
)

VERY_HIGH_RANK_THRESHOLD = 80.0
HIGH_RANK_THRESHOLD = 60.0
LOW_RANK_THRESHOLD = 20.0
VERY_LOW_RANK_THRESHOLD = 20.0


class IVRankAnalyzer:
    """Analyze supplied IV rank values.

    IV rank measures where current IV sits within the 52-week range
    as a percentile (0-100). Higher values indicate expensive options.
    """

    name = "IVRankAnalyzer"

    def analyze(
        self, snapshot: VolatilitySnapshot
    ) -> tuple[IVRankLevel, float | None, float]:
        """Classify IV rank level.

        Args:
            snapshot: Volatility data snapshot containing iv_rank.

        Returns:
            (rank_level, rank_value, confidence) tuple.
        """

        rank = snapshot.iv_rank

        if rank is None:
            return IVRankLevel.UNKNOWN, None, 0.0

        if rank < 0.0 or rank > 100.0:
            return IVRankLevel.UNKNOWN, rank, 0.0

        level = self._classify(rank)

        return level, rank, 0.6

    def _classify(self, rank: float) -> IVRankLevel:
        if rank >= VERY_HIGH_RANK_THRESHOLD:
            return IVRankLevel.VERY_HIGH
        if rank >= HIGH_RANK_THRESHOLD:
            return IVRankLevel.HIGH
        if rank >= LOW_RANK_THRESHOLD:
            return IVRankLevel.NEUTRAL
        return IVRankLevel.VERY_LOW
