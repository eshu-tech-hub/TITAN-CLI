"""Accumulation / Distribution Analyzer.

Detects smart-money participation through price-volume divergence analysis.

No broker imports.
No API calls.
"""

from titan.market.intelligence.models import AccumulationDistribution
from titan.market.series import MarketDataSeries

LOOKBACK = 5
MIN_CANDLES = 5
VOLUME_DIVERGENCE_THRESHOLD = 1.3
PRICE_CHANGE_THRESHOLD = 0.001


class AccumulationDistributionAnalyzer:
    """Analyse accumulation/distribution from price-volume relationship.

    Consumes MarketDataSeries to detect whether institutions are
    accumulating (buying on rising volume) or distributing (selling
    on rising volume).
    """

    name = "AccumulationDistributionAnalyzer"

    def analyze(
        self,
        series: MarketDataSeries,
    ) -> AccumulationDistribution:
        """Detect accumulation and distribution patterns.

        Args:
            series: Market data series with OHLCV candles.

        Returns:
            Accumulation/distribution assessment.
        """

        reasons: list[str] = []
        volumes = series.volumes
        closes = series.closes

        if len(volumes) < MIN_CANDLES or len(closes) < MIN_CANDLES:
            return AccumulationDistribution(
                confidence=0.0,
                reasons=(f"Insufficient data: need at least {MIN_CANDLES} candles.",),
            )

        lookback = min(LOOKBACK, len(volumes))

        recent_volumes = volumes[-lookback:]
        recent_closes = closes[-lookback:]

        up_volume = 0.0
        down_volume = 0.0
        divergence_count = 0

        for i in range(1, lookback):
            price_change = (recent_closes[i] - recent_closes[i - 1]) / recent_closes[
                i - 1
            ]
            vol_ratio = (
                recent_volumes[i] / recent_volumes[i - 1]
                if recent_volumes[i - 1] > 0
                else 1.0
            )

            if price_change > PRICE_CHANGE_THRESHOLD:
                up_volume += recent_volumes[i]
                if vol_ratio < 1.0 / VOLUME_DIVERGENCE_THRESHOLD:
                    divergence_count += 1
            elif price_change < -PRICE_CHANGE_THRESHOLD:
                down_volume += recent_volumes[i]
                if vol_ratio < 1.0 / VOLUME_DIVERGENCE_THRESHOLD:
                    divergence_count += 1

        total_volume = up_volume + down_volume
        ad_ratio = up_volume / total_volume if total_volume > 0 else 0.5

        accumulation = ad_ratio >= 0.6
        distribution = ad_ratio <= 0.4
        divergence = divergence_count >= lookback // 2

        confidence = self._confidence(len(volumes), ad_ratio)

        reasons.extend(
            self._reasons(
                ad_ratio=ad_ratio,
                accumulation=accumulation,
                distribution=distribution,
                divergence=divergence,
                divergence_count=divergence_count,
            )
        )

        return AccumulationDistribution(
            accumulation=accumulation,
            distribution=distribution,
            ad_ratio=ad_ratio,
            divergence=divergence,
            confidence=confidence,
            reasons=tuple(reasons),
        )

    def _confidence(
        self,
        num_candles: int,
        ad_ratio: float,
    ) -> float:
        if num_candles < MIN_CANDLES:
            return 0.0
        sample_factor = min(1.0, num_candles / 20)
        if abs(ad_ratio - 0.5) > 0.1:
            signal = 0.7
        else:
            signal = 0.3
        return min(1.0, sample_factor * (0.3 + 0.7 * signal))

    def _reasons(
        self,
        ad_ratio: float,
        accumulation: bool,
        distribution: bool,
        divergence: bool,
        divergence_count: int,
    ) -> list[str]:
        reasons: list[str] = []

        if accumulation:
            reasons.append(
                f"Accumulation detected — up-volume ratio is {ad_ratio:.2f}."
            )
        elif distribution:
            reasons.append(
                f"Distribution detected — up-volume ratio is {ad_ratio:.2f}."
            )
        else:
            reasons.append(
                f"No clear accumulation or distribution — "
                f"up-volume ratio is {ad_ratio:.2f}."
            )

        if divergence:
            reasons.append(
                f"Price-volume divergence in {divergence_count} of {LOOKBACK} periods."
            )

        return reasons
