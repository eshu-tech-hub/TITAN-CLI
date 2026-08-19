"""Economic Calendar Analyzer.

Analyzes scheduled economic events and classifies them by type,
importance, and temporal proximity. Pure analyzer — no API calls.

Integrates with:
  - Event Intelligence Engine
  - Impact Analyzer
  - Event Risk Analyzer
"""

from datetime import UTC, datetime

from titan.events.models import EconomicEvent, EventImportance


class EconomicCalendarAnalyzer:
    """Analyze scheduled economic calendar events.

    Classifies events by type, determines highest importance, and
    provides temporal context for upcoming releases.
    """

    name = "EconomicCalendarAnalyzer"

    CRITICAL_EVENTS = frozenset(
        {
            "fomc",
            "ecb",
            "boj",
            "rbi_policy",
            "nfp",
            "interest_rate_decision",
        }
    )

    HIGH_IMPACT_EVENTS = frozenset(
        {
            "gdp",
            "cpi",
            "ppi",
        }
    )

    @classmethod
    def importance_for(cls, event: EconomicEvent) -> EventImportance:
        """Determine appropriate importance based on event type."""
        if event.importance is not EventImportance.MEDIUM:
            return event.importance

        if event.event_type.value in cls.CRITICAL_EVENTS:
            return EventImportance.CRITICAL
        if event.event_type.value in cls.HIGH_IMPACT_EVENTS:
            return EventImportance.HIGH
        if event.event_type.value == "holiday":
            return EventImportance.LOW
        return EventImportance.MEDIUM

    def analyze(
        self,
        events: tuple[EconomicEvent, ...],
    ) -> tuple[
        tuple[EconomicEvent, ...],
        EventImportance,
        float,
        tuple[str, ...],
    ]:
        """Analyze economic calendar events.

        Args:
            events: Economic events to analyze.

        Returns:
            Tuple of (sorted_events, highest_importance, confidence, reasons).
        """
        if not events:
            return (
                (),
                EventImportance.LOW,
                0.0,
                ("No economic events in calendar.",),
            )

        sorted_events = tuple(
            sorted(
                (
                    EconomicEvent(
                        event_type=e.event_type,
                        timestamp=e.timestamp,
                        importance=self.importance_for(e),
                        description=e.description,
                        country=e.country,
                        previous=e.previous,
                        forecast=e.forecast,
                        actual=e.actual,
                        affected_asset_classes=e.affected_asset_classes,
                        affected_sectors=e.affected_sectors,
                    )
                    for e in events
                ),
                key=lambda x: (
                    -_importance_rank(x.importance),
                    x.timestamp,
                ),
            )
        )

        highest = sorted_events[0].importance

        now = datetime.now(UTC)
        upcoming = sum(1 for e in sorted_events if e.timestamp > now)
        total = len(sorted_events)
        confidence = min(1.0, total / 5) * min(1.0, upcoming / max(1, total))

        reasons: list[str] = [
            f"Analyzed {total} economic event(s).",
            f"Highest importance: {highest.value}.",
            f"{upcoming} event(s) pending.",
        ]

        if highest is EventImportance.CRITICAL:
            reasons.append(
                "Critical event(s) present — elevated market awareness required."
            )

        return sorted_events, highest, confidence, tuple(reasons)


def _importance_rank(importance: EventImportance) -> int:
    mapping = {
        EventImportance.CRITICAL: 4,
        EventImportance.HIGH: 3,
        EventImportance.MEDIUM: 2,
        EventImportance.LOW: 1,
    }
    return mapping.get(importance, 0)
