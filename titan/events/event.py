"""Event Intelligence Engine — Orchestrator.

Provides institutional-grade scheduled event analysis. Synthesises
economic calendar, corporate actions, impact, and risk into a unified
assessment.

Pure orchestrator — no API calls, no broker imports, no news ingestion.

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

from titan.events.calendar import EconomicCalendarAnalyzer
from titan.events.corporate import CorporateEventAnalyzer
from titan.events.impact import ImpactAnalyzer
from titan.events.models import (
    CorporateEvent,
    DecisionContext,
    EconomicEvent,
    EventAnalysis,
    EventExplanation,
    EventImportance,
    EventRisk,
    EventRiskAssessment,
)
from titan.events.risk import EventRiskAnalyzer

POSITIVE_SCORE = 65.0
NEGATIVE_SCORE = 35.0
NEUTRAL_SCORE = 50.0

CONFIDENCE_HIGH = 0.7
CONFIDENCE_MODERATE = 0.5
CONFIDENCE_LOW = 0.3

IMPORTANCE_RANKING: dict[EventImportance, int] = {
    EventImportance.CRITICAL: 4,
    EventImportance.HIGH: 3,
    EventImportance.MEDIUM: 2,
    EventImportance.LOW: 1,
}

RISK_THRESHOLD_HIGH = 0.6
RISK_THRESHOLD_GAP = 0.5
VOL_THRESHOLD_HIGH = 0.5


class EventIntelligenceAnalyzer:
    """Orchestrate Event Intelligence.

    Consumes EconomicEvent and CorporateEvent lists and delegates to
    EconomicCalendarAnalyzer, CorporateEventAnalyzer, ImpactAnalyzer,
    and EventRiskAnalyzer to produce a unified institutional assessment
    of scheduled market events. Pure orchestrator — no external data
    fetching.
    """

    name = "EventIntelligenceAnalyzer"

    def __init__(
        self,
        calendar_analyzer: EconomicCalendarAnalyzer | None = None,
        corporate_analyzer: CorporateEventAnalyzer | None = None,
        impact_analyzer: ImpactAnalyzer | None = None,
        risk_analyzer: EventRiskAnalyzer | None = None,
    ) -> None:
        self._calendar = calendar_analyzer or EconomicCalendarAnalyzer()
        self._corporate = corporate_analyzer or CorporateEventAnalyzer()
        self._impact = impact_analyzer or ImpactAnalyzer()
        self._risk = risk_analyzer or EventRiskAnalyzer()

    def analyze(
        self,
        economic_events: tuple[EconomicEvent, ...] = (),
        corporate_events: tuple[CorporateEvent, ...] = (),
    ) -> EventAnalysis:
        """Execute event intelligence analysis.

        Args:
            economic_events: Scheduled economic events.
            corporate_events: Scheduled corporate events.

        Returns:
            Combined EventAnalysis.
        """

        if not economic_events and not corporate_events:
            return self._empty_analysis("No events provided for analysis.")

        eco_sorted, eco_importance, eco_conf, eco_reasons = self._calendar.analyze(
            economic_events
        )
        corp_sorted, corp_importance, corp_conf, corp_reasons = self._corporate.analyze(
            corporate_events
        )

        impact = self._impact.analyze(
            economic_events=eco_sorted,
            corporate_events=corp_sorted,
        )

        risk = self._risk.analyze(
            impact=impact,
            economic_events=eco_sorted,
            corporate_events=corp_sorted,
        )

        highest_importance = self._highest_importance(eco_importance, corp_importance)

        decision = self._decision_context(impact, risk, highest_importance)

        confidence = self._calculate_confidence(eco_conf, corp_conf, risk.confidence)

        analysis = EventAnalysis(
            economic_events=eco_sorted,
            corporate_events=corp_sorted,
            highest_importance=highest_importance,
            overall_risk=risk.risk_level,
            decision_context=decision,
            confidence=confidence,
            warnings=self._combine_warnings(eco_sorted, corp_sorted, risk),
            metadata=self._metadata(eco_sorted, corp_sorted, impact, risk),
        )

        evidence = self._to_evidence(analysis, risk)
        explanation = self._explanation(
            analysis, eco_sorted, corp_sorted, impact, risk, decision
        )

        object.__setattr__(analysis, "evidence", evidence)
        object.__setattr__(analysis, "explanation", explanation)

        return analysis

    # ------------------------------------------------------------------
    # Decision context
    # ------------------------------------------------------------------

    def _decision_context(
        self,
        impact: Any,
        risk: EventRiskAssessment,
        importance: EventImportance,
    ) -> DecisionContext:
        high_risk = risk.risk_level in (
            EventRisk.HIGH,
            EventRisk.EXTREME,
        )
        high_vol = impact.expected_volatility >= VOL_THRESHOLD_HIGH
        gap_risk = impact.expected_gap_risk >= RISK_THRESHOLD_GAP or risk.gap_risk in (
            EventRisk.HIGH,
            EventRisk.EXTREME,
        )
        critical = importance is EventImportance.CRITICAL

        avoid_new = high_risk or critical
        reduce_size = high_risk or critical
        expect_high_vol = high_vol or high_risk or critical
        expect_gap = gap_risk or critical
        intraday_only = critical or (high_risk and high_vol)

        return DecisionContext(
            avoid_new_positions=avoid_new,
            reduce_position_size=reduce_size,
            expect_high_volatility=expect_high_vol,
            expect_gap_open=expect_gap,
            allow_intraday_only=intraday_only,
            confidence=risk.confidence,
        )

    # ------------------------------------------------------------------
    # Highest importance
    # ------------------------------------------------------------------

    def _highest_importance(
        self,
        eco: EventImportance,
        corp: EventImportance,
    ) -> EventImportance:
        if IMPORTANCE_RANKING.get(eco, 0) >= IMPORTANCE_RANKING.get(corp, 0):
            return eco
        return corp

    # ------------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------------

    def _calculate_confidence(
        self,
        eco_conf: float,
        corp_conf: float,
        risk_conf: float,
    ) -> float:
        confidences: list[float] = []
        weights: list[float] = []

        if eco_conf > 0:
            confidences.append(eco_conf)
            weights.append(0.35)
        if corp_conf > 0:
            confidences.append(corp_conf)
            weights.append(0.30)
        if risk_conf > 0:
            confidences.append(risk_conf)
            weights.append(0.35)

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
        economic: tuple[EconomicEvent, ...],
        corporate: tuple[CorporateEvent, ...],
        risk: EventRiskAssessment,
    ) -> tuple[str, ...]:
        combined: list[str] = []

        if not economic:
            combined.append("No economic events in calendar.")
        if not corporate:
            combined.append("No corporate events in calendar.")
        if risk.confidence < CONFIDENCE_LOW:
            combined.append("Low risk assessment confidence.")

        return tuple(combined)

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def _metadata(
        self,
        economic: tuple[EconomicEvent, ...],
        corporate: tuple[CorporateEvent, ...],
        impact: Any,
        risk: EventRiskAssessment,
    ) -> dict[str, Any]:
        return {
            "analyzer": self.name,
            "economic_event_count": len(economic),
            "corporate_event_count": len(corporate),
            "volatility": impact.expected_volatility,
            "gap_risk": impact.expected_gap_risk,
            "liquidity": impact.expected_liquidity,
            "risk_level": risk.risk_level.value,
        }

    # ------------------------------------------------------------------
    # Evidence generation
    # ------------------------------------------------------------------

    def _evidence_signal(
        self,
        importance: EventImportance,
        risk: EventRiskAssessment,
    ) -> EvidenceSignal:
        if risk.risk_level in (EventRisk.EXTREME,):
            return EvidenceSignal.VERY_BEARISH
        if risk.risk_level in (EventRisk.HIGH,) and importance in (
            EventImportance.CRITICAL,
            EventImportance.HIGH,
        ):
            return EvidenceSignal.BEARISH
        if importance is EventImportance.LOW and risk.risk_level in (
            EventRisk.LOW,
            EventRisk.VERY_LOW,
        ):
            return EvidenceSignal.NEUTRAL
        return EvidenceSignal.NEUTRAL

    def _evidence_score(
        self,
        analysis: EventAnalysis,
    ) -> float:
        base = NEUTRAL_SCORE

        if analysis.highest_importance in (
            EventImportance.CRITICAL,
            EventImportance.HIGH,
        ):
            base = NEGATIVE_SCORE

        adj = 0.0
        if analysis.confidence >= CONFIDENCE_HIGH:
            adj += 5.0
        elif analysis.confidence >= CONFIDENCE_MODERATE:
            adj += 3.0

        return max(0.0, min(100.0, base + adj))

    def _evidence_reasons(
        self,
        analysis: EventAnalysis,
    ) -> tuple[str, ...]:
        reasons: list[str] = []

        eco_count = len(analysis.economic_events)
        corp_count = len(analysis.corporate_events)
        total = eco_count + corp_count
        reasons.append(f"{total} event(s) in calendar.")
        reasons.append(f"Highest importance: {analysis.highest_importance.value}.")
        reasons.append(f"Overall risk: {analysis.overall_risk.value}.")

        return tuple(reasons)

    def _to_evidence(
        self,
        analysis: EventAnalysis,
        risk: EventRiskAssessment,
    ) -> Evidence:
        signal = self._evidence_signal(analysis.highest_importance, risk)
        score = self._evidence_score(analysis)
        confidence = analysis.confidence

        return Evidence(
            source="Event Intelligence",
            category=EvidenceCategory.EVENT,
            signal=signal,
            score=Score(score),
            confidence=Confidence(confidence),
            weight=1.0,
            reasons=self._evidence_reasons(analysis),
            warnings=analysis.warnings,
            metadata={
                "analyzer": self.name,
                "economic_events": len(analysis.economic_events),
                "corporate_events": len(analysis.corporate_events),
                "highest_importance": analysis.highest_importance.value,
                "overall_risk": analysis.overall_risk.value,
            },
        )

    # ------------------------------------------------------------------
    # Explanation generation
    # ------------------------------------------------------------------

    def _explanation(
        self,
        analysis: EventAnalysis,
        economic: tuple[EconomicEvent, ...],
        corporate: tuple[CorporateEvent, ...],
        impact: Any,
        risk: EventRiskAssessment,
        context: DecisionContext | None,
    ) -> EventExplanation:
        return EventExplanation(
            upcoming_events=self._upcoming_section(economic, corporate),
            importance=self._importance_section(analysis),
            market_impact=self._impact_section(impact),
            risk_assessment=self._risk_section(risk),
            trading_implications=self._implications_section(context),
            overall_assessment=self._overall_section(analysis, risk, context),
        )

    def _upcoming_section(
        self,
        economic: tuple[EconomicEvent, ...],
        corporate: tuple[CorporateEvent, ...],
    ) -> str:
        parts: list[str] = ["Upcoming Events:"]

        eco_count = len(economic)
        corp_count = len(corporate)
        total = eco_count + corp_count
        parts.append(f"{total} event(s) scheduled.")

        if economic:
            eco_types = sorted(set(e.event_type.value for e in economic))
            parts.append(f"Economic: {', '.join(eco_types)}.")
        if corporate:
            corp_types = sorted(set(e.event_type.value for e in corporate))
            parts.append(f"Corporate: {', '.join(corp_types)}.")

        return " ".join(parts)

    def _importance_section(self, analysis: EventAnalysis) -> str:
        return (
            f"Importance: Highest importance level is "
            f"{analysis.highest_importance.value}."
        )

    def _impact_section(self, impact: Any) -> str:
        return (
            f"Market Impact: Expected volatility "
            f"{impact.expected_volatility:.2f}, "
            f"liquidity {impact.expected_liquidity:.2f}, "
            f"gap risk {impact.expected_gap_risk:.2f}. "
            f"Affected: {impact.affected_asset_class.value}."
        )

    def _risk_section(self, risk: EventRiskAssessment) -> str:
        return (
            f"Risk Assessment: Overall risk is {risk.risk_level.value}. "
            f"Gap risk: {risk.gap_risk.value}. "
            f"Volatility risk: {risk.volatility_risk.value}."
        )

    def _implications_section(
        self,
        context: DecisionContext | None,
    ) -> str:
        parts: list[str] = ["Trading Implications:"]

        if context is None:
            parts.append("No event-driven implications.")
            return " ".join(parts)

        if context.avoid_new_positions:
            parts.append("Avoid new positions before key events.")
        if context.reduce_position_size:
            parts.append("Consider reducing existing position sizes.")
        if context.expect_high_volatility:
            parts.append("Elevated volatility expected.")
        if context.expect_gap_open:
            parts.append("Gap open risk present.")
        if context.allow_intraday_only:
            parts.append("Limit activity to intraday where possible.")

        if not any(
            [
                context.avoid_new_positions,
                context.reduce_position_size,
                context.expect_high_volatility,
                context.expect_gap_open,
                context.allow_intraday_only,
            ]
        ):
            parts.append("No significant event-driven restrictions.")

        return " ".join(parts)

    def _overall_section(
        self,
        analysis: EventAnalysis,
        risk: EventRiskAssessment,
        context: DecisionContext | None,
    ) -> str:
        parts: list[str] = ["Overall Assessment:"]

        high_risk = risk.risk_level in (EventRisk.HIGH, EventRisk.EXTREME)

        if high_risk:
            parts.append(
                "Elevated event risk detected. " "Capital preservation is the priority."
            )
        elif analysis.highest_importance in (
            EventImportance.CRITICAL,
            EventImportance.HIGH,
        ):
            parts.append(
                "Important events pending. " "Monitor developments and adjust exposure."
            )
        else:
            parts.append(
                "Event calendar is benign. "
                "No significant event-driven disruptions expected."
            )

        if context is not None and context.confidence < CONFIDENCE_LOW:
            parts.append("Low confidence. Cross-reference with other intelligence.")

        return " ".join(parts)

    # ------------------------------------------------------------------
    # Empty / fallback analysis
    # ------------------------------------------------------------------

    def _empty_analysis(self, reason: str) -> EventAnalysis:
        analysis = EventAnalysis.neutral_placeholder()
        object.__setattr__(analysis, "warnings", (reason,))
        explanation = EventExplanation(
            upcoming_events="Event assessment unavailable: no events provided.",
            importance="Importance assessment unavailable: no events provided.",
            market_impact="Market impact unavailable: no events provided.",
            risk_assessment="Risk assessment unavailable: no events provided.",
            trading_implications="Trading implications unavailable: no events provided.",
            overall_assessment="Overall Assessment: Event intelligence data is unavailable.",
        )
        object.__setattr__(analysis, "explanation", explanation)
        return analysis
