"""Relative Volume (RVOL) Analyzer.

Computes current-to-average volume ratio and classifies market
participation intensity.

No broker imports.
No API calls.
"""

from titan.market.intelligence.models import (
    ParticipationLevel,
    RelativeVolume,
)
from titan.market.series import MarketDataSeries

DEFAULT_LOOKBACK = 20
MIN_CANDLES = 5


class RelativeVolumeAnalyzer:
    """Analyse relative volume and market participation intensity.

    Consumes MarketDataSeries to compute the ratio of current
    volume to average volume and classify participation level.
    """

    name = "RelativeVolumeAnalyzer"

    def analyze(
        self,
        series: MarketDataSeries,
        lookback: int = DEFAULT_LOOKBACK,
    ) -> RelativeVolume:
        """Compute relative volume and classify participation.

        Args:
            series: Market data series with OHLCV candles.
            lookback: Number of periods for average volume calculation.

        Returns:
            Relative volume assessment.
        """

        reasons: list[str] = []
        volumes = series.volumes

        if len(volumes) < 2:
            return RelativeVolume(
                rvol=0.0,
                average_volume=0.0,
                participation=ParticipationLevel.NORMAL,
                confidence=0.0,
                reasons=("Insufficient data: need at least 2 candles.",),
            )

        recent_lookback = min(lookback, len(volumes))
        lookback_volumes = volumes[-recent_lookback:]

        current_volume = volumes[-1]
        avg_volume = sum(lookback_volumes) / recent_lookback

        if avg_volume > 0:
            rvol = current_volume / avg_volume
        else:
            rvol = 0.0

        participation = self._participation_level(rvol)
        confidence = self._confidence(len(volumes), rvol)
        reasons.extend(self._reasons(rvol, participation))

        return RelativeVolume(
            rvol=rvol,
            average_volume=float(avg_volume),
            participation=participation,
            confidence=confidence,
            reasons=tuple(reasons),
        )

    def _participation_level(
        self,
        rvol: float,
    ) -> ParticipationLevel:
        if rvol <= 0.25:
            return ParticipationLevel.VERY_LOW
        elif rvol <= 0.67:
            return ParticipationLevel.LOW
        elif rvol >= 3.0:
            return ParticipationLevel.EXTREME
        elif rvol >= 1.5:
            return ParticipationLevel.HIGH
        else:
            return ParticipationLevel.NORMAL

    def _confidence(
        self,
        num_candles: int,
        rvol: float,
    ) -> float:
        if num_candles < MIN_CANDLES:
            return 0.0
        sample_factor = min(1.0, num_candles / DEFAULT_LOOKBACK)
        if abs(rvol - 1.0) > 0.5:
            signal = 0.75
        else:
            signal = 0.3
        return min(1.0, sample_factor * (0.3 + 0.7 * signal))

    def _reasons(
        self,
        rvol: float,
        participation: ParticipationLevel,
    ) -> list[str]:
        reasons: list[str] = []
        reasons.append(f"RVOL is {rvol:.2f}x average volume.")
        reasons.append(f"Participation is {participation.value}.")
        return reasons
