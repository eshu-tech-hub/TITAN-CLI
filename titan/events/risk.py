"""Event Risk Analyzer.

Classifies event-driven market risk across volatility, gap, and
liquidity dimensions. Pure analyzer — no API calls.

Integrates with:
  - Impact Analyzer
  - Event Intelligence Engine
"""

from typing import ClassVar

from titan.events.models import (
    CorporateEvent,
    EconomicEvent,
    EventImpact,
    EventImportance,
    EventRisk,
    EventRiskAssessment,
)


class EventRiskAnalyzer:
    """Classify event-driven market risk.

    Evaluates overall risk, gap risk, volatility risk, and liquidity
    risk based on scheduled events and their expected impact.
    """

    name = "EventRiskAnalyzer"

    RISK_BY_IMPORTANCE: ClassVar[dict[EventImportance, EventRisk]] = {
        EventImportance.CRITICAL: EventRisk.EXTREME,
        EventImportance.HIGH: EventRisk.HIGH,
        EventImportance.MEDIUM: EventRisk.MODERATE,
        EventImportance.LOW: EventRisk.LOW,
    }

    def analyze(
        self,
        impact: EventImpact | None = None,
        economic_events: tuple[EconomicEvent, ...] = (),
        corporate_events: tuple[CorporateEvent, ...] = (),
    ) -> EventRiskAssessment:
        """Classify event-driven risk.

        Args:
            impact: Expected impact from ImpactAnalyzer.
            economic_events: Economic events to consider.
            corporate_events: Corporate events to consider.

        Returns:
            EventRiskAssessment with multi-dimensional risk levels.
        """
        if not economic_events and not corporate_events:
            return EventRiskAssessment(
                risk_level=EventRisk.LOW,
                gap_risk=EventRisk.LOW,
                volatility_risk=EventRisk.LOW,
                liquidity_risk=EventRisk.LOW,
                confidence=0.0,
            )

        if impact is None:
            impact = EventImpact()

        importance = self._refined_importance(economic_events, corporate_events)

        risk_level = self.RISK_BY_IMPORTANCE.get(importance, EventRisk.MODERATE)
        gap_risk = self._gap_risk(impact, importance)
        volatility_risk = self._volatility_risk(impact, importance)
        liquidity_risk = self._liquidity_risk(impact, importance)

        total_events = len(economic_events) + len(corporate_events)
        confidence = min(1.0, total_events / 3)

        return EventRiskAssessment(
            risk_level=risk_level,
            gap_risk=gap_risk,
            volatility_risk=volatility_risk,
            liquidity_risk=liquidity_risk,
            confidence=confidence,
        )

    def _refined_importance(
        self,
        economic: tuple[EconomicEvent, ...],
        corporate: tuple[CorporateEvent, ...],
    ) -> EventImportance:
        from titan.events.calendar import EconomicCalendarAnalyzer
        from titan.events.corporate import CorporateEventAnalyzer

        highest = EventImportance.LOW
        for e in economic:
            imp = EconomicCalendarAnalyzer.importance_for(e)
            if _importance_rank(imp) > _importance_rank(highest):
                highest = imp
        for c in corporate:
            imp = CorporateEventAnalyzer.importance_for(c)
            if _importance_rank(imp) > _importance_rank(highest):
                highest = imp
        return highest

    def _gap_risk(
        self,
        impact: EventImpact,
        importance: EventImportance,
    ) -> EventRisk:
        if impact.expected_gap_risk >= 0.7:
            return EventRisk.EXTREME
        if impact.expected_gap_risk >= 0.5:
            return EventRisk.HIGH
        if impact.expected_gap_risk >= 0.3:
            return EventRisk.MODERATE
        return EventRisk.LOW

    def _volatility_risk(
        self,
        impact: EventImpact,
        importance: EventImportance,
    ) -> EventRisk:
        if impact.expected_volatility >= 0.7:
            return EventRisk.HIGH
        if impact.expected_volatility >= 0.5:
            return EventRisk.MODERATE
        return EventRisk.LOW

    def _liquidity_risk(
        self,
        impact: EventImpact,
        importance: EventImportance,
    ) -> EventRisk:
        if impact.expected_liquidity <= 0.35:
            return EventRisk.HIGH
        if impact.expected_liquidity <= 0.55:
            return EventRisk.MODERATE
        return EventRisk.LOW


def _importance_rank(importance: EventImportance) -> int:
    mapping = {
        EventImportance.CRITICAL: 4,
        EventImportance.HIGH: 3,
        EventImportance.MEDIUM: 2,
        EventImportance.LOW: 1,
    }
    return mapping.get(importance, 0)
