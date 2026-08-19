"""Breadth Intelligence Engine — Orchestrator.

Provides institutional-grade market breadth analysis from supplied
MarketBreadthSnapshot. Evaluates advance/decline ratio, sector
leadership, and participation quality.

Pure orchestrator — no broker imports, no API calls.

Integrates with:
  - Evidence Engine
  - Intelligence Fusion Engine
  - Market Structure Intelligence
  - VWAP Intelligence
  - Volume Intelligence
"""

from typing import Any

from titan.core.evidence import (
    Confidence,
    Evidence,
    EvidenceCategory,
    EvidenceSignal,
    Score,
)
from titan.market.intelligence.advance_decline import (
    AdvanceDeclineAnalyzer,
)
from titan.market.intelligence.market_participation import (
    MarketParticipationAnalyzer,
)
from titan.market.intelligence.models import (
    BreadthAnalysis,
    BreadthBias,
    BreadthExplanation,
    BreadthStrength,
    MarketBreadthSnapshot,
)
from titan.market.intelligence.sector_breadth import (
    SectorBreadthAnalyzer,
)

POSITIVE_SCORE = 65.0
NEGATIVE_SCORE = 35.0
NEUTRAL_SCORE = 50.0

CONFIDENCE_HIGH = 0.7
CONFIDENCE_MODERATE = 0.5
CONFIDENCE_LOW = 0.3

BULLISH_AD = 1.5
BEARISH_AD = 0.67
HEALTHY_BREADTH_AD = 1.2
HEALTHY_PARTICIPATION = 0.8


