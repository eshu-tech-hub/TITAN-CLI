import typing
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from titan.decision.models import TradeDecision


@dataclass(frozen=True, slots=True)
class EvidenceSnapshot:
    """Snapshot of evidence at the time of the decision."""

    source: str
    category: str
    signal: str
    score: float
    confidence: float
    weight: float
    reasons: tuple[str, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DecisionReason:
    """A specific reason for a decision (either for taking or rejecting a trade)."""

    reason_type: str
    description: str
    severity: str = "info"  # info, warning, critical


@dataclass(frozen=True, slots=True)
class DecisionJournalEntry:
    """An immutable, timestamped record of a trade decision."""

    id: str
    timestamp: datetime
    symbol: str
    decision: str
    trade_direction: str
    instrument_type: str
    trade_score: float
    confidence: float
    institutional_grade: bool
    evidence_snapshot: EvidenceSnapshot | None
    reasons: tuple[DecisionReason, ...]
    explanation_summary: str
    risk_summary: str
    raw_decision: TradeDecision


class DecisionRepository:
    """In-memory repository for storing Decision Journal entries."""

    def __init__(self) -> None:
        self._entries: list[DecisionJournalEntry] = []

    def save(self, entry: DecisionJournalEntry) -> None:
        """Save a new decision entry."""
        self._entries.append(entry)

    def get_latest(self, count: int = 100) -> list[DecisionJournalEntry]:
        """Get the latest N entries, ordered by timestamp descending."""
        return [
            e
            for _, e in sorted(
                enumerate(self._entries),
                key=lambda t: (t[1].timestamp, t[0]),
                reverse=True,
            )[:count]
        ]

    def get_by_symbol(self, symbol: str) -> list[DecisionJournalEntry]:
        """Get all entries for a specific symbol."""
        return [e for e in self._entries if e.symbol == symbol]

    def clear(self) -> None:
        """Clear the repository."""
        self._entries.clear()

    def get(self, entry_id: str) -> DecisionJournalEntry | None:
        """Get a specific entry by its ID."""
        for entry in self._entries:
            if entry.id == entry_id:
                return entry
        return None

    def latest(self) -> DecisionJournalEntry | None:
        """Get the most recent entry."""
        if not self._entries:
            return None
        return max(enumerate(self._entries), key=lambda t: (t[1].timestamp, t[0]))[1]

    def previous(self, current_id: str) -> DecisionJournalEntry | None:
        """Get the entry immediately preceding the given ID chronologically."""
        indexed = list(enumerate(self._entries))
        sorted_entries = sorted(indexed, key=lambda t: (t[1].timestamp, t[0]))
        for i, (_, entry) in enumerate(sorted_entries):
            if entry.id == current_id:
                if i > 0:
                    return sorted_entries[i - 1][1]
                return None
        return None

    def next(self, current_id: str) -> DecisionJournalEntry | None:
        """Get the entry immediately following the given ID chronologically."""
        indexed = list(enumerate(self._entries))
        sorted_entries = sorted(indexed, key=lambda t: (t[1].timestamp, t[0]))
        for i, (_, entry) in enumerate(sorted_entries):
            if entry.id == current_id:
                if i < len(sorted_entries) - 1:
                    return sorted_entries[i + 1][1]
                return None
        return None

    def list(
        self, page: int = 1, page_size: int = 100
    ) -> Sequence[DecisionJournalEntry]:
        """List entries with pagination, newest first."""
        sorted_entries = [
            e
            for _, e in sorted(
                enumerate(self._entries),
                key=lambda t: (t[1].timestamp, t[0]),
                reverse=True,
            )
        ]
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        return sorted_entries[start_idx:end_idx]

    def search(self, query: str) -> typing.Sequence[DecisionJournalEntry]:
        """Simple text search across explanation and reasons, newest first."""
        query = query.lower()
        results = []
        for _, entry in sorted(
            enumerate(self._entries), key=lambda t: (t[1].timestamp, t[0]), reverse=True
        ):
            if (
                query in entry.explanation_summary.lower()
                or query in entry.risk_summary.lower()
            ):
                results.append(entry)
                continue
            reason_match = False
            for r in entry.reasons:
                if query in r.description.lower():
                    reason_match = True
                    break
            if reason_match:
                results.append(entry)
        return results

    def filter(
        self,
        symbol: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        status: str | None = None,
        strategy: str | None = None,
        confidence_min: float | None = None,
    ) -> Sequence[DecisionJournalEntry]:
        """Filter entries based on multiple criteria."""
        results = []
        for entry in self._entries:
            if symbol and entry.symbol != symbol:
                continue
            if start_date and entry.timestamp < start_date:
                continue
            if end_date and entry.timestamp > end_date:
                continue
            if status and entry.decision != status:
                continue
            if (
                strategy
                and strategy.lower() not in entry.raw_decision.entry_strategy.lower()
            ):
                continue
            if confidence_min is not None and entry.confidence < confidence_min:
                continue
            results.append(entry)
        return [
            e
            for _, e in sorted(
                enumerate(results), key=lambda t: (t[1].timestamp, t[0]), reverse=True
            )
        ]

    def count(self) -> int:
        """Total number of entries in the journal."""
        return len(self._entries)


@dataclass(slots=True)
class DecisionJournal:
    """Authoritative source for every trading decision generated by TITAN.

    Records every accepted trade, rejected trade, and NO_TRADE outcome
    with full explainability.
    """

    repository: DecisionRepository = field(default_factory=DecisionRepository)

    def record_decision(self, decision: TradeDecision) -> DecisionJournalEntry:
        """Record a TradeDecision into the journal.

        Args:
            decision: The final decision produced by the DecisionEngine.

        Returns:
            The recorded DecisionJournalEntry.
        """
        # Create EvidenceSnapshot if evidence is present
        evidence_snapshot = None
        if decision.evidence is not None:
            evidence_snapshot = EvidenceSnapshot(
                source=decision.evidence.source,
                category=decision.evidence.category.value,
                signal=decision.evidence.signal.value,
                score=decision.evidence.score.value,
                confidence=decision.evidence.confidence.value,
                weight=decision.evidence.weight,
                reasons=decision.evidence.reasons,
                metadata=decision.evidence.metadata,
            )

        # Build reasons from explanation or warnings
        reasons: list[DecisionReason] = []
        if decision.explanation:
            if decision.explanation.why_alternatives_rejected:
                reasons.append(
                    DecisionReason(
                        reason_type="rejection",
                        description=decision.explanation.why_alternatives_rejected,
                        severity="info",
                    )
                )
            if decision.explanation.why_this_trade:
                reasons.append(
                    DecisionReason(
                        reason_type="rationale",
                        description=decision.explanation.why_this_trade,
                        severity="info",
                    )
                )
        for warning in decision.warnings:
            reasons.append(
                DecisionReason(
                    reason_type="warning", description=warning, severity="warning"
                )
            )

        entry = DecisionJournalEntry(
            id=str(uuid.uuid4()),
            timestamp=decision.timestamp or datetime.now(UTC),
            symbol=decision.symbol,
            decision=decision.decision.value,
            trade_direction=decision.trade_direction.value,
            instrument_type=decision.instrument_type.value,
            trade_score=decision.trade_score,
            confidence=decision.confidence,
            institutional_grade=decision.institutional_grade,
            evidence_snapshot=evidence_snapshot,
            reasons=tuple(reasons),
            explanation_summary=(
                decision.explanation.decision_summary if decision.explanation else ""
            ),
            risk_summary=(
                decision.explanation.risk_summary if decision.explanation else ""
            ),
            raw_decision=decision,
        )

        self.repository.save(entry)
        return entry
