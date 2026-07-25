"""Market Structure Intelligence Engine Orchestrator.

Provides institutional market structure analysis from supplied price data.
Identifies trends, swing points, support/resistance levels, and structure
breaks (BOS, CHOCH).

Pure orchestrator — no broker imports, no API calls.

Integrates with:
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
    BreakType,
    MarketStructureAnalysis,
    MarketStructureExplanation,
    StructureState,
    SupportResistanceStructure,
    SwingStructure,
    TrendDirection,
    TrendStructure,
)
from titan.market.intelligence.support_resistance import (
    SupportResistanceAnalyzer,
)
from titan.market.intelligence.swing import SwingAnalyzer
from titan.market.intelligence.trend import TrendAnalyzer
from titan.market.series import MarketDataSeries

POSITIVE_SCORE = 65.0
NEGATIVE_SCORE = 35.0
NEUTRAL_SCORE = 50.0

CONFIDENCE_LOW = 0.3
CONFIDENCE_MODERATE = 0.5
CONFIDENCE_HIGH = 0.7


class MarketStructureAnalyzer:
    """Orchestrate market structure intelligence.

    Consumes MarketDataSeries and delegates to TrendAnalyzer,
    SwingAnalyzer, and SupportResistanceAnalyzer to produce a unified
    institutional assessment of market structure.  Pure orchestrator —
    does not recalculate any price metric.
    """

    name = "MarketStructureAnalyzer"

    def __init__(
        self,
        trend_analyzer: TrendAnalyzer | None = None,
        swing_analyzer: SwingAnalyzer | None = None,
        sr_analyzer: SupportResistanceAnalyzer | None = None,
    ) -> None:
        self._trend = trend_analyzer or TrendAnalyzer()
        self._swing = swing_analyzer or SwingAnalyzer()
        self._sr = sr_analyzer or SupportResistanceAnalyzer()

    def analyze(
        self,
        series: MarketDataSeries,
    ) -> MarketStructureAnalysis:
        """Execute market structure analysis.

        Args:
            series: Market data series with OHLCV candles.

        Returns:
            Combined MarketStructureAnalysis.
        """

        if len(series) < 5:
            return self._empty_analysis(
                f"Insufficient data: need at least 5 candles, got {len(series)}."
            )

        trend = self._trend.analyze(series)
        swing = self._swing.analyze(series)
        sr = self._sr.analyze(series, swing=swing)

        structure_state = self._determine_structure_state(trend, swing)
        support_levels = sr.support_levels
        resistance_levels = sr.resistance_levels
        trend_strength = trend.strength
        confidence = self._calculate_confidence(trend, swing, sr)

        analysis = MarketStructureAnalysis(
            primary_trend=trend.primary,
            secondary_trend=trend.secondary,
            structure_state=structure_state,
            support_levels=support_levels,
            resistance_levels=resistance_levels,
            trend_strength=trend_strength,
            confidence=confidence,
            warnings=self._combine_warnings(series, trend, swing, sr),
            metadata=self._metadata(series, trend, swing, sr),
        )

        evidence = self._to_evidence(analysis, trend, swing)
        explanation = self._explanation(analysis, trend, swing, sr)

        object.__setattr__(analysis, "evidence", evidence)
        object.__setattr__(analysis, "explanation", explanation)

        return analysis

    # ------------------------------------------------------------------
    # Structure state determination
    # ------------------------------------------------------------------

    def _determine_structure_state(
        self,
        trend: TrendStructure,
        swing: SwingStructure,
    ) -> StructureState:
        if trend.primary is TrendDirection.UNKNOWN:
            return StructureState.UNKNOWN

        if swing.break_type is BreakType.CHOCH:
            return StructureState.TRANSITION

        if trend.primary is TrendDirection.SIDEWAYS:
            if swing.break_type is BreakType.NONE:
                return StructureState.RANGING
            return StructureState.TRANSITION

        if trend.strength >= CONFIDENCE_MODERATE:
            return StructureState.TRENDING

        if trend.strength >= CONFIDENCE_LOW:
            if swing.break_type is not BreakType.NONE:
                return StructureState.TRANSITION
            return StructureState.RANGING

        return StructureState.UNKNOWN

    # ------------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------------

    def _calculate_confidence(
        self,
        trend: TrendStructure,
        swing: SwingStructure,
        sr: SupportResistanceStructure,
    ) -> float:
        confidences: list[float] = []
        weights: list[float] = []

        if trend.confidence > 0:
            confidences.append(trend.confidence)
            weights.append(0.4)

        if swing.confidence > 0:
            confidences.append(swing.confidence)
            weights.append(0.35)

        if sr.confidence > 0:
            confidences.append(sr.confidence)
            weights.append(0.25)

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
        trend: TrendStructure,
        swing: SwingStructure,
        sr: SupportResistanceStructure,
    ) -> tuple[str, ...]:
        combined: list[str] = []

        if len(series) < 50:
            combined.append(
                f"Limited data: {len(series)} candle(s). "
                "Trend analysis may be unreliable."
            )

        if trend.confidence < CONFIDENCE_LOW:
            combined.append("Low trend confidence.")

        if swing.confidence < CONFIDENCE_LOW:
            combined.append("Low swing analysis confidence.")

        return tuple(combined)

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def _metadata(
        self,
        series: MarketDataSeries,
        trend: TrendStructure,
        swing: SwingStructure,
        sr: SupportResistanceStructure,
    ) -> dict[str, Any]:
        return {
            "analyzer": self.name,
            "candle_count": len(series),
            "trend_strength": trend.strength,
            "swing_count": len(swing.swing_highs) + len(swing.swing_lows),
            "structure_break": swing.break_type.value,
            "support_levels_count": len(sr.support_levels),
            "resistance_levels_count": len(sr.resistance_levels),
        }

    # ------------------------------------------------------------------
    # Evidence generation
    # ------------------------------------------------------------------

    def _evidence_signal(
        self,
        trend: TrendStructure,
    ) -> EvidenceSignal:
        mapping = {
            TrendDirection.BULLISH: EvidenceSignal.BULLISH,
            TrendDirection.BEARISH: EvidenceSignal.BEARISH,
            TrendDirection.SIDEWAYS: EvidenceSignal.NEUTRAL,
        }
        return mapping.get(trend.primary, EvidenceSignal.UNKNOWN)

    def _evidence_score(
        self,
        analysis: MarketStructureAnalysis,
    ) -> float:
        base = NEUTRAL_SCORE

        if analysis.primary_trend is TrendDirection.BULLISH:
            base = POSITIVE_SCORE
        elif analysis.primary_trend is TrendDirection.BEARISH:
            base = NEGATIVE_SCORE

        adj = 0.0
        if analysis.trend_strength >= CONFIDENCE_HIGH:
            adj += 5.0
        elif analysis.trend_strength >= CONFIDENCE_MODERATE:
            adj += 3.0

        return max(0.0, min(100.0, base + adj))

    def _evidence_reasons(
        self,
        analysis: MarketStructureAnalysis,
        trend: TrendStructure,
        swing: SwingStructure,
    ) -> tuple[str, ...]:
        reasons: list[str] = []

        reasons.append(f"Primary trend is {analysis.primary_trend.value}.")
        reasons.append(f"Market structure state is {analysis.structure_state.value}.")
        reasons.append(f"Trend strength: {analysis.trend_strength:.2f}.")

        if swing.break_type is BreakType.BOS:
            reasons.append("Break of Structure (BOS) detected.")
        elif swing.break_type is BreakType.CHOCH:
            reasons.append("Change of Character (CHOCH) detected.")

        if analysis.support_levels:
            reasons.append(
                f"Support levels: "
                f"{', '.join(f'{v:.2f}' for v in analysis.support_levels)}."
            )
        if analysis.resistance_levels:
            reasons.append(
                f"Resistance levels: "
                f"{', '.join(f'{v:.2f}' for v in analysis.resistance_levels)}."
            )

        return tuple(reasons)

    def _to_evidence(
        self,
        analysis: MarketStructureAnalysis,
        trend: TrendStructure,
        swing: SwingStructure,
    ) -> Evidence:
        signal = self._evidence_signal(trend)
        score = self._evidence_score(analysis)
        confidence = analysis.confidence

        return Evidence(
            source="Market Structure",
            category=EvidenceCategory.MARKET_STRUCTURE,
            signal=signal,
            score=Score(score),
            confidence=Confidence(confidence),
            weight=1.0,
            reasons=self._evidence_reasons(analysis, trend, swing),
            warnings=analysis.warnings,
            metadata={
                "analyzer": self.name,
                "primary_trend": analysis.primary_trend.value,
                "secondary_trend": analysis.secondary_trend.value,
                "structure_state": analysis.structure_state.value,
                "trend_strength": analysis.trend_strength,
                "support_count": len(analysis.support_levels),
                "resistance_count": len(analysis.resistance_levels),
            },
        )

    # ------------------------------------------------------------------
    # Explanation generation
    # ------------------------------------------------------------------

    def _explanation(
        self,
        analysis: MarketStructureAnalysis,
        trend: TrendStructure,
        swing: SwingStructure,
        sr: SupportResistanceStructure,
    ) -> MarketStructureExplanation:
        return MarketStructureExplanation(
            trend=self._trend_section(analysis, trend),
            swings=self._swing_section(swing),
            support=self._support_section(sr),
            resistance=self._resistance_section(sr),
            structure=self._structure_section(analysis),
            institutional_interpretation=self._institutional_section(analysis),
        )

    def _trend_section(
        self,
        analysis: MarketStructureAnalysis,
        trend: TrendStructure,
    ) -> str:
        parts: list[str] = ["Trend Assessment:"]

        if analysis.primary_trend is TrendDirection.BULLISH:
            parts.append("Primary trend is bullish.")
            if analysis.secondary_trend is TrendDirection.BULLISH:
                parts.append("Both primary and secondary trends are aligned bullish.")
            elif analysis.secondary_trend is TrendDirection.BEARISH:
                parts.append("Secondary trend is bearish — potential pullback.")
            else:
                parts.append("Secondary trend is sideways — consolidation.")
        elif analysis.primary_trend is TrendDirection.BEARISH:
            parts.append("Primary trend is bearish.")
            if analysis.secondary_trend is TrendDirection.BEARISH:
                parts.append("Both primary and secondary trends are aligned bearish.")
            elif analysis.secondary_trend is TrendDirection.BULLISH:
                parts.append("Secondary trend is bullish — potential rally.")
            else:
                parts.append("Secondary trend is sideways — consolidation.")
        elif analysis.primary_trend is TrendDirection.SIDEWAYS:
            parts.append("Primary trend is sideways. Market is ranging.")
        else:
            parts.append("Trend cannot be determined from available data.")

        if analysis.trend_strength >= CONFIDENCE_HIGH:
            parts.append("Trend strength is high.")
        elif analysis.trend_strength >= CONFIDENCE_MODERATE:
            parts.append("Trend strength is moderate.")
        elif analysis.trend_strength >= CONFIDENCE_LOW:
            parts.append("Trend strength is low.")

        return " ".join(parts)

    def _swing_section(self, swing: SwingStructure) -> str:
        parts: list[str] = ["Swing Analysis:"]

        parts.append(
            f"Identified {len(swing.swing_highs)} swing high(s) and "
            f"{len(swing.swing_lows)} swing low(s)."
        )

        if swing.higher_highs and swing.higher_lows:
            parts.append("Higher highs and higher lows confirm uptrend structure.")
        elif swing.lower_highs and swing.lower_lows:
            parts.append("Lower highs and lower lows confirm downtrend structure.")
        elif swing.higher_highs and swing.lower_lows:
            parts.append("Divergent structure: higher highs with lower lows.")
        elif swing.lower_highs and swing.higher_lows:
            parts.append("Divergent structure: lower highs with higher lows.")

        if swing.break_type is BreakType.BOS:
            parts.append(
                "Break of Structure (BOS) detected — trend continuation likely."
            )
        elif swing.break_type is BreakType.CHOCH:
            parts.append(
                "Change of Character (CHOCH) detected — potential trend reversal."
            )

        return " ".join(parts)

    def _support_section(
        self,
        sr: SupportResistanceStructure,
    ) -> str:
        parts: list[str] = ["Support Levels:"]

        if sr.support_levels:
            levels_str = ", ".join(f"{v:.2f}" for v in sr.support_levels)
            parts.append(f"Key support at {levels_str}.")
        else:
            parts.append("No significant support levels identified.")

        if sr.confidence >= CONFIDENCE_MODERATE:
            parts.append("Confidence in support levels is moderate to high.")
        elif sr.confidence >= CONFIDENCE_LOW:
            parts.append("Confidence in support levels is low.")

        return " ".join(parts)

    def _resistance_section(
        self,
        sr: SupportResistanceStructure,
    ) -> str:
        parts: list[str] = ["Resistance Levels:"]

        if sr.resistance_levels:
            levels_str = ", ".join(f"{v:.2f}" for v in sr.resistance_levels)
            parts.append(f"Key resistance at {levels_str}.")
        else:
            parts.append("No significant resistance levels identified.")

        if sr.confidence >= CONFIDENCE_MODERATE:
            parts.append("Confidence in resistance levels is moderate to high.")
        elif sr.confidence >= CONFIDENCE_LOW:
            parts.append("Confidence in resistance levels is low.")

        return " ".join(parts)

    def _structure_section(
        self,
        analysis: MarketStructureAnalysis,
    ) -> str:
        parts: list[str] = ["Market Structure:"]

        state = analysis.structure_state

        if state is StructureState.TRENDING:
            parts.append(
                "Market is in a clear trend. Price is making "
                "directional progress with defined swing structure."
            )
        elif state is StructureState.RANGING:
            parts.append(
                "Market is ranging between support and resistance. "
                "No clear directional bias."
            )
        elif state is StructureState.TRANSITION:
            parts.append(
                "Market is in transition. Structure is breaking "
                "and a new trend may be emerging."
            )
        else:
            parts.append(
                "Market structure cannot be determined from " "available data."
            )

        return " ".join(parts)

    def _institutional_section(
        self,
        analysis: MarketStructureAnalysis,
    ) -> str:
        parts: list[str] = ["Institutional Interpretation:"]

        trend = analysis.primary_trend
        state = analysis.structure_state
        strength = analysis.trend_strength

        if state is StructureState.TRENDING and strength >= CONFIDENCE_MODERATE:
            direction = "bullish" if trend is TrendDirection.BULLISH else "bearish"
            parts.append(
                f"Market exhibits a strong {direction} trend with "
                f"clear swing structure. Trend-following approaches "
                f"are favoured."
            )
        elif state is StructureState.RANGING:
            parts.append(
                "Market is range-bound. Mean-reversion approaches "
                "are favoured. Monitor for structure breaks that "
                "may signal trend emergence."
            )
        elif state is StructureState.TRANSITION:
            parts.append(
                "Market structure is transitioning. Trend-following "
                "approaches carry elevated risk. Wait for structure "
                "confirmation before committing to directional bias."
            )
        else:
            parts.append(
                "Market structure is insufficiently characterised. "
                "Cross-reference with other market intelligence."
            )

        if analysis.confidence < CONFIDENCE_LOW:
            parts.append(
                "Low confidence suggests limited data availability. "
                "Interpret with caution."
            )

        return " ".join(parts)

    # ------------------------------------------------------------------
    # Empty / fallback analysis
    # ------------------------------------------------------------------

    def _empty_analysis(self, reason: str) -> MarketStructureAnalysis:
        analysis = MarketStructureAnalysis.neutral_placeholder()
        object.__setattr__(analysis, "warnings", (reason,))
        explanation = MarketStructureExplanation(
            trend="Trend assessment unavailable: insufficient data.",
            swings="Swing analysis unavailable: insufficient data.",
            support="Support level assessment unavailable: insufficient data.",
            resistance="Resistance level assessment unavailable: insufficient data.",
            structure="Market structure assessment unavailable: insufficient data.",
            institutional_interpretation="Institutional Interpretation: Market structure data is unavailable.",
        )
        object.__setattr__(analysis, "explanation", explanation)
        return analysis
