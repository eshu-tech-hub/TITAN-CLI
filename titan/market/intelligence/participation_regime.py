"""Participation Regime Analyzer.

Synthesises Volume and Breadth intelligence to assess participation
quality, institutional confirmation, and market compression/expansion.

Pure synthesis — consumes existing intelligence, no market calculations.
"""

from titan.market.intelligence.models import (
    BreadthAnalysis,
    ParticipationRegime,
    VolumeAnalysis,
)

CONFIDENCE_HIGH = 0.7
CONFIDENCE_LOW = 0.3

HEALTHY_RVOL = 1.5
HEALTHY_AD = 1.5
EXHAUSTION_HIGH = 0.6


class ParticipationRegimeAnalyzer:
    """Synthesise participation regime from volume and breadth.

    Consumes VolumeAnalysis and BreadthAnalysis to determine
    institutional confirmation, compression, and expansion.
    """

    name = "ParticipationRegimeAnalyzer"

    def analyze(
        self,
        volume: VolumeAnalysis | None,
        breadth: BreadthAnalysis | None,
    ) -> ParticipationRegime:
        """Determine participation regime characteristics.

        Args:
            volume: Volume intelligence output.
            breadth: Breadth intelligence output.

        Returns:
            Participation regime assessment.
        """

        reasons: list[str] = []

        if volume is None or breadth is None:
            return ParticipationRegime(
                confidence=0.0,
                reasons=("Insufficient intelligence inputs.",),
            )

        if volume.confidence < CONFIDENCE_LOW and breadth.confidence < CONFIDENCE_LOW:
            return ParticipationRegime(
                confidence=0.0,
                reasons=("All inputs have low confidence.",),
            )

        institutional_conf = self._institutional_confirmation(volume, breadth)
        compressed = self._compressed(volume, breadth)
        expanding = self._expanding(volume, breadth)
        quality = self._quality(institutional_conf, compressed, expanding)

        confidence = self._confidence(volume, breadth)

        reasons.extend(
            self._reasons(
                quality=quality,
                institutional_conf=institutional_conf,
                compressed=compressed,
                expanding=expanding,
            )
        )

        return ParticipationRegime(
            quality=quality,
            institutional_confirmation=institutional_conf,
            compressed=compressed,
            expanding=expanding,
            confidence=confidence,
            reasons=tuple(reasons),
        )

    def _institutional_confirmation(
        self,
        volume: VolumeAnalysis,
        breadth: BreadthAnalysis,
    ) -> bool:
        vol_confirms = (
            volume.volume_bias.value in ("bullish", "bearish")
            and volume.confidence >= CONFIDENCE_LOW
        )
        breadth_confirms = (
            breadth.breadth_bias.value in ("bullish", "bearish")
            and breadth.confidence >= CONFIDENCE_LOW
        )
        return vol_confirms or breadth_confirms

    def _compressed(
        self,
        volume: VolumeAnalysis,
        breadth: BreadthAnalysis,
    ) -> bool:
        vol_low = volume.relative_volume < 0.67
        breadth_neutral = breadth.breadth_bias.value == "neutral"
        return vol_low and breadth_neutral

    def _expanding(
        self,
        volume: VolumeAnalysis,
        breadth: BreadthAnalysis,
    ) -> bool:
        vol_high = volume.relative_volume >= HEALTHY_RVOL
        breadth_active = breadth.breadth_bias.value in ("bullish", "bearish")
        return vol_high and breadth_active

    def _quality(
        self,
        institutional_conf: bool,
        compressed: bool,
        expanding: bool,
    ) -> str:
        if expanding and institutional_conf:
            return "strong"
        if compressed:
            return "low"
        if institutional_conf:
            return "moderate"
        return "neutral"

    def _confidence(
        self,
        volume: VolumeAnalysis,
        breadth: BreadthAnalysis,
    ) -> float:
        confidences: list[float] = []
        weights: list[float] = []

        if volume.confidence > 0:
            confidences.append(volume.confidence)
            weights.append(0.5)
        if breadth.confidence > 0:
            confidences.append(breadth.confidence)
            weights.append(0.5)

        if not confidences:
            return 0.0

        total = sum(c * w for c, w in zip(confidences, weights))
        total_w = sum(weights)
        return total / total_w if total_w > 0 else 0.0

    def _reasons(
        self,
        quality: str,
        institutional_conf: bool,
        compressed: bool,
        expanding: bool,
    ) -> list[str]:
        reasons: list[str] = []

        reasons.append(f"Participation quality is {quality}.")

        if institutional_conf:
            reasons.append("Institutional confirmation detected.")
        else:
            reasons.append("No strong institutional confirmation.")

        if compressed:
            reasons.append(
                "Market appears compressed — low volume " "and neutral breadth."
            )
        if expanding:
            reasons.append(
                "Market is expanding — rising volume " "with directional breadth."
            )

        return reasons
