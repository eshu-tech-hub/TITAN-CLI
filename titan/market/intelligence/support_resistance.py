"""Support and Resistance Analyzer.

Identifies institutional support and resistance zones from supplied
MarketDataSeries using swing points and price-level clustering.

No broker imports.
No API calls.
"""

from titan.market.intelligence.models import (
    SupportResistanceStructure,
    SwingStructure,
)
from titan.market.series import MarketDataSeries

CLUSTER_DISTANCE_PERCENT = 0.005
MAX_LEVELS = 6


class SupportResistanceAnalyzer:
    """Analyse support and resistance levels.

    Identifies key price levels where price has reversed multiple times,
    using swing points from SwingAnalyzer and price-level clustering.
    """

    name = "SupportResistanceAnalyzer"

    def analyze(
        self,
        series: MarketDataSeries,
        swing: SwingStructure | None = None,
    ) -> SupportResistanceStructure:
        """Identify support and resistance levels.

        Args:
            series: Market data series with OHLCV candles.
            swing: Pre-computed swing structure (optional). If not
                provided, swing points will not be available for
                level identification.

        Returns:
            Support and resistance structure assessment.
        """

        reasons: list[str] = []

        if len(series) < 10:
            return SupportResistanceStructure(
                confidence=0.0,
                reasons=(
                    f"Insufficient data: need at least 10 candles, "
                    f"got {len(series)}.",
                ),
            )

        resistance_levels: list[float] = []
        support_levels: list[float] = []

        if swing is not None:
            for sh in swing.swing_highs:
                resistance_levels.append(sh.price)
            for sl in swing.swing_lows:
                support_levels.append(sl.price)

        if not support_levels:
            support_levels = self._find_support_from_lows(series)
        if not resistance_levels:
            resistance_levels = self._find_resistance_from_highs(series)

        support_levels = self._cluster_levels(support_levels)
        resistance_levels = self._cluster_levels(resistance_levels)
        support_levels = support_levels[:MAX_LEVELS]
        resistance_levels = resistance_levels[:MAX_LEVELS]

        support_levels.sort(reverse=True)
        resistance_levels.sort(reverse=True)

        confidence = self._confidence(support_levels, resistance_levels, series)
        reasons.extend(self._reasons(support_levels, resistance_levels))

        return SupportResistanceStructure(
            support_levels=tuple(support_levels),
            resistance_levels=tuple(resistance_levels),
            confidence=confidence,
            reasons=tuple(reasons),
        )

    def _find_support_from_lows(
        self,
        series: MarketDataSeries,
    ) -> list[float]:
        lows = series.lows
        levels: list[float] = []

        for i in range(2, len(lows) - 2):
            if (
                lows[i] < lows[i - 1]
                and lows[i] < lows[i - 2]
                and lows[i] < lows[i + 1]
                and lows[i] < lows[i + 2]
            ):
                levels.append(lows[i])

        return levels

    def _find_resistance_from_highs(
        self,
        series: MarketDataSeries,
    ) -> list[float]:
        highs = series.highs
        levels: list[float] = []

        for i in range(2, len(highs) - 2):
            if (
                highs[i] > highs[i - 1]
                and highs[i] > highs[i - 2]
                and highs[i] > highs[i + 1]
                and highs[i] > highs[i + 2]
            ):
                levels.append(highs[i])

        return levels

    def _cluster_levels(
        self,
        levels: list[float],
    ) -> list[float]:
        if not levels:
            return []
        if len(levels) == 1:
            return [levels[0]]

        sorted_levels = sorted(levels)
        clustered: list[float] = []
        current_cluster: list[float] = [sorted_levels[0]]

        for level in sorted_levels[1:]:
            avg = sum(current_cluster) / len(current_cluster)
            avg_distance = abs(level - avg) / avg if avg != 0 else abs(level - avg)

            if avg_distance <= CLUSTER_DISTANCE_PERCENT:
                current_cluster.append(level)
            else:
                clustered.append(sum(current_cluster) / len(current_cluster))
                current_cluster = [level]

        if current_cluster:
            clustered.append(sum(current_cluster) / len(current_cluster))

        return clustered

    def _confidence(
        self,
        support_levels: list[float],
        resistance_levels: list[float],
        series: MarketDataSeries,
    ) -> float:
        total_levels = len(support_levels) + len(resistance_levels)
        if total_levels == 0:
            return 0.0

        score = min(1.0, total_levels / 6)
        return score

    def _reasons(
        self,
        support_levels: list[float],
        resistance_levels: list[float],
    ) -> list[str]:
        reasons: list[str] = []

        if support_levels:
            levels_str = ", ".join(f"{v:.2f}" for v in support_levels)
            reasons.append(f"Support levels: {levels_str}.")
        else:
            reasons.append("No support levels identified.")

        if resistance_levels:
            levels_str = ", ".join(f"{v:.2f}" for v in resistance_levels)
            reasons.append(f"Resistance levels: {levels_str}.")
        else:
            reasons.append("No significant resistance levels identified.")

        return reasons
