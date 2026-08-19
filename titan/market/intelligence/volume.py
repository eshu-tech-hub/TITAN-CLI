"""Volume Intelligence Engine — Orchestrator.

Provides institutional-grade volume analysis from supplied price data.
Evaluates relative volume, volume trend, accumulation/distribution, and
participation strength.

Pure orchestrator — no broker imports, no API calls.

Integrates with:
  - Evidence Engine
  - Intelligence Fusion Engine
  - Market Structure Intelligence
  - VWAP Intelligence
"""

from typing import Any

from titan.core.evidence import (
    Confidence,
    Evidence,
    EvidenceCategory,
    EvidenceSignal,
    Score,
)
from titan.market.intelligence.accumulation_distribution import (
    AccumulationDistributionAnalyzer,
)
from titan.market.intelligence.models import (
    ParticipationLevel,
    VolumeAnalysis,
    VolumeBias,
    VolumeExplanation,
    VolumeTrend,
)
from titan.market.intelligence.relative_volume import RelativeVolumeAnalyzer
from titan.market.intelligence.volume_trend import VolumeTrendAnalyzer
from titan.market.series import MarketDataSeries

POSITIVE_SCORE = 65.0
NEGATIVE_SCORE = 35.0
NEUTRAL_SCORE = 50.0

CONFIDENCE_HIGH = 0.7
CONFIDENCE_MODERATE = 0.5
CONFIDENCE_LOW = 0.3

RVOL_BULLISH_LOW = 1.5
RVOL_BEARISH_HIGH = 0.67
RVOL_EXTREME = 3.0
EXHAUSTION_RVOL = 3.0
EXHAUSTION_CONTRACTION = 0.5


