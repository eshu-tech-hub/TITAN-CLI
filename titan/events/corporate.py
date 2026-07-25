"""Corporate Event Analyzer.

Analyzes scheduled corporate action events and classifies them by type,
importance, and temporal proximity. Pure analyzer — no API calls.

Integrates with:
  - Event Intelligence Engine
  - Impact Analyzer
  - Event Risk Analyzer
"""

from datetime import datetime, timezone

from titan.events.models import CorporateEvent, EventImportance


class CorporateEventAnalyzer:
    """Analyze scheduled corporate action events.

    Classifies events by type, determines highest importance, and
    provides temporal context for upcoming corporate actions.
    """

    name = "CorporateEventAnalyzer"

    CRITICAL_EVENTS = frozenset(
        {
            "quarterly_results",
            "merger",
            "acquisition",
            "buyback",
        }
    )

    HIGH_IMPACT_EVENTS = frozenset(
        {
            "guidance",
            "promoter_activity",
            "block_deal",
            "rights_issue",
        }
    )

    @classmethod
    def importance_for(cls, event: CorporateEvent) -> EventImportance:
        """Determine appropriate importance based on event type."""
        if event.importance is not EventImportance.MEDIUM:
            return event.importance

        if event.event_type.value in cls.CRITICAL_EVENTS:
            return EventImportance.CRITICAL
        if event.event_type.value in cls.HIGH_IMPACT_EVENTS:
            return EventImportance.HIGH
        return EventImportance.MEDIUM

    def analyze(
        self,
        events: tuple[CorporateEvent, ...],
    ) -> tuple[
        tuple[CorporateEvent, ...],
        EventImportance,
        float,
        tuple[str, ...],
    ]:
        """Analyze corporate action events.

        Args:
            events: Corporate events to analyze.

        Returns:
            Tuple of (sorted_events, highest_importance, confidence, reasons).
        """
        if not events:
            return (
                (),
                EventImportance.LOW,
                0.0,
                ("No corporate events in calendar.",),
            )

        sorted_events = tuple(
            sorted(
                (
                    CorporateEvent(
                        event_type=e.event_type,
                        timestamp=e.timestamp,
                        company=e.company,
                        importance=self.importance_for(e),
                        description=e.description,
                        details=e.details,
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

        now = datetime.now(timezone.utc)
        upcoming = sum(1 for e in sorted_events if e.timestamp > now)
        total = len(sorted_events)
        confidence = min(1.0, total / 5) * min(1.0, upcoming / max(1, total))

        reasons: list[str] = [
            f"Analyzed {total} corporate event(s).",
            f"Highest importance: {highest.value}.",
            f"{upcoming} event(s) pending.",
        ]

        if highest is EventImportance.CRITICAL:
            reasons.append("Critical corporate event(s) present.")

        return sorted_events, highest, confidence, tuple(reasons)


def _importance_rank(importance: EventImportance) -> int:
    mapping = {
        EventImportance.CRITICAL: 4,
        EventImportance.HIGH: 3,
        EventImportance.MEDIUM: 2,
        EventImportance.LOW: 1,
    }
    return mapping.get(importance, 0)
