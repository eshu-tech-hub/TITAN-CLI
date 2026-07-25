from titan.options.analytics.models import (
    IVTrend,
    VolatilityRegime,
    VolatilitySnapshot,
)

PREMIUM_THRESHOLD = 1.10
DISCOUNT_THRESHOLD = 0.90


class VolatilityRegimeAnalyzer:
    """Analyze volatility regime from IV, HV, and trend data.

    Determines whether the market is in expansion, compression, stable,
    or transition based on the relationship between implied and
    historical volatility and their respective trends.
    """

    name = "VolatilityRegimeAnalyzer"

    def analyze(
        self,
        snapshot: VolatilitySnapshot,
        iv_trend: IVTrend,
    ) -> tuple[VolatilityRegime, bool, bool, float]:
        """Classify the current volatility regime.

        Args:
            snapshot: Volatility data snapshot.
            iv_trend: IV trend classification from IVAnalyzer.

        Returns:
            (regime, buying_bias, selling_bias, confidence) tuple.
        """

        iv = snapshot.implied_volatility
        hv = snapshot.historical_volatility

        if iv is None or hv is None:
            return VolatilityRegime.UNKNOWN, False, False, 0.0

        regime = self._classify_regime(iv, hv, iv_trend)
        buying_bias, selling_bias = self._bias_from_regime(regime, iv_trend)
        confidence = self._confidence(snapshot)

        return regime, buying_bias, selling_bias, confidence

    def _classify_regime(
        self, iv: float, hv: float, iv_trend: IVTrend
    ) -> VolatilityRegime:
        ratio = iv / hv if hv > 0.0 else float("inf")

        if ratio >= PREMIUM_THRESHOLD and iv_trend is IVTrend.RISING:
            return VolatilityRegime.EXPANSION
        if ratio <= DISCOUNT_THRESHOLD and iv_trend is IVTrend.FALLING:
            return VolatilityRegime.COMPRESSION

        is_normal = DISCOUNT_THRESHOLD < ratio < PREMIUM_THRESHOLD

        if is_normal and iv_trend is IVTrend.FLAT:
            return VolatilityRegime.STABLE
        if is_normal and iv_trend in (IVTrend.RISING, IVTrend.FALLING):
            return VolatilityRegime.TRANSITION

        if ratio >= PREMIUM_THRESHOLD:
            return VolatilityRegime.EXPANSION
        if ratio <= DISCOUNT_THRESHOLD:
            return VolatilityRegime.COMPRESSION

        return VolatilityRegime.STABLE

    def _bias_from_regime(
        self, regime: VolatilityRegime, iv_trend: IVTrend
    ) -> tuple[bool, bool]:
        if regime is VolatilityRegime.EXPANSION:
            return False, True
        if regime is VolatilityRegime.COMPRESSION:
            return True, False
        if regime is VolatilityRegime.TRANSITION:
            if iv_trend is IVTrend.RISING:
                return False, True
            return True, False
        return False, False

    def _confidence(self, snapshot: VolatilitySnapshot) -> float:
        if (
            snapshot.implied_volatility is None
            or snapshot.historical_volatility is None
        ):
            return 0.0
        if snapshot.implied_volatilities and snapshot.historical_volatilities:
            return 0.7
        return 0.5