class VolumeAnalyzer:
    """Orchestrate Volume Intelligence.

    Consumes MarketDataSeries and delegates to VolumeTrendAnalyzer,
    RelativeVolumeAnalyzer, and AccumulationDistributionAnalyzer to
    produce a unified institutional assessment of volume context.
    Pure orchestrator — does not recalculate any volume metric.
    """

    name = "VolumeAnalyzer"

    def __init__(
        self,
        trend_analyzer: VolumeTrendAnalyzer | None = None,
        relative_analyzer: RelativeVolumeAnalyzer | None = None,
        ad_analyzer: AccumulationDistributionAnalyzer | None = None,
    ) -> None:
        self._trend = trend_analyzer or VolumeTrendAnalyzer()
        self._relative = relative_analyzer or RelativeVolumeAnalyzer()
        self._ad = ad_analyzer or AccumulationDistributionAnalyzer()

    def analyze(
        self,
        series: MarketDataSeries,
    ) -> VolumeAnalysis:
        """Execute volume intelligence analysis.

        Args:
            series: Market data series with OHLCV candles.

        Returns:
            Combined VolumeAnalysis.
        """

        if len(series) < 2:
            return self._empty_analysis(
                f"Insufficient data: need at least 2 candles, got {len(series)}."
            )

        current_volume = series.volumes[-1]
        relative = self._relative.analyze(series)
        trend = self._trend.analyze(series)
        ad = self._ad.analyze(series)

        avg_volume = relative.average_volume
        rvol = relative.rvol
        participation_level = relative.participation

        breakout_confirmation = self._breakout_confirmation(trend, ad)

        exhaustion_probability = self._exhaustion_probability(rvol, trend, series)

        volume_bias = self._bias(rvol, ad, trend)

        confidence = self._calculate_confidence(relative, trend, ad, series)

        analysis = VolumeAnalysis(
            current_volume=current_volume,
            average_volume=avg_volume,
            relative_volume=rvol,
            participation_level=participation_level,
            volume_bias=volume_bias,
            breakout_confirmation=breakout_confirmation,
            exhaustion_probability=exhaustion_probability,
            trend=trend,
            relative=relative,
            accumulation_distribution=ad,
            confidence=confidence,
            warnings=self._combine_warnings(series, relative, trend, ad),
            metadata=self._metadata(series, relative, trend, ad),
        )

        evidence = self._to_evidence(analysis)
        explanation = self._explanation(analysis, trend, relative, ad)

        object.__setattr__(analysis, "evidence", evidence)
        object.__setattr__(analysis, "explanation", explanation)

        return analysis

    # ------------------------------------------------------------------
    # Core calculations
    # ------------------------------------------------------------------

    def _breakout_confirmation(
        self,
        trend: VolumeTrend,
        ad: Any,
    ) -> bool:
        return trend.expanding and (ad.accumulation or ad.distribution)

    def _exhaustion_probability(
        self,
        rvol: float,
        trend: VolumeTrend,
        series: MarketDataSeries,
    ) -> float:
        prob = 0.0

        if rvol >= EXHAUSTION_RVOL:
            prob += 0.4

        if trend.contracting:
            prob += 0.3

        if len(series) >= 3:
            recent_volumes = series.volumes[-3:]
            if len(recent_volumes) >= 3:
                vol_decrease = all(
                    recent_volumes[i] <= recent_volumes[i - 1]
                    for i in range(1, len(recent_volumes))
                )
                if vol_decrease and rvol >= RVOL_BULLISH_LOW:
                    prob += 0.3

        return min(1.0, prob)

    def _bias(
        self,
        rvol: float,
        ad: Any,
        trend: VolumeTrend,
    ) -> VolumeBias:
        if ad.accumulation and rvol >= RVOL_BULLISH_LOW:
            return VolumeBias.BULLISH
        if ad.distribution and rvol >= RVOL_BULLISH_LOW:
            return VolumeBias.BEARISH
        if trend.expanding and ad.accumulation:
            return VolumeBias.BULLISH
        if trend.expanding and ad.distribution:
            return VolumeBias.BEARISH
        if rvol <= RVOL_BEARISH_HIGH:
            return VolumeBias.NEUTRAL
        return VolumeBias.UNKNOWN

    # ------------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------------

    def _calculate_confidence(
        self,
        relative: Any,
        trend: VolumeTrend,
        ad: Any,
        series: MarketDataSeries,
    ) -> float:
        confidences: list[float] = []
        weights: list[float] = []

        if relative.confidence > 0:
            confidences.append(relative.confidence)
            weights.append(0.35)

        if trend.confidence > 0:
            confidences.append(trend.confidence)
            weights.append(0.35)

        if ad.confidence > 0:
            confidences.append(ad.confidence)
            weights.append(0.30)

        sample_factor = min(1.0, len(series) / 20)
        confidences.append(sample_factor)
        weights.append(0.20)

        if not confidences:
            return 0.0

        total = sum(c * w for c, w in zip(confidences, weights))
        total_w = sum(weights)
        return total / total_w if total_w > 0 else 0.0

    # ------------------------------------------------------------------
    # Warnings
    # ------------------------------------------------------------------

    def _combine_warnings(
        self,
        series: MarketDataSeries,
        relative: Any,
        trend: VolumeTrend,
        ad: Any,
    ) -> tuple[str, ...]:
        combined: list[str] = []

        if len(series) < 10:
            combined.append(
                f"Limited data: {len(series)} candle(s). "
                "Volume analysis may be unreliable."
            )

        if relative.confidence < CONFIDENCE_LOW:
            combined.append("Low relative volume confidence.")

        if trend.confidence < CONFIDENCE_LOW:
            combined.append("Low volume trend confidence.")

        if ad.confidence < CONFIDENCE_LOW:
            combined.append("Low accumulation/distribution confidence.")

        return tuple(combined)

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def _metadata(
        self,
        series: MarketDataSeries,
        relative: Any,
        trend: VolumeTrend,
        ad: Any,
    ) -> dict[str, Any]:
        return {
            "analyzer": self.name,
            "candle_count": len(series),
            "rvol": relative.rvol,
            "participation": relative.participation.value,
            "volume_slope": trend.slope,
            "expanding": trend.expanding,
            "contracting": trend.contracting,
            "accumulation": ad.accumulation,
            "distribution": ad.distribution,
            "divergence": ad.divergence,
        }

    # ------------------------------------------------------------------
    # Evidence generation
    # ------------------------------------------------------------------

    def _evidence_signal(self, bias: VolumeBias) -> EvidenceSignal:
        mapping = {
            VolumeBias.BULLISH: EvidenceSignal.BULLISH,
            VolumeBias.BEARISH: EvidenceSignal.BEARISH,
            VolumeBias.NEUTRAL: EvidenceSignal.NEUTRAL,
        }
        return mapping.get(bias, EvidenceSignal.UNKNOWN)

    def _evidence_score(
        self,
        analysis: VolumeAnalysis,
    ) -> float:
        base = NEUTRAL_SCORE
        if analysis.volume_bias is VolumeBias.BULLISH:
            base = POSITIVE_SCORE
        elif analysis.volume_bias is VolumeBias.BEARISH:
            base = NEGATIVE_SCORE

        adj = 0.0
        if analysis.breakout_confirmation:
            adj += 5.0
        if analysis.confidence >= CONFIDENCE_HIGH:
            adj += 5.0
        elif analysis.confidence >= CONFIDENCE_MODERATE:
            adj += 3.0

        return max(0.0, min(100.0, base + adj))

    def _evidence_reasons(
        self,
        analysis: VolumeAnalysis,
    ) -> tuple[str, ...]:
        reasons: list[str] = []

        reasons.append(f"RVOL is {analysis.relative_volume:.2f}x average.")
        reasons.append(f"Participation is {analysis.participation_level.value}.")
        reasons.append(f"Volume bias is {analysis.volume_bias.value}.")

        if analysis.breakout_confirmation:
            reasons.append("Volume confirms breakout/breakdown.")

        return tuple(reasons)

    def _to_evidence(
        self,
        analysis: VolumeAnalysis,
    ) -> Evidence:
        signal = self._evidence_signal(analysis.volume_bias)
        score = self._evidence_score(analysis)
        confidence = analysis.confidence

        return Evidence(
            source="Volume",
            category=EvidenceCategory.VOLUME,
            signal=signal,
            score=Score(score),
            confidence=Confidence(confidence),
            weight=1.0,
            reasons=self._evidence_reasons(analysis),
            warnings=analysis.warnings,
            metadata={
                "analyzer": self.name,
                "rvol": analysis.relative_volume,
                "participation": analysis.participation_level.value,
                "bias": analysis.volume_bias.value,
                "breakout_confirmation": analysis.breakout_confirmation,
                "exhaustion_probability": analysis.exhaustion_probability,
                "accumulation": (
                    analysis.accumulation_distribution.accumulation
                    if analysis.accumulation_distribution
                    else False
                ),
                "distribution": (
                    analysis.accumulation_distribution.distribution
                    if analysis.accumulation_distribution
                    else False
                ),
            },
        )

    # ------------------------------------------------------------------
    # Explanation generation
    # ------------------------------------------------------------------

    def _explanation(
        self,
        analysis: VolumeAnalysis,
        trend: VolumeTrend,
        relative: Any,
        ad: Any,
    ) -> VolumeExplanation:
        return VolumeExplanation(
            current_volume=self._current_vol_section(analysis),
            relative_volume=self._rv_section(analysis),
            participation=self._participation_section(analysis),
            accumulation_distribution=self._ad_section(analysis, ad),
            breakout_quality=self._breakout_section(analysis, trend),
            institutional_interpretation=self._institutional_section(analysis),
        )

    def _current_vol_section(self, analysis: VolumeAnalysis) -> str:
        return (
            f"Current Volume: {analysis.current_volume:,}. "
            f"Average Volume: {analysis.average_volume:,.0f}."
        )

    def _rv_section(self, analysis: VolumeAnalysis) -> str:
        return (
            f"Relative Volume: {analysis.relative_volume:.2f}x. "
            f"Volume is "
            f"{'above' if analysis.relative_volume >= 1.0 else 'below'} "
            f"the average."
        )

    def _participation_section(self, analysis: VolumeAnalysis) -> str:
        mapping = {
            ParticipationLevel.VERY_LOW: (
                "Participation is very low. Market is illiquid."
            ),
            ParticipationLevel.LOW: ("Participation is below normal. Low conviction."),
            ParticipationLevel.NORMAL: (
                "Participation is normal. No anomalous activity detected."
            ),
            ParticipationLevel.HIGH: (
                "Participation is high. Significant market "
                "interest in current price levels."
            ),
            ParticipationLevel.EXTREME: (
                "Participation is extreme. Potential climax or exhaustion risk."
            ),
        }
        return mapping.get(
            analysis.participation_level,
            "Participation cannot be determined.",
        )

    def _ad_section(self, analysis: VolumeAnalysis, ad: Any) -> str:
        parts: list[str] = ["Accumulation / Distribution:"]

        if ad.accumulation:
            parts.append("Accumulation detected — price increasing with rising volume.")
        elif ad.distribution:
            parts.append("Distribution detected — price decreasing with rising volume.")
        else:
            parts.append("No clear accumulation or distribution pattern.")

        if ad.divergence:
            parts.append("Price-volume divergence detected — trend may be weakening.")

        return " ".join(parts)

    def _breakout_section(
        self,
        analysis: VolumeAnalysis,
        trend: VolumeTrend,
    ) -> str:
        parts: list[str] = ["Breakout Quality Assessment:"]

        if analysis.breakout_confirmation:
            parts.append("Volume confirms breakout — high conviction setup.")
        elif trend.expanding:
            parts.append("Volume is expanding but no clear breakout signal yet.")
        else:
            parts.append("Volume is not confirming breakouts. Caution warranted.")

        return " ".join(parts)

    def _institutional_section(self, analysis: VolumeAnalysis) -> str:
        parts: list[str] = ["Institutional Interpretation:"]

        bias = analysis.volume_bias
        ex_prob = analysis.exhaustion_probability

        if bias is VolumeBias.BULLISH:
            parts.append(
                "Volume supports bullish positioning. "
                "Institutional accumulation detected."
            )
        elif bias is VolumeBias.BEARISH:
            parts.append(
                "Volume supports bearish positioning. "
                "Institutional distribution detected."
            )
        elif bias is VolumeBias.NEUTRAL:
            parts.append(
                "Volume is neutral. Institutions are not actively positioning."
            )
        else:
            parts.append(
                "Volume context is inconclusive. Cross-reference "
                "with market structure and price action."
            )

        if ex_prob >= 0.6:
            parts.append("Elevated exhaustion risk. Monitor for potential reversal.")
        elif ex_prob >= 0.3:
            parts.append("Moderate exhaustion risk. Exercise caution.")

        if analysis.confidence < CONFIDENCE_LOW:
            parts.append(
                "Low confidence suggests limited data "
                "availability. Interpret with caution."
            )

        return " ".join(parts)

    # ------------------------------------------------------------------
    # Empty / fallback analysis
    # ------------------------------------------------------------------

    def _empty_analysis(self, reason: str) -> VolumeAnalysis:
        analysis = VolumeAnalysis.neutral_placeholder()
        object.__setattr__(analysis, "warnings", (reason,))
        explanation = VolumeExplanation(
            current_volume="Volume assessment unavailable: insufficient data.",
            relative_volume="Relative volume unavailable: insufficient data.",
            participation="Participation unavailable: insufficient data.",
            accumulation_distribution="Accumulation/distribution "
            "unavailable: insufficient data.",
            breakout_quality="Breakout quality unavailable: insufficient data.",
            institutional_interpretation="Institutional "
            "Interpretation: Volume data is unavailable.",
        )
        object.__setattr__(analysis, "explanation", explanation)
        return analysis
