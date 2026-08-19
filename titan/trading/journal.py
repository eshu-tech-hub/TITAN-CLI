import csv
import json
import typing
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any


class TradeLifecycleState(str, Enum):
    """Lifecycle states for a trade from creation to archive."""

    CREATED = "created"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    MODIFIED = "modified"
    CLOSED = "closed"
    ARCHIVED = "archived"


@dataclass(frozen=True, slots=True)
class TradeLifecycleEvent:
    """A single transition in the trade lifecycle."""

    timestamp: datetime
    status: TradeLifecycleState
    reason: str = ""
    broker_reference: str = ""
    notes: str = ""


@dataclass(frozen=True, slots=True)
class TradeJournalEntry:
    """An immutable record of an executed trade and its lifecycle."""

    trade_id: str
    decision_id: str
    runtime_session_id: str
    symbol: str
    exchange: str
    direction: str
    quantity: int
    entry_price: float
    exit_price: float
    gross_pnl: float
    net_pnl: float
    fees: float
    slippage: float
    strategy: str
    tags: tuple[str, ...]
    decision_status: str
    execution_status: TradeLifecycleState
    open_time: datetime | None
    close_time: datetime | None
    lifecycle_events: tuple[TradeLifecycleEvent, ...] = field(default_factory=tuple)

    @property
    def holding_time_seconds(self) -> float:
        """Calculate holding time in seconds."""
        if not self.open_time:
            return 0.0
        end_time = self.close_time or datetime.now(UTC)
        return (end_time - self.open_time).total_seconds()