class BreadthAnalyzer:
    """Orchestrate Breadth Intelligence.

    Consumes MarketBreadthSnapshot and delegates to
    AdvanceDeclineAnalyzer, SectorBreadthAnalyzer, and
    MarketParticipationAnalyzer to produce a unified institutional
    assessment of market breadth. Pure orchestrator — does not
    recalculate any metric.
    """

    name = "BreadthAnalyzer"

    def __init__(
        self,
        ad_analyzer: AdvanceDeclineAnalyzer | None = None,
        sector_analyzer: SectorBreadthAnalyzer | None = None,
        participation_analyzer: MarketParticipationAnalyzer | None = None,
    ) -> None:
        self._ad = ad_analyzer or AdvanceDeclineAnalyzer()
        self._sector = sector_analyzer or SectorBreadthAnalyzer()
        self._participation = participation_analyzer or MarketParticipationAnalyzer()

    def analyze(
        self,
        snapshot: MarketBreadthSnapshot,
    ) -> BreadthAnalysis:
        """Execute breadth intelligence analysis.

        Args:
            snapshot: Market breadth snapshot.

        Returns:
            Combined BreadthAnalysis.
        """

        if snapshot.total_symbols < 2:
            return self._empty_analysis(
                f"Insufficient data: need at least 2 symbols, "
                f"got {snapshot.total_symbols}."
            )

        ad = self._ad.analyze(snapshot)
        sector = self._sector.analyze(snapshot)
        participation = self._participation.analyze(snapshot)

        advance_decline_ratio = ad.ad_ratio
        advance_percentage = ad.advance_percentage
        participation_ratio = participation.participation_ratio
        breadth_strength = ad.breadth_strength
        breadth_bias = self._bias(ad, participation)
        leading_sectors = sector.leading_sectors
        lagging_sectors = sector.lagging_sectors
        divergence_detected = participation.divergence_detected
        market_health = self._market_health(ad, participation)

        confidence = self._calculate_confidence(ad, sector, participation, snapshot)

        analysis = BreadthAnalysis(
            advance_decline_ratio=advance_decline_ratio,
            advance_percentage=advance_percentage,
            participation_ratio=participation_ratio,
            breadth_strength=breadth_strength,
            breadth_bias=breadth_bias,
            leading_sectors=leading_sectors,
            lagging_sectors=lagging_sectors,
            divergence_detected=divergence_detected,
            market_health=market_health,
            advance_decline=ad,
            sector_breadth=sector,
            market_participation=participation,
            confidence=confidence,
            warnings=self._combine_warnings(snapshot, ad, sector, participation),
            metadata=self._metadata(snapshot, ad, sector, participation),
        )

        evidence = self._to_evidence(analysis)
        explanation = self._explanation(analysis, ad, sector, participation)

        object.__setattr__(analysis, "evidence", evidence)
        object.__setattr__(analysis, "explanation", explanation)

        return analysis

    # ------------------------------------------------------------------
    # Core calculations
    # ------------------------------------------------------------------

    def _bias(
        self,
        ad: Any,
        participation: Any,
    ) -> BreadthBias:
        if (
            ad.breadth_strength
            in (
                BreadthStrength.VERY_STRONG,
                BreadthStrength.STRONG,
            )
            and participation.internal_strength
        ):
            return BreadthBias.BULLISH

        if (
            ad.breadth_strength
            in (
                BreadthStrength.VERY_WEAK,
                BreadthStrength.WEAK,
            )
            and participation.internal_weakness
        ):
            return BreadthBias.BEARISH

        if ad.advance_dominance and not participation.divergence_detected:
            return BreadthBias.BULLISH

        if ad.decline_dominance and not participation.divergence_detected:
            return BreadthBias.BEARISH

        return BreadthBias.NEUTRAL

    def _market_health(
        self,
        ad: Any,
        participation: Any,
    ) -> str:
        if (
            ad.breadth_strength in (BreadthStrength.VERY_STRONG, BreadthStrength.STRONG)
            and participation.internal_strength
        ):
            return "healthy"
        if (
            ad.breadth_strength in (BreadthStrength.VERY_WEAK, BreadthStrength.WEAK)
            and participation.internal_weakness
        ):
            return "unhealthy"
        if participation.divergence_detected:
            return "divergent"
        return "neutral"

    # ------------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------------

    def _calculate_confidence(
        self,
        ad: Any,
        sector: Any,
        participation: Any,
        snapshot: MarketBreadthSnapshot,
    ) -> float:
        confidences: list[float] = []
        weights: list[float] = []

        if ad.confidence > 0:
            confidences.append(ad.confidence)
            weights.append(0.40)

        if sector.confidence > 0:
            confidences.append(sector.confidence)
            weights.append(0.30)

        if participation.confidence > 0:
            confidences.append(participation.confidence)
            weights.append(0.30)

        sample_factor = min(1.0, snapshot.total_symbols / 50)
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
        snapshot: MarketBreadthSnapshot,
        ad: Any,
        sector: Any,
        participation: Any,
    ) -> tuple[str, ...]:
        combined: list[str] = []

        if snapshot.total_symbols < 50:
            combined.append(
                f"Limited symbols: {snapshot.total_symbols}. "
                "Breadth analysis may be less reliable."
            )

        if ad.confidence < CONFIDENCE_LOW:
            combined.append("Low A/D confidence.")

        if sector.confidence < CONFIDENCE_LOW:
            combined.append("Low sector breadth confidence.")

        if participation.confidence < CONFIDENCE_LOW:
            combined.append("Low participation confidence.")

        return tuple(combined)

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def _metadata(
        self,
        snapshot: MarketBreadthSnapshot,
        ad: Any,
        sector: Any,
        participation: Any,
    ) -> dict[str, Any]:
        return {
            "analyzer": self.name,
            "index_name": snapshot.index_name,
            "total_symbols": snapshot.total_symbols,
            "ad_ratio": ad.ad_ratio,
            "advance_pct": ad.advance_percentage,
            "breadth_strength": ad.breadth_strength.value,
            "advancing_sectors": sector.advancing_sectors,
            "declining_sectors": sector.declining_sectors,
            "participation_ratio": participation.participation_ratio,
            "divergence": participation.divergence_detected,
        }

    # ------------------------------------------------------------------
    # Evidence generation
    # ------------------------------------------------------------------

    def _evidence_signal(self, bias: BreadthBias) -> EvidenceSignal:
        mapping = {
            BreadthBias.BULLISH: EvidenceSignal.BULLISH,
            BreadthBias.BEARISH: EvidenceSignal.BEARISH,
            BreadthBias.NEUTRAL: EvidenceSignal.NEUTRAL,
        }
        return mapping.get(bias, EvidenceSignal.UNKNOWN)

    def _evidence_score(self, analysis: BreadthAnalysis) -> float:
        base = NEUTRAL_SCORE
        if analysis.breadth_bias is BreadthBias.BULLISH:
            base = POSITIVE_SCORE
        elif analysis.breadth_bias is BreadthBias.BEARISH:
            base = NEGATIVE_SCORE

        adj = 0.0
        if analysis.divergence_detected:
            adj -= 5.0
        if analysis.confidence >= CONFIDENCE_HIGH:
            adj += 5.0
        elif analysis.confidence >= CONFIDENCE_MODERATE:
            adj += 3.0

        return max(0.0, min(100.0, base + adj))

    def _evidence_reasons(self, analysis: BreadthAnalysis) -> tuple[str, ...]:
        reasons: list[str] = []

        reasons.append(f"A/D ratio is {analysis.advance_decline_ratio:.2f}.")
        reasons.append(f"Breadth is {analysis.breadth_strength.value}.")
        reasons.append(f"Bias is {analysis.breadth_bias.value}.")

        if analysis.divergence_detected:
            reasons.append("Breadth divergence detected.")

        return tuple(reasons)

    def _to_evidence(self, analysis: BreadthAnalysis) -> Evidence:
        signal = self._evidence_signal(analysis.breadth_bias)
        score = self._evidence_score(analysis)
        confidence = analysis.confidence

        return Evidence(
            source="Breadth",
            category=EvidenceCategory.MARKET_BREADTH,
            signal=signal,
            score=Score(score),
            confidence=Confidence(confidence),
            weight=1.0,
            reasons=self._evidence_reasons(analysis),
            warnings=analysis.warnings,
            metadata={
                "analyzer": self.name,
                "ad_ratio": analysis.advance_decline_ratio,
                "advance_pct": analysis.advance_percentage,
                "breadth_strength": analysis.breadth_strength.value,
                "bias": analysis.breadth_bias.value,
                "participation_ratio": analysis.participation_ratio,
                "divergence": analysis.divergence_detected,
                "leading_sectors": list(analysis.leading_sectors),
                "lagging_sectors": list(analysis.lagging_sectors),
            },
        )

    # ------------------------------------------------------------------
    # Explanation generation
    # ------------------------------------------------------------------

    def _explanation(
        self,
        analysis: BreadthAnalysis,
        ad: Any,
        sector: Any,
        participation: Any,
    ) -> BreadthExplanation:
        return BreadthExplanation(
            overall_breadth=self._breadth_section(analysis),
            advance_decline=self._ad_section(analysis, ad),
            participation=self._participation_section(analysis, participation),
            sector_leadership=self._sector_section(analysis, sector),
            market_health=self._health_section(analysis),
            institutional_interpretation=self._institutional_section(analysis),
        )

    def _breadth_section(self, analysis: BreadthAnalysis) -> str:
        return (
            f"Overall Breadth: {analysis.breadth_strength.value}. "
            f"A/D ratio: {analysis.advance_decline_ratio:.2f}. "
            f"Advancing: {analysis.advance_percentage:.1f}%."
        )

    def _ad_section(self, analysis: BreadthAnalysis, ad: Any) -> str:
        parts: list[str] = ["Advance / Decline Analysis:"]

        if ad.advance_dominance:
            parts.append(
                "Advances strongly dominate declines. "
                "Broad market participation on the upside."
            )
        elif ad.decline_dominance:
            parts.append(
                "Declines strongly dominate advances. "
                "Broad market participation on the downside."
            )
        else:
            parts.append("Advances and declines are relatively balanced.")

        return " ".join(parts)

    def _participation_section(
        self,
        analysis: BreadthAnalysis,
        participation: Any,
    ) -> str:
        parts: list[str] = ["Market Participation:"]

        if participation.internal_strength:
            parts.append("Broad participation confirms price action.")
        elif participation.internal_weakness:
            parts.append("Participation is narrow — internals do not support the move.")
        else:
            parts.append("Participation is neutral.")

        return " ".join(parts)

    def _sector_section(
        self,
        analysis: BreadthAnalysis,
        sector: Any,
    ) -> str:
        parts: list[str] = ["Sector Leadership:"]

        if analysis.leading_sectors:
            parts.append(f"Leading: {', '.join(analysis.leading_sectors)}.")
        if analysis.lagging_sectors:
            parts.append(f"Lagging: {', '.join(analysis.lagging_sectors)}.")

        if sector.rotation_detected:
            parts.append("Rotation detected — capital is rotating between sectors.")

        if not analysis.leading_sectors and not analysis.lagging_sectors:
            parts.append("No sector data available.")

        return " ".join(parts)

    def _health_section(self, analysis: BreadthAnalysis) -> str:
        parts: list[str] = ["Market Health:"]

        health_map = {
            "healthy": (
                "Breadth confirms price action. Market internals are supportive."
            ),
            "unhealthy": (
                "Breadth does not confirm price action. "
                "Market internals suggest caution."
            ),
            "divergent": (
                "Divergence between price and breadth. "
                "Current price levels may not be sustainable."
            ),
            "neutral": (
                "Breadth is neither confirming nor contradicting price action."
            ),
        }
        parts.append(
            health_map.get(
                analysis.market_health,
                "Market health cannot be determined.",
            )
        )

        return " ".join(parts)

    def _institutional_section(self, analysis: BreadthAnalysis) -> str:
        parts: list[str] = ["Institutional Interpretation:"]

        bias = analysis.breadth_bias

        if bias is BreadthBias.BULLISH:
            parts.append(
                "Breadth supports bullish positioning. "
                "Broad participation confirms institutional accumulation."
            )
        elif bias is BreadthBias.BEARISH:
            parts.append(
                "Breadth supports bearish positioning. "
                "Weak internals suggest institutional distribution."
            )
        elif bias is BreadthBias.NEUTRAL:
            parts.append(
                "Breadth is neutral. No strong institutional conviction from internals."
            )
        else:
            parts.append(
                "Breadth context is inconclusive. Cross-reference "
                "with market structure and volume."
            )

        if analysis.divergence_detected:
            parts.append(
                "Divergence between breadth and price suggests "
                "the move lacks broad support."
            )

        if analysis.confidence < CONFIDENCE_LOW:
            parts.append(
                "Low confidence suggests limited symbol coverage. "
                "Interpret with caution."
            )

        return " ".join(parts)

    # ------------------------------------------------------------------
    # Empty / fallback analysis
    # ------------------------------------------------------------------

    def _empty_analysis(self, reason: str) -> BreadthAnalysis:
        analysis = BreadthAnalysis.neutral_placeholder()
        object.__setattr__(analysis, "warnings", (reason,))
        explanation = BreadthExplanation(
            overall_breadth="Breadth assessment unavailable: insufficient data.",
            advance_decline="A/D analysis unavailable: insufficient data.",
            participation="Participation analysis unavailable: insufficient data.",
            sector_leadership="Sector analysis unavailable: insufficient data.",
            market_health="Market health unavailable: insufficient data.",
            institutional_interpretation="Institutional "
            "Interpretation: Breadth data is unavailable.",
        )
        object.__setattr__(analysis, "explanation", explanation)
        return analysis
