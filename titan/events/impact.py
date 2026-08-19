"""Impact Analyzer.

Determines expected market impact from scheduled events including
volatility, liquidity, gap risk, affected asset classes, and sectors.
Pure analyzer — no API calls.

Integrates with:
  - Economic Calendar Analyzer
  - Corporate Event Analyzer
  - Event Intelligence Engine
  - Event Risk Analyzer
"""

from typing import ClassVar

from titan.events.models import (
    AssetClass,
    CorporateEvent,
    EconomicEvent,
    EventImpact,
    EventImportance,
)


class ImpactAnalyzer:
    """Determine expected market impact from scheduled events.

    Evaluates volatility, liquidity, gap risk, duration, and affected
    asset classes/sectors based on event type and importance.
    """

    name = "ImpactAnalyzer"

    VOLATILITY_MAP: ClassVar[dict[EventImportance, float]] = {
        EventImportance.CRITICAL: 0.85,
        EventImportance.HIGH: 0.65,
        EventImportance.MEDIUM: 0.35,
        EventImportance.LOW: 0.15,
    }

    LIQUIDITY_MAP: ClassVar[dict[EventImportance, float]] = {
        EventImportance.CRITICAL: 0.30,
        EventImportance.HIGH: 0.45,
        EventImportance.MEDIUM: 0.70,
        EventImportance.LOW: 0.90,
    }

    GAP_RISK_MAP: ClassVar[dict[EventImportance, float]] = {
        EventImportance.CRITICAL: 0.80,
        EventImportance.HIGH: 0.55,
        EventImportance.MEDIUM: 0.25,
        EventImportance.LOW: 0.10,
    }

    DURATION_MAP: ClassVar[dict[EventImportance, str]] = {
        EventImportance.CRITICAL: "Multiple sessions",
        EventImportance.HIGH: "Intraday to next session",
        EventImportance.MEDIUM: "Intraday",
        EventImportance.LOW: "Brief intraday",
    }

    ASSET_MAP: ClassVar[dict[str, AssetClass]] = {
        "rbi_policy": AssetClass.CURRENCY,
        "fomc": AssetClass.CURRENCY,
        "ecb": AssetClass.CURRENCY,
        "boj": AssetClass.CURRENCY,
        "interest_rate_decision": AssetClass.RATES,
        "gdp": AssetClass.BROAD,
        "cpi": AssetClass.BROAD,
        "ppi": AssetClass.BROAD,
        "pmi": AssetClass.BROAD,
        "nfp": AssetClass.CURRENCY,
        "unemployment": AssetClass.BROAD,
        "holiday": AssetClass.BROAD,
    }

    def analyze(
        self,
        economic_events: tuple[EconomicEvent, ...] = (),
        corporate_events: tuple[CorporateEvent, ...] = (),
    ) -> EventImpact:
        """Determine event-driven market impact.

        Args:
            economic_events: Economic events to consider.
            corporate_events: Corporate events to consider.

        Returns:
            EventImpact with volatility, liquidity, gap risk assessments.
        """
        if not economic_events and not corporate_events:
            return EventImpact()

        highest_importance = self._refined_highest(economic_events, corporate_events)

        volatility = self.VOLATILITY_MAP.get(highest_importance, 0.35)
        liquidity = self.LIQUIDITY_MAP.get(highest_importance, 0.70)
        gap_risk = self.GAP_RISK_MAP.get(highest_importance, 0.25)
        duration = self.DURATION_MAP.get(highest_importance, "Intraday")

        asset_class = self._affected_asset_class(economic_events, corporate_events)
        sector = self._affected_sector(corporate_events)

        return EventImpact(
            expected_volatility=volatility,
            expected_liquidity=liquidity,
            expected_gap_risk=gap_risk,
            affected_asset_class=asset_class,
            affected_sector=sector,
            expected_duration=duration,
        )

    def _highest_importance(
        self,
        economic: tuple[EconomicEvent, ...],
        corporate: tuple[CorporateEvent, ...],
    ) -> EventImportance:
        ranks: list[EventImportance] = []
        for e in economic:
            ranks.append(e.importance)
        for c in corporate:
            ranks.append(c.importance)
        if not ranks:
            return EventImportance.LOW
        return max(ranks, key=lambda x: _importance_rank(x))

    def _refined_highest(
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

    def _affected_asset_class(
        self,
        economic: tuple[EconomicEvent, ...],
        corporate: tuple[CorporateEvent, ...],
    ) -> AssetClass:
        for e in economic:
            mapped = self.ASSET_MAP.get(e.event_type.value)
            if mapped is not None:
                return mapped
        if corporate:
            return AssetClass.EQUITY
        return AssetClass.BROAD

    def _affected_sector(
        self,
        corporate: tuple[CorporateEvent, ...],
    ) -> str:
        if not corporate:
            return ""
        companies = {c.company for c in corporate if c.company}
        if companies:
            return ", ".join(sorted(companies))
        return "Corporate sector"


def _importance_rank(importance: EventImportance) -> int:
    mapping = {
        EventImportance.CRITICAL: 4,
        EventImportance.HIGH: 3,
        EventImportance.MEDIUM: 2,
        EventImportance.LOW: 1,
    }
    return mapping.get(importance, 0)
