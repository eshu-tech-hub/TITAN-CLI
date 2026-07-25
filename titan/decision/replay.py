from dataclasses import dataclass

from titan.decision.journal import DecisionJournalEntry, DecisionRepository


@dataclass(frozen=True, slots=True)
class DecisionReplaySnapshot:
    """Snapshot of the historical state during the decision."""

    entry: DecisionJournalEntry


@dataclass(frozen=True, slots=True)
class DecisionReplayTimeline:
    """Timeline of events that occurred during this decision process."""

    events: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DecisionReplayResult:
    """The result of the decision replay."""

    snapshot: DecisionReplaySnapshot
    timeline: DecisionReplayTimeline


@dataclass(slots=True)
class DecisionReplayService:
    """Service to reconstruct historical decisions for replay.

    This service operates strictly in read-only mode and
    must not execute any analytics or business logic.
    """

    repository: DecisionRepository

    def replay(self, entry_id: str) -> DecisionReplayResult | None:
        """Reconstruct a historical decision by its ID."""
        entry = self.repository.get(entry_id)
        if not entry:
            return None

        snapshot = DecisionReplaySnapshot(entry=entry)
        # The timeline is a placeholder since the journal entry currently
        # stores the final decision in one atomic timestamp.
        timeline = DecisionReplayTimeline(events=("Decision Generated",))

        return DecisionReplayResult(snapshot=snapshot, timeline=timeline)

    def latest(self) -> DecisionReplayResult | None:
        """Replay the most recent decision."""
        entry = self.repository.latest()
        if not entry:
            return None
        return self.replay(entry.id)
