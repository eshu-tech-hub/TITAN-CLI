from statistics import stdev

from titan.options.analytics.models import (
    HVTrend,
    HVStability,
    VolatilitySnapshot,
)

TREND_MIN_OBSERVATIONS = 2
STABILITY_MIN_OBSERVATIONS = 3
MAX_STABLE_CV = 0.3


class HVAnalyzer:
    """Analyze supplied historical volatility values.

    Determines current HV level, directional trend, and stability
    of HV estimates over the observation window.
    """

    name = "HVAnalyzer"

    def analyze(
        self, snapshot: VolatilitySnapshot
    ) -> tuple[float | None, HVTrend, HVStability, float]:
        """Analyze historical volatility from snapshot data.

        Args:
            snapshot: Volatility data snapshot.

        Returns:
            (current_hv, hv_trend, hv_stability, confidence) tuple.
        """

        hv = snapshot.historical_volatility

        if hv is None:
            return None, HVTrend.UNKNOWN, HVStability.UNKNOWN, 0.0

        trend = self._detect_trend(snapshot.historical_volatilities)
        stability = self._classify_stability(snapshot.historical_volatilities)
        confidence = self._confidence(snapshot)

        return hv, trend, stability, confidence

    def _detect_trend(self, values: tuple[float, ...]) -> HVTrend:
        if len(values) < TREND_MIN_OBSERVATIONS:
            return HVTrend.UNKNOWN

        recent = values[-TREND_MIN_OBSERVATIONS:]

        if recent[-1] > recent[0] * 1.05:
            return HVTrend.RISING
        if recent[-1] < recent[0] * 0.95:
            return HVTrend.FALLING
        return HVTrend.FLAT

    def _classify_stability(self, values: tuple[float, ...]) -> HVStability:
        if len(values) < STABILITY_MIN_OBSERVATIONS:
            return HVStability.UNKNOWN

        mean = sum(values) / len(values)

        if mean == 0.0:
            return HVStability.UNKNOWN

        cv = stdev(values) / mean

        if cv <= MAX_STABLE_CV:
            return HVStability.STABLE
        return HVStability.UNSTABLE

    def _confidence(self, snapshot: VolatilitySnapshot) -> float:
        if snapshot.historical_volatility is None:
            return 0.0
        if len(snapshot.historical_volatilities) >= STABILITY_MIN_OBSERVATIONS:
            return 0.7
        return 0.5
