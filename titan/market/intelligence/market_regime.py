"""Market Regime Intelligence Engine — Orchestrator.

Synthesises Market Structure, VWAP, Volume, and Breadth intelligence
into a unified institutional assessment of the current market
environment. Pure synthesizer — no market calculations.

Integrates with:
  - Market Structure Intelligence
  - VWAP Intelligence
  - Volume Intelligence
  - Breadth Intelligence
  - Evidence Engine
  - Intelligence Fusion Engine
"""

from typing import Any

from titan.core.evidence import (
    Confidence,
    Evidence,
    EvidenceCategory,
    EvidenceSignal,
    Score,
)

from titan.market.intelligence.models import (
    BreadthAnalysis,
    DecisionContext,
    MarketRegime,
    MarketRegimeAnalysis,
    MarketRegimeExplanation,
    MarketStructureAnalysis,
    ParticipationRegime,
    TrendRegime,
    VolumeAnalysis,
    VWAPAnalysis,
)
from titan.market.intelligence.participation_regime import (
    ParticipationRegimeAnalyzer,
)
from titan.market.intelligence.strategy_suitability import (
    StrategySuitabilityAnalyzer,
)
from titan.market.intelligence.trend_regime import TrendRegimeAnalyzer

POSITIVE_SCORE = 65.0
NEGATIVE_SCORE = 35.0
NEUTRAL_SCORE = 50.0

CONFIDENCE_HIGH = 0.7
CONFIDENCE_MODERATE = 0.5
CONFIDENCE_LOW = 0.3

TREND_STRENGTH_HIGH = 0.6
TREND_STRENGTH_MODERATE = 0.35