class TradeRepository:
    """In-memory repository for storing and querying TradeJournalEntry records."""

    def __init__(self) -> None:
        self._entries: list[TradeJournalEntry] = []
        self._by_id: dict[str, TradeJournalEntry] = {}

    def add(self, entry: TradeJournalEntry) -> None:
        """Add a new entry to the repository."""
        if entry.trade_id in self._by_id:
            raise ValueError(f"Trade entry {entry.trade_id} already exists.")
        self._entries.append(entry)
        self._by_id[entry.trade_id] = entry

    def update(self, entry: TradeJournalEntry) -> None:
        """Update an existing entry."""
        if entry.trade_id not in self._by_id:
            raise ValueError(f"Trade entry {entry.trade_id} not found.")

        # Replace existing entry while maintaining order
        for i, existing in enumerate(self._entries):
            if existing.trade_id == entry.trade_id:
                self._entries[i] = entry
                break
        self._by_id[entry.trade_id] = entry

    def get(self, trade_id: str) -> TradeJournalEntry | None:
        """Retrieve an entry by ID."""
        return self._by_id.get(trade_id)

    def latest(self) -> TradeJournalEntry | None:
        """Get the most recent entry by open_time/creation time."""
        if not self._entries:
            return None

        # Use open_time or first lifecycle event timestamp
        def sort_key(e: TradeJournalEntry) -> datetime:
            if e.open_time:
                return e.open_time
            if e.lifecycle_events:
                return e.lifecycle_events[0].timestamp
            return datetime.min.replace(tzinfo=UTC)

        return max(self._entries, key=sort_key)

    def previous(self, current_id: str) -> TradeJournalEntry | None:
        """Get the entry chronologically before the given ID."""
        if not self._entries:
            return None

        def sort_key(e: TradeJournalEntry) -> datetime:
            return e.open_time or (
                e.lifecycle_events[0].timestamp
                if e.lifecycle_events
                else datetime.min.replace(tzinfo=UTC)
            )

        sorted_entries = sorted(self._entries, key=sort_key, reverse=True)
        for i, entry in enumerate(sorted_entries):
            if entry.trade_id == current_id:
                if i < len(sorted_entries) - 1:
                    return sorted_entries[i + 1]
                return None
        return None

    def next(self, current_id: str) -> TradeJournalEntry | None:
        """Get the entry chronologically after the given ID."""
        if not self._entries:
            return None

        def sort_key(e: TradeJournalEntry) -> datetime:
            return e.open_time or (
                e.lifecycle_events[0].timestamp
                if e.lifecycle_events
                else datetime.min.replace(tzinfo=UTC)
            )

        sorted_entries = sorted(self._entries, key=sort_key, reverse=True)
        for i, entry in enumerate(sorted_entries):
            if entry.trade_id == current_id:
                if i > 0:
                    return sorted_entries[i - 1]
                return None
        return None

    def list(self, page: int = 1, page_size: int = 100) -> Sequence[TradeJournalEntry]:
        """List entries with pagination, newest first."""

        def sort_key(e: TradeJournalEntry) -> datetime:
            return e.open_time or (
                e.lifecycle_events[0].timestamp
                if e.lifecycle_events
                else datetime.min.replace(tzinfo=UTC)
            )

        sorted_entries = sorted(self._entries, key=sort_key, reverse=True)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        return sorted_entries[start_idx:end_idx]

    def count(self) -> int:
        """Total number of entries in the repository."""
        return len(self._entries)

    def search(self, query: str) -> typing.Sequence[TradeJournalEntry]:
        """Simple text search across symbol, strategy, and tags."""
        query = query.lower()
        results = []
        for entry in self._entries:
            if (
                query in entry.symbol.lower()
                or query in entry.strategy.lower()
                or any(query in tag.lower() for tag in entry.tags)
            ):
                results.append(entry)

        def sort_key(e: TradeJournalEntry) -> datetime:
            return e.open_time or (
                e.lifecycle_events[0].timestamp
                if e.lifecycle_events
                else datetime.min.replace(tzinfo=UTC)
            )

        return sorted(results, key=sort_key, reverse=True)

    def filter(
        self,
        symbol: str | None = None,
        strategy: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        outcome: str | None = None,
        direction: str | None = None,
        tags: Sequence[str] | None = None,
    ) -> Sequence[TradeJournalEntry]:
        """Filter entries based on multiple criteria."""
        results = []
        for entry in self._entries:
            if symbol and entry.symbol != symbol:
                continue
            if strategy and strategy.lower() not in entry.strategy.lower():
                continue

            entry_time = entry.open_time or (
                entry.lifecycle_events[0].timestamp if entry.lifecycle_events else None
            )
            if start_date and entry_time and entry_time < start_date:
                continue
            if end_date and entry_time and entry_time > end_date:
                continue

            if outcome:
                # Basic outcome logic: win if net_pnl > 0, loss if net_pnl < 0, breakeven if == 0
                if outcome == "win" and entry.net_pnl <= 0:
                    continue
                if outcome == "loss" and entry.net_pnl >= 0:
                    continue
                if outcome == "breakeven" and entry.net_pnl != 0:
                    continue

            if direction and entry.direction.lower() != direction.lower():
                continue

            if tags and not all(t in entry.tags for t in tags):
                continue

            results.append(entry)

        def sort_key(e: TradeJournalEntry) -> datetime:
            return e.open_time or (
                e.lifecycle_events[0].timestamp
                if e.lifecycle_events
                else datetime.min.replace(tzinfo=UTC)
            )

        return sorted(results, key=sort_key, reverse=True)

    def export_csv(self, filepath: Path) -> None:
        """Export all entries to a CSV file."""
        if not self._entries:
            return

        fields = [
            "Trade UUID",
            "Decision UUID",
            "Runtime Session",
            "Symbol",
            "Exchange",
            "Direction",
            "Quantity",
            "Entry Price",
            "Exit Price",
            "Gross PnL",
            "Net PnL",
            "Fees",
            "Slippage",
            "Holding Time",
            "Strategy",
            "Tags",
            "Decision Status",
            "Execution Status",
            "Open Time",
            "Close Time",
        ]

        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(fields)

            def sort_key(e: TradeJournalEntry) -> datetime:
                return e.open_time or (
                    e.lifecycle_events[0].timestamp
                    if e.lifecycle_events
                    else datetime.min.replace(tzinfo=UTC)
                )

            for entry in sorted(self._entries, key=sort_key):
                writer.writerow(
                    [
                        entry.trade_id,
                        entry.decision_id,
                        entry.runtime_session_id,
                        entry.symbol,
                        entry.exchange,
                        entry.direction,
                        entry.quantity,
                        entry.entry_price,
                        entry.exit_price,
                        entry.gross_pnl,
                        entry.net_pnl,
                        entry.fees,
                        entry.slippage,
                        entry.holding_time_seconds,
                        entry.strategy,
                        ",".join(entry.tags),
                        entry.decision_status,
                        entry.execution_status.value,
                        entry.open_time.isoformat() if entry.open_time else "",
                        entry.close_time.isoformat() if entry.close_time else "",
                    ]
                )

    def export_json(self, filepath: Path) -> None:
        """Export complete object hierarchy to a JSON file."""

        def custom_serializer(obj: Any) -> Any:
            if isinstance(obj, datetime):
                return obj.isoformat()
            if isinstance(obj, Enum):
                return obj.value
            raise TypeError(f"Type {type(obj)} not serializable")

        def sort_key(e: TradeJournalEntry) -> datetime:
            return e.open_time or (
                e.lifecycle_events[0].timestamp
                if e.lifecycle_events
                else datetime.min.replace(tzinfo=UTC)
            )

        data = [asdict(entry) for entry in sorted(self._entries, key=sort_key)]

        with open(filepath, mode="w", encoding="utf-8") as f:
            json.dump(data, f, default=custom_serializer, indent=2)


