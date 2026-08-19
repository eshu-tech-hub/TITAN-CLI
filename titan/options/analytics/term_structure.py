from typing import Any

from titan.core.evidence import (
    Confidence,
    Evidence,
    EvidenceCategory,
    EvidenceSignal,
    Score,
)
from titan.options.analytics.backwardation import BackwardationAnalyzer
from titan.options.analytics.calendar import CalendarAnalyzer
from titan.options.analytics.contango import ContangoAnalyzer
from titan.options.analytics.models import (
    BackwardationResult,
    CalendarResult,
    ContangoResult,
    MarketBias,
    TermStructureAnalysis,
    TermStructureExplanation,
    TermStructureShape,
    TermStructureSnapshot,
    TermStructureStrength,
)

NEUTRAL_SCORE = 50.0
SHAPE_FLAT_THRESHOLD = 0.01
SHAPE_CONTANGO_THRESHOLD = 0.03


class TermStructureAnalyzer:
    """Analyze implied volatility term structure across multiple expiries.

    Orchestrates CalendarAnalyzer, ContangoAnalyzer, and
    BackwardationAnalyzer to produce combined institutional-grade
    term structure intelligence.

    Consumes supplied volatility values only.
    Never estimates volatility or interpolates missing data.
    """

    name = "TermStructureAnalyzer"

    def __init__(
        self,
        calendar_analyzer: CalendarAnalyzer | None = None,
        contango_analyzer: ContangoAnalyzer | None = None,
        backwardation_analyzer: BackwardationAnalyzer | None = None,
    ) -> None:
        self._calendar = calendar_analyzer or CalendarAnalyzer()
        self._contango = contango_analyzer or ContangoAnalyzer()
        self._backwardation = backwardation_analyzer or BackwardationAnalyzer()

    def analyze(self, snapshot: TermStructureSnapshot) -> TermStructureAnalysis:
        if not isinstance(snapshot, TermStructureSnapshot):
            raise TypeError("snapshot must be a TermStructureSnapshot.")

        if not snapshot.expiries:
            return self._empty_analysis("No expiry data provided.")

        calendar = self._calendar.analyze(snapshot)
        contango = self._contango.analyze(calendar)
        backwardation = self._backwardation.analyze(calendar)

        shape = self._determine_shape(calendar, contango, backwardation)
        strength = self._determine_strength(calendar, contango, backwardation)
        calendar_bias = self._calendar_bias(shape)
        overall_bias = self._overall_bias(shape, calendar_bias)
        confidence = self._calculate_confidence(calendar, contango, backwardation)
        warnings = self._combine_warnings(calendar, contango, backwardation)

        analysis = TermStructureAnalysis(
            shape=shape,
            strength=strength,
            front_iv=calendar.front_iv,
            back_iv=calendar.back_iv,
            curve_slope=calendar.curve_slope,
            event_premium=calendar.event_premium,
            calendar_bias=calendar_bias,
            overall_bias=overall_bias,
            confidence=confidence,
            warnings=warnings,
            metadata=self._metadata(snapshot, shape, strength, overall_bias),
        )

        evidence = self._to_evidence(analysis, calendar)
        explanation = self._explanation(analysis, calendar, contango, backwardation)

        object.__setattr__(analysis, "evidence", evidence)
        object.__setattr__(analysis, "explanation", explanation)

        return analysis

    def _determine_shape(
        self,
        calendar: CalendarResult,
        contango: ContangoResult,
        backwardation: BackwardationResult,
    ) -> TermStructureShape:
        if calendar.calendar_spread is None:
            return TermStructureShape.UNKNOWN

        spread = calendar.calendar_spread

        if abs(spread) <= SHAPE_FLAT_THRESHOLD:
            return TermStructureShape.FLAT

        if spread > 0:
            if contango.strength in (
                TermStructureStrength.MEDIUM,
                TermStructureStrength.HIGH,
                TermStructureStrength.EXTREME,
            ):
                return TermStructureShape.CONTANGO
            return TermStructureShape.NORMAL

        if backwardation.strength in (
            TermStructureStrength.MEDIUM,
            TermStructureStrength.HIGH,
            TermStructureStrength.EXTREME,
        ):
            return TermStructureShape.INVERTED
        return TermStructureShape.BACKWARDATION

    def _determine_strength(
        self,
        calendar: CalendarResult,
        contango: ContangoResult,
        backwardation: BackwardationResult,
    ) -> TermStructureStrength:
        if contango.is_contango:
            return contango.strength
        if backwardation.is_backwardation:
            return backwardation.strength
        if (
            calendar.calendar_spread is not None
            and abs(calendar.calendar_spread) <= SHAPE_FLAT_THRESHOLD
        ):
            return TermStructureStrength.LOW
        return TermStructureStrength.UNKNOWN

    def _calendar_bias(self, shape: TermStructureShape) -> MarketBias:
        if shape in (TermStructureShape.BACKWARDATION, TermStructureShape.INVERTED):
            return MarketBias.BEARISH
        if shape in (TermStructureShape.NORMAL, TermStructureShape.CONTANGO):
            return MarketBias.NEUTRAL
        if shape is TermStructureShape.FLAT:
            return MarketBias.NEUTRAL
        return MarketBias.UNKNOWN

    def _overall_bias(
        self,
        shape: TermStructureShape,
        calendar_bias: MarketBias,
    ) -> MarketBias:
        return calendar_bias

    def _calculate_confidence(
        self,
        calendar: CalendarResult,
        contango: ContangoResult,
        backwardation: BackwardationResult,
    ) -> float:
        confidences = [calendar.confidence]
        if contango.is_contango:
            confidences.append(contango.confidence)
        if backwardation.is_backwardation:
            confidences.append(backwardation.confidence)

        if not confidences:
            return 0.0
        return sum(confidences) / len(confidences)

    def _combine_warnings(
        self,
        calendar: CalendarResult,
        contango: ContangoResult,
        backwardation: BackwardationResult,
    ) -> tuple[str, ...]:
        combined: list[str] = list(calendar.warnings)
        return tuple(combined)

    def _metadata(
        self,
        snapshot: TermStructureSnapshot,
        shape: TermStructureShape,
        strength: TermStructureStrength,
        overall_bias: MarketBias,
    ) -> dict[str, Any]:
        return {
            "analyzer": self.name,
            "underlying": snapshot.underlying,
            "timestamp": snapshot.timestamp.isoformat() if snapshot.timestamp else None,
            "expiry_count": len(snapshot.expiries),
            "shape": shape.value,
            "strength": strength.value,
            "overall_bias": overall_bias.value,
        }

    # ------------------------------------------------------------------
    # Evidence generation
    # ------------------------------------------------------------------

    def _evidence_signal(self, analysis: TermStructureAnalysis) -> EvidenceSignal:
        if analysis.overall_bias is MarketBias.BEARISH:
            return EvidenceSignal.BEARISH
        if analysis.overall_bias is MarketBias.BULLISH:
            return EvidenceSignal.BULLISH
        if analysis.overall_bias is MarketBias.NEUTRAL:
            return EvidenceSignal.NEUTRAL
        return EvidenceSignal.UNKNOWN

    def _evidence_score(self, analysis: TermStructureAnalysis) -> float:
        base = NEUTRAL_SCORE
        if analysis.shape in (
            TermStructureShape.CONTANGO,
            TermStructureShape.INVERTED,
            TermStructureShape.BACKWARDATION,
        ):
            if analysis.strength in (
                TermStructureStrength.HIGH,
                TermStructureStrength.EXTREME,
            ):
                return base + (analysis.confidence * 40.0)
            return base + (analysis.confidence * 25.0)
        return base

    def _evidence_reasons(
        self,
        analysis: TermStructureAnalysis,
        calendar: CalendarResult,
    ) -> tuple[str, ...]:
        reasons: list[str] = []
        if analysis.shape is not TermStructureShape.UNKNOWN:
            reasons.append(f"Term structure shape is {analysis.shape.value}.")
        if analysis.strength is not TermStructureStrength.UNKNOWN:
            reasons.append(f"Term structure strength is {analysis.strength.value}.")

        if calendar.front_iv is not None and calendar.back_iv is not None:
            reasons.append(
                f"Front IV is {calendar.front_iv:.2%}, "
                f"back IV is {calendar.back_iv:.2%}."
            )
        if calendar.calendar_spread is not None:
            reasons.append(f"Calendar spread is {calendar.calendar_spread:+.4f}.")
        if calendar.curve_slope is not None:
            reasons.append(f"Curve slope is {calendar.curve_slope:+.4f}.")
        if calendar.event_premium is not None:
            reasons.append(f"Event premium detected: {calendar.event_premium:.2%}.")

        return tuple(reasons)

    def _to_evidence(
        self,
        analysis: TermStructureAnalysis,
        calendar: CalendarResult,
    ) -> Evidence:
        return Evidence(
            source="Volatility Term Structure",
            category=EvidenceCategory.OPTION_CHAIN,
            signal=self._evidence_signal(analysis),
            score=Score(self._evidence_score(analysis)),
            confidence=Confidence(analysis.confidence),
            weight=1.0,
            reasons=self._evidence_reasons(analysis, calendar),
            warnings=analysis.warnings,
            metadata={
                "analyzer": self.name,
                "shape": analysis.shape.value,
                "strength": analysis.strength.value,
                "overall_bias": analysis.overall_bias.value,
                "front_iv": calendar.front_iv,
                "back_iv": calendar.back_iv,
                "calendar_spread": calendar.calendar_spread,
                "curve_slope": calendar.curve_slope,
                "event_premium": calendar.event_premium,
            },
        )

    # ------------------------------------------------------------------
    # Explanation generation
    # ------------------------------------------------------------------

    def _explanation(
        self,
        analysis: TermStructureAnalysis,
        calendar: CalendarResult,
        contango: ContangoResult,
        backwardation: BackwardationResult,
    ) -> TermStructureExplanation:
        return TermStructureExplanation(
            curve_shape=self._curve_shape_section(analysis),
            calendar_analysis=self._calendar_section(analysis, calendar),
            slope_interpretation=self._slope_section(analysis, calendar),
            institutional_view=self._institutional_section(analysis),
            risk_assessment=self._risk_section(analysis),
            future_considerations=self._future_section(analysis),
            warnings=analysis.warnings,
        )

    def _curve_shape_section(self, analysis: TermStructureAnalysis) -> str:
        shape_desc = {
            TermStructureShape.NORMAL: (
                "The volatility term structure exhibits a normal "
                "upward-sloping shape. Far-term implied volatility "
                "is moderately higher than near-term."
            ),
            TermStructureShape.CONTANGO: (
                "The volatility term structure is in contango with "
                "a steep upward slope. Far-term implied volatility "
                "is significantly higher than near-term."
            ),
            TermStructureShape.BACKWARDATION: (
                "The volatility term structure is in backwardation. "
                "Near-term implied volatility exceeds far-term, "
                "indicating elevated near-term risk perception."
            ),
            TermStructureShape.INVERTED: (
                "The volatility term structure is sharply inverted. "
                "Near-term implied volatility is substantially higher "
                "than far-term, suggesting acute near-term stress."
            ),
            TermStructureShape.FLAT: (
                "The volatility term structure is flat. Near-term "
                "and far-term implied volatilities are approximately "
                "equal."
            ),
            TermStructureShape.UNKNOWN: (
                "Volatility term structure shape cannot be determined "
                "from available data."
            ),
        }

        base = shape_desc.get(
            analysis.shape,
            "Term structure shape is unavailable.",
        )

        strength_desc = {
            TermStructureStrength.LOW: " The slope magnitude is low.",
            TermStructureStrength.MEDIUM: " The slope magnitude is moderate.",
            TermStructureStrength.HIGH: " The slope magnitude is high.",
            TermStructureStrength.EXTREME: " The slope magnitude is extreme.",
            TermStructureStrength.UNKNOWN: "",
        }

        return base + strength_desc.get(analysis.strength, "")

    def _calendar_section(
        self,
        analysis: TermStructureAnalysis,
        calendar: CalendarResult,
    ) -> str:
        parts: list[str] = ["Calendar Spread Analysis:"]

        if calendar.front_iv is not None and calendar.back_iv is not None:
            parts.append(
                f"Front-month IV is {calendar.front_iv:.2%}, "
                f"back-month IV is {calendar.back_iv:.2%}."
            )
        if calendar.calendar_spread is not None:
            parts.append(
                f"The calendar spread (back - front) is "
                f"{calendar.calendar_spread:+.4f}."
            )
        if calendar.curve_slope is not None:
            parts.append(
                f"Average slope per expiry step is {calendar.curve_slope:+.4f}."
            )
        if calendar.event_premium is not None:
            parts.append(
                f"Event premium of {calendar.event_premium:.2%} detected, "
                f"indicating an expiry with abnormally high IV relative "
                f"to the interpolated curve."
            )
        if calendar.max_discontinuity is not None:
            parts.append(
                f"Maximum discontinuity between consecutive expiries "
                f"is {calendar.max_discontinuity:.4f}."
            )

        return " ".join(parts)

    def _slope_section(
        self,
        analysis: TermStructureAnalysis,
        calendar: CalendarResult,
    ) -> str:
        parts: list[str] = ["Slope Interpretation:"]

        if analysis.shape is TermStructureShape.NORMAL:
            parts.append(
                "The mild upward slope is consistent with standard "
                "volatility term structure, where longer-dated options "
                "carry a risk premium for the additional time horizon."
            )
        elif analysis.shape is TermStructureShape.CONTANGO:
            parts.append(
                "The steep contango indicates a significant premium "
                "for longer-dated volatility. This environment "
                "typically benefits short volatility strategies "
                "with a positive roll yield."
            )
        elif analysis.shape is TermStructureShape.BACKWARDATION:
            parts.append(
                "The mild backwardation suggests near-term "
                "uncertainty is elevated relative to the longer-dated "
                "outlook. This may warrant attention to near-term "
                "event risk."
            )
        elif analysis.shape is TermStructureShape.INVERTED:
            parts.append(
                "The inverted curve signals that market participants "
                "are pricing significant near-term risk. Long "
                "volatility strategies may benefit, while short "
                "volatility positions face elevated risk."
            )
        elif analysis.shape is TermStructureShape.FLAT:
            parts.append(
                "The flat curve suggests no significant premium "
                "is being assigned to any particular time horizon."
            )
        else:
            parts.append("Slope interpretation is unavailable.")

        return " ".join(parts)

    def _institutional_section(self, analysis: TermStructureAnalysis) -> str:
        parts: list[str] = ["Institutional View:"]

        if analysis.shape is TermStructureShape.CONTANGO:
            parts.append(
                "The upward-sloping curve supports premium collection "
                "strategies in the near term. Consider short volatility "
                "or calendar spread strategies that benefit from "
                "time decay and roll yield."
            )
        elif analysis.shape is TermStructureShape.INVERTED:
            parts.append(
                "The inverted curve suggests defensive positioning. "
                "Consider tail-risk hedges and long volatility "
                "strategies to protect against near-term events."
            )
        elif analysis.shape is TermStructureShape.BACKWARDATION:
            parts.append(
                "Mild backwardation warrants monitoring for "
                "escalation. Current positioning should account "
                "for potential near-term volatility expansion."
            )
        elif analysis.shape is TermStructureShape.NORMAL:
            parts.append(
                "The normal term structure is consistent with "
                "orderly markets. Standard volatility strategies "
                "apply with normal risk management parameters."
            )
        elif analysis.shape is TermStructureShape.FLAT:
            parts.append(
                "The flat curve suggests limited term premium. "
                "Directional volatility positioning should focus on "
                "event-driven opportunities rather than carry."
            )

        return " ".join(parts)

    def _risk_section(self, analysis: TermStructureAnalysis) -> str:
        parts: list[str] = ["Risk Assessment:"]

        if analysis.shape in (
            TermStructureShape.INVERTED,
            TermStructureShape.BACKWARDATION,
        ):
            parts.append(
                "Inverted term structure elevates the risk of "
                "near-term volatility expansion. Position sizing "
                "should account for potential gap moves."
            )
            if analysis.strength in (
                TermStructureStrength.HIGH,
                TermStructureStrength.EXTREME,
            ):
                parts.append(
                    "The severity of the inversion warrants "
                    "heightened vigilance. Consider reducing "
                    "short vega exposure."
                )
        elif analysis.shape is TermStructureShape.CONTANGO:
            parts.append(
                "Elevated contango may correct rapidly if "
                "market conditions change. Monitor for curve "
                "flattening as a leading indicator."
            )
        elif analysis.shape is TermStructureShape.NORMAL:
            parts.append(
                "Standard risk management applies. Monitor "
                "for changes in the slope as a potential "
                "leading indicator."
            )
        elif analysis.shape is TermStructureShape.FLAT:
            parts.append(
                "Limited term premium reduces roll-down risk. "
                "Focus on event risk in individual expiries."
            )

        return " ".join(parts)

    def _future_section(self, analysis: TermStructureAnalysis) -> str:
        parts: list[str] = ["Future Considerations:"]

        if analysis.event_premium is not None:
            parts.append(
                f"Event premium of {analysis.event_premium:.2%} detected. "
                "Consider whether specific known events (earnings, "
                "FOMC, data releases) align with the affected expiry."
            )
        if analysis.confidence < 0.3:
            parts.append(
                "Low confidence in term structure analysis. "
                "Cross-reference with other market indicators."
            )
        if analysis.shape is TermStructureShape.UNKNOWN:
            parts.append(
                "Additional expiry data would improve analysis. "
                "Consider requesting data for more tenors."
            )
        else:
            parts.append(
                "Monitor term structure evolution for shifts "
                "in shape and slope as leading indicators."
            )

        return " ".join(parts)

    def _empty_analysis(self, reason: str) -> TermStructureAnalysis:
        analysis = TermStructureAnalysis.neutral_placeholder()
        object.__setattr__(analysis, "warnings", (reason,))
        explanation = TermStructureExplanation(
            curve_shape="Term structure shape is unavailable.",
            calendar_analysis="Calendar analysis is unavailable.",
            slope_interpretation="Slope interpretation is unavailable.",
            institutional_view="Institutional View: Term structure data is unavailable.",
            risk_assessment="Risk Assessment: Term structure data is unavailable.",
            future_considerations="Future Considerations: Term structure data is unavailable.",
            warnings=(reason,),
        )
        object.__setattr__(analysis, "explanation", explanation)
        return analysis