class MarketRegimeAnalyzer:
    """Orchestrate Market Regime Intelligence.

    Consumes MarketStructureAnalysis, VWAPAnalysis, VolumeAnalysis,
    and BreadthAnalysis and delegates to TrendRegimeAnalyzer,
    ParticipationRegimeAnalyzer, and StrategySuitabilityAnalyzer to
    produce a unified institutional assessment of the market regime.
    Pure synthesizer — does not perform any market calculations.
    """

    name = "MarketRegimeAnalyzer"

    def __init__(
        self,
        trend_analyzer: TrendRegimeAnalyzer | None = None,
        participation_analyzer: ParticipationRegimeAnalyzer | None = None,
        strategy_analyzer: StrategySuitabilityAnalyzer | None = None,
    ) -> None:
        self._trend = trend_analyzer or TrendRegimeAnalyzer()
        self._participation = participation_analyzer or ParticipationRegimeAnalyzer()
        self._strategy = strategy_analyzer or StrategySuitabilityAnalyzer()

    def analyze(
        self,
        market_structure: MarketStructureAnalysis | None = None,
        vwap: VWAPAnalysis | None = None,
        volume: VolumeAnalysis | None = None,
        breadth: BreadthAnalysis | None = None,
    ) -> MarketRegimeAnalysis:
        """Execute market regime intelligence.

        Args:
            market_structure: Market structure intelligence output.
            vwap: VWAP intelligence output.
            volume: Volume intelligence output.
            breadth: Breadth intelligence output.

        Returns:
            Combined MarketRegimeAnalysis.
        """

        if all(x is None for x in (market_structure, vwap, volume, breadth)):
            return self._empty_analysis("No intelligence inputs provided.")

        trend = self._trend.analyze(market_structure, vwap)
        participation = self._participation.analyze(volume, breadth)
        regime = self._determine_regime(trend, participation, market_structure)
        strategy = self._strategy.analyze(
            trend, participation, regime, market_structure
        )
        decision = self._decision_context(regime, trend, strategy)
        health = self._market_health(participation, breadth)
        confidence = self._calculate_confidence(
            trend, participation, strategy, market_structure, vwap, volume, breadth
        )

        analysis = MarketRegimeAnalysis(
            market_regime=regime,
            trend_strength=trend.strength,
            participation_quality=participation.quality,
            institutional_confirmation=participation.institutional_confirmation,
            market_health=health,
            preferred_strategy=strategy.preferred,
            decision_context=decision,
            trend=trend,
            participation=participation,
            strategy=strategy,
            confidence=confidence,
            warnings=self._combine_warnings(
                trend, participation, strategy, market_structure
            ),
            metadata=self._metadata(market_structure, vwap, volume, breadth),
        )

        evidence = self._to_evidence(analysis)
        explanation = self._explanation(analysis, trend, participation, strategy)

        object.__setattr__(analysis, "evidence", evidence)
        object.__setattr__(analysis, "explanation", explanation)

        return analysis

    # ------------------------------------------------------------------
    # Regime determination
    # ------------------------------------------------------------------

    def _determine_regime(
        self,
        trend: TrendRegime,
        participation: ParticipationRegime,
        ms: MarketStructureAnalysis | None,
    ) -> MarketRegime:
        if ms is None:
            return MarketRegime.UNKNOWN

        if trend.direction.value == "unknown":
            return MarketRegime.UNKNOWN

        if ms.structure_state.value == "trending":
            if trend.direction.value == "bullish":
                if participation.expanding:
                    return MarketRegime.BREAKOUT
                return MarketRegime.TRENDING_BULLISH
            elif trend.direction.value == "bearish":
                if participation.expanding:
                    return MarketRegime.BREAKDOWN
                return MarketRegime.TRENDING_BEARISH

        if ms.structure_state.value == "ranging":
            if participation.compressed:
                return MarketRegime.COMPRESSION
            if participation.expanding:
                return MarketRegime.EXPANSION
            return MarketRegime.RANGING

        if ms.structure_state.value == "transition":
            return MarketRegime.TRANSITION

        return MarketRegime.MIXED

    # ------------------------------------------------------------------
    # Decision context
    # ------------------------------------------------------------------

    def _decision_context(
        self,
        regime: MarketRegime,
        trend: TrendRegime,
        strategy: Any,
    ) -> DecisionContext:
        bullish_regimes = (
            MarketRegime.TRENDING_BULLISH,
            MarketRegime.BREAKOUT,
            MarketRegime.EXPANSION,
        )
        bearish_regimes = (
            MarketRegime.TRENDING_BEARISH,
            MarketRegime.BREAKDOWN,
        )
        long_vol_regimes = (
            MarketRegime.TRENDING_BULLISH,
            MarketRegime.TRENDING_BEARISH,
            MarketRegime.BREAKOUT,
            MarketRegime.BREAKDOWN,
            MarketRegime.EXPANSION,
            MarketRegime.TRANSITION,
        )
        short_vol_regimes = (
            MarketRegime.RANGING,
            MarketRegime.COMPRESSION,
        )

        favorable_long = regime in bullish_regimes
        favorable_short = regime in bearish_regimes
        favorable_option_buying = regime in long_vol_regimes
        favorable_option_selling = regime in short_vol_regimes

        score = self._overall_score(regime, trend, favorable_long, favorable_short)

        return DecisionContext(
            favorable_for_long=favorable_long,
            favorable_for_short=favorable_short,
            favorable_for_option_buying=favorable_option_buying,
            favorable_for_option_selling=favorable_option_selling,
            preferred_strategy=strategy.preferred,
            avoid_breakouts=strategy.avoid_breakouts,
            avoid_mean_reversion=strategy.avoid_mean_reversion,
            overall_score=score,
            confidence=trend.confidence,
        )

    def _overall_score(
        self,
        regime: MarketRegime,
        trend: TrendRegime,
        favorable_long: bool,
        favorable_short: bool,
    ) -> float:
        if regime is MarketRegime.UNKNOWN:
            return 50.0

        score = 50.0

        if favorable_long and trend.strength >= TREND_STRENGTH_HIGH:
            score += 20.0
        elif favorable_long and trend.strength >= TREND_STRENGTH_MODERATE:
            score += 10.0

        if favorable_short and trend.strength >= TREND_STRENGTH_HIGH:
            score -= 20.0
        elif favorable_short and trend.strength >= TREND_STRENGTH_MODERATE:
            score -= 10.0

        if regime is MarketRegime.MIXED:
            score = 30.0

        return max(0.0, min(100.0, score))

    # ------------------------------------------------------------------
    # Market health
    # ------------------------------------------------------------------

    def _market_health(
        self,
        participation: ParticipationRegime,
        breadth: BreadthAnalysis | None,
    ) -> str:
        if participation.quality == "strong":
            return "healthy"
        if participation.quality == "low":
            return "unhealthy"
        if breadth is not None and breadth.divergence_detected:
            return "divergent"
        return "neutral"

    # ------------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------------

    def _calculate_confidence(
        self,
        trend: TrendRegime,
        participation: ParticipationRegime,
        strategy: Any,
        ms: MarketStructureAnalysis | None,
        vwap: VWAPAnalysis | None,
        volume: VolumeAnalysis | None,
        breadth: BreadthAnalysis | None,
    ) -> float:
        confidences: list[float] = []
        weights: list[float] = []

        if trend.confidence > 0:
            confidences.append(trend.confidence)
            weights.append(0.30)

        if participation.confidence > 0:
            confidences.append(participation.confidence)
            weights.append(0.25)

        if strategy.confidence > 0:
            confidences.append(strategy.confidence)
            weights.append(0.15)

        for analysis, w in [
            (ms, 0.10),
            (vwap, 0.10),
            (volume, 0.05),
            (breadth, 0.05),
        ]:
            if analysis is not None and analysis.confidence > 0:
                confidences.append(analysis.confidence)
                weights.append(w)

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
        trend: TrendRegime,
        participation: ParticipationRegime,
        strategy: Any,
        ms: MarketStructureAnalysis | None,
    ) -> tuple[str, ...]:
        combined: list[str] = []

        if trend.confidence < CONFIDENCE_LOW:
            combined.append("Low trend regime confidence.")

        if participation.confidence < CONFIDENCE_LOW:
            combined.append("Low participation regime confidence.")

        if strategy.confidence < CONFIDENCE_LOW:
            combined.append("Low strategy suitability confidence.")

        if ms is not None and ms.confidence < CONFIDENCE_LOW:
            combined.append("Low market structure confidence.")

        return tuple(combined)

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def _metadata(
        self,
        ms: MarketStructureAnalysis | None,
        vwap: VWAPAnalysis | None,
        volume: VolumeAnalysis | None,
        breadth: BreadthAnalysis | None,
    ) -> dict[str, Any]:
        return {
            "analyzer": self.name,
            "inputs": {
                "market_structure": ms is not None,
                "vwap": vwap is not None,
                "volume": volume is not None,
                "breadth": breadth is not None,
            },
        }

    # ------------------------------------------------------------------
    # Evidence generation
    # ------------------------------------------------------------------

    def _evidence_signal(self, regime: MarketRegime) -> EvidenceSignal:
        mapping: dict[MarketRegime, EvidenceSignal] = {
            MarketRegime.TRENDING_BULLISH: EvidenceSignal.BULLISH,
            MarketRegime.BREAKOUT: EvidenceSignal.BULLISH,
            MarketRegime.EXPANSION: EvidenceSignal.BULLISH,
            MarketRegime.TRENDING_BEARISH: EvidenceSignal.BEARISH,
            MarketRegime.BREAKDOWN: EvidenceSignal.BEARISH,
            MarketRegime.RANGING: EvidenceSignal.NEUTRAL,
            MarketRegime.COMPRESSION: EvidenceSignal.NEUTRAL,
            MarketRegime.TRANSITION: EvidenceSignal.NEUTRAL,
            MarketRegime.MIXED: EvidenceSignal.NEUTRAL,
        }
        return mapping.get(regime, EvidenceSignal.UNKNOWN)

    def _evidence_score(self, analysis: MarketRegimeAnalysis) -> float:
        base = NEUTRAL_SCORE

        if analysis.market_regime in (
            MarketRegime.TRENDING_BULLISH,
            MarketRegime.BREAKOUT,
            MarketRegime.EXPANSION,
        ):
            base = POSITIVE_SCORE
        elif analysis.market_regime in (
            MarketRegime.TRENDING_BEARISH,
            MarketRegime.BREAKDOWN,
        ):
            base = NEGATIVE_SCORE

        adj = 0.0
        if analysis.institutional_confirmation:
            adj += 5.0
        if analysis.confidence >= CONFIDENCE_HIGH:
            adj += 5.0
        elif analysis.confidence >= CONFIDENCE_MODERATE:
            adj += 3.0

        return max(0.0, min(100.0, base + adj))

    def _evidence_reasons(
        self,
        analysis: MarketRegimeAnalysis,
    ) -> tuple[str, ...]:
        reasons: list[str] = []

        reasons.append(f"Market regime is {analysis.market_regime.value}.")
        reasons.append(f"Trend strength: {analysis.trend_strength:.2f}.")
        reasons.append(f"Participation quality: {analysis.participation_quality}.")

        if analysis.institutional_confirmation:
            reasons.append("Institutional confirmation detected.")

        reasons.append(f"Preferred strategy: {analysis.preferred_strategy.value}.")

        return tuple(reasons)

    def _to_evidence(
        self,
        analysis: MarketRegimeAnalysis,
    ) -> Evidence:
        signal = self._evidence_signal(analysis.market_regime)
        score = self._evidence_score(analysis)
        confidence = analysis.confidence

        return Evidence(
            source="Market Regime",
            category=EvidenceCategory.MARKET_REGIME,
            signal=signal,
            score=Score(score),
            confidence=Confidence(confidence),
            weight=1.0,
            reasons=self._evidence_reasons(analysis),
            warnings=analysis.warnings,
            metadata={
                "analyzer": self.name,
                "regime": analysis.market_regime.value,
                "trend_strength": analysis.trend_strength,
                "participation_quality": analysis.participation_quality,
                "institutional_confirmation": (analysis.institutional_confirmation),
                "preferred_strategy": analysis.preferred_strategy.value,
                "favorable_long": (
                    analysis.decision_context.favorable_for_long
                    if analysis.decision_context
                    else False
                ),
                "favorable_short": (
                    analysis.decision_context.favorable_for_short
                    if analysis.decision_context
                    else False
                ),
            },
        )

    # ------------------------------------------------------------------
    # Explanation generation
    # ------------------------------------------------------------------

    def _explanation(
        self,
        analysis: MarketRegimeAnalysis,
        trend: TrendRegime,
        participation: ParticipationRegime,
        strategy: Any,
    ) -> MarketRegimeExplanation:
        return MarketRegimeExplanation(
            overall_regime=self._regime_section(analysis),
            trend_assessment=self._trend_section(analysis, trend),
            participation_assessment=self._participation_section(
                analysis, participation
            ),
            institutional_confirmation=self._confirmation_section(
                analysis, participation
            ),
            preferred_strategy=self._strategy_section(analysis),
            risk_assessment=self._risk_section(analysis),
        )

    def _regime_section(self, analysis: MarketRegimeAnalysis) -> str:
        return (
            f"Market Regime: {analysis.market_regime.value}. "
            f"Market health: {analysis.market_health}."
        )

    def _trend_section(
        self,
        analysis: MarketRegimeAnalysis,
        trend: TrendRegime,
    ) -> str:
        parts: list[str] = ["Trend Assessment:"]

        parts.append(
            f"Trend direction is {trend.direction.value} "
            f"(strength: {trend.strength:.2f})."
        )

        if trend.aligned:
            parts.append("Price trend and VWAP are aligned.")
        else:
            parts.append("Price trend and VWAP are diverging.")

        if trend.momentum_environment:
            parts.append("Momentum conditions favourable.")
        if trend.mean_reversion_environment:
            parts.append("Mean reversion conditions present.")

        return " ".join(parts)

    def _participation_section(
        self,
        analysis: MarketRegimeAnalysis,
        participation: ParticipationRegime,
    ) -> str:
        parts: list[str] = ["Participation Assessment:"]

        parts.append(f"Participation quality is {participation.quality}.")

        if participation.compressed:
            parts.append("Market is compressed.")
        if participation.expanding:
            parts.append("Market is expanding.")

        return " ".join(parts)

    def _confirmation_section(
        self,
        analysis: MarketRegimeAnalysis,
        participation: ParticipationRegime,
    ) -> str:
        if participation.institutional_confirmation:
            return (
                "Institutional Confirmation: Volume and breadth "
                "confirm the current price move."
            )
        return (
            "Institutional Confirmation: No strong confirmation "
            "from volume or breadth."
        )

    def _strategy_section(self, analysis: MarketRegimeAnalysis) -> str:
        return (
            f"Preferred Strategy: {analysis.preferred_strategy.value}. "
            f"{'Avoid breakout trades.' if analysis.strategy and analysis.strategy.avoid_breakouts else ''}"
            f"{'Avoid mean reversion trades.' if analysis.strategy and analysis.strategy.avoid_mean_reversion else ''}"
        )

    def _risk_section(self, analysis: MarketRegimeAnalysis) -> str:
        parts: list[str] = ["Risk Assessment:"]

        if analysis.market_regime in (
            MarketRegime.TRENDING_BULLISH,
            MarketRegime.EXPANSION,
        ):
            parts.append(
                "Environment favours long positions with " "trend confirmation."
            )
        elif analysis.market_regime in (
            MarketRegime.TRENDING_BEARISH,
            MarketRegime.BREAKDOWN,
        ):
            parts.append(
                "Environment favours short positions with " "trend confirmation."
            )
        elif analysis.market_regime is MarketRegime.RANGING:
            parts.append(
                "Environment favours range-bound approaches. " "Avoid trend following."
            )
        elif analysis.market_regime is MarketRegime.MIXED:
            parts.append("Conflicting signals. Reduced position sizing " "advised.")
        else:
            parts.append(
                "Risk environment is unclear. " "Prioritise capital preservation."
            )

        return " ".join(parts)

    # ------------------------------------------------------------------
    # Empty / fallback analysis
    # ------------------------------------------------------------------

    def _empty_analysis(self, reason: str) -> MarketRegimeAnalysis:
        analysis = MarketRegimeAnalysis.neutral_placeholder()
        object.__setattr__(analysis, "warnings", (reason,))
        explanation = MarketRegimeExplanation(
            overall_regime="Regime assessment unavailable: " "insufficient data.",
            trend_assessment="Trend assessment unavailable: " "insufficient data.",
            participation_assessment="Participation assessment "
            "unavailable: insufficient data.",
            institutional_confirmation="Institutional confirmation "
            "unavailable: insufficient data.",
            preferred_strategy="Strategy assessment unavailable: " "insufficient data.",
            risk_assessment="Risk Assessment: Market regime " "data is unavailable.",
        )
        object.__setattr__(analysis, "explanation", explanation)
        return analysis