@dataclass(slots=True)
class TradeJournal:
    """The authoritative system for tracking trade execution and lifecycles."""

    repository: TradeRepository = field(default_factory=TradeRepository)

    def record_transition(
        self,
        trade_id: str,
        status: TradeLifecycleState,
        reason: str = "",
        broker_reference: str = "",
        notes: str = "",
        timestamp: datetime | None = None,
        **updates: Any,
    ) -> TradeJournalEntry:
        """Record a state transition for a trade, updating its journal entry."""
        ts = timestamp or datetime.now(UTC)
        event = TradeLifecycleEvent(
            timestamp=ts,
            status=status,
            reason=reason,
            broker_reference=broker_reference,
            notes=notes,
        )

        entry = self.repository.get(trade_id)
        if not entry:
            raise ValueError(f"Trade {trade_id} does not exist in journal.")

        current_dict = asdict(entry)

        # Apply lifecycle event
        events = list(current_dict["lifecycle_events"])

        # Convert events back to dataclass objects since asdict serialized them to dicts
        event_objs = [
            TradeLifecycleEvent(
                timestamp=e["timestamp"] if isinstance(e, dict) else e.timestamp,
                status=(
                    TradeLifecycleState(e["status"])
                    if isinstance(e, dict)
                    else e.status
                ),
                reason=e["reason"] if isinstance(e, dict) else e.reason,
                broker_reference=(
                    e["broker_reference"] if isinstance(e, dict) else e.broker_reference
                ),
                notes=e["notes"] if isinstance(e, dict) else e.notes,
            )
            for e in events
        ]
        event_objs.append(event)

        current_dict["lifecycle_events"] = tuple(event_objs)
        current_dict["execution_status"] = status

        # Special handling for open/close times
        if status in (
            TradeLifecycleState.PARTIALLY_FILLED,
            TradeLifecycleState.FILLED,
        ) and not current_dict.get("open_time"):
            current_dict["open_time"] = ts
        if status in (
            TradeLifecycleState.CLOSED,
            TradeLifecycleState.ARCHIVED,
        ) and not current_dict.get("close_time"):
            current_dict["close_time"] = ts

        # Apply any ad-hoc updates (e.g. exit_price, pnl)
        for key, value in updates.items():
            if key in current_dict:
                current_dict[key] = value

        new_entry = TradeJournalEntry(**current_dict)
        self.repository.update(new_entry)
        return new_entry

    def initialize_trade(self, entry: TradeJournalEntry) -> TradeJournalEntry:
        """Initialize a new trade in the journal."""
        self.repository.add(entry)
        return entry
