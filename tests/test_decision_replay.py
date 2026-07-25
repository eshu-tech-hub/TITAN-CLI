"""Tests for the Decision Replay system."""

from titan.decision.journal import (
    DecisionJournal,
)
from titan.decision.models import (
    DecisionAction,
    InstrumentType,
    TradeDecision,
    TradeDirection,
)
from titan.decision.replay import (
    DecisionReplayResult,
    DecisionReplayService,
    DecisionReplaySnapshot,
    DecisionReplayTimeline,
)


def create_dummy_decision(
    symbol: str = "AAPL", strategy: str = "test"
) -> TradeDecision:
    return TradeDecision(
        decision=DecisionAction.BUY,
        trade_direction=TradeDirection.LONG,
        instrument_type=InstrumentType.UNDERLYING,
        symbol=symbol,
        entry_strategy=strategy,
        confidence=0.85,
    )


def test_repository_get():
    journal = DecisionJournal()
    dec = create_dummy_decision()
    journal.record_decision(dec)

    entries = journal.repository.list()
    assert len(entries) == 1

    entry = journal.repository.get(entries[0].id)
    assert entry is not None
    assert entry.id == entries[0].id

    assert journal.repository.get("non-existent") is None


def test_repository_latest():
    journal = DecisionJournal()
    assert journal.repository.latest() is None

    journal.record_decision(create_dummy_decision())
    latest = journal.repository.latest()
    assert latest is not None


def test_repository_previous_next():
    journal = DecisionJournal()
    journal.record_decision(create_dummy_decision("AAPL"))
    journal.record_decision(create_dummy_decision("MSFT"))
    journal.record_decision(create_dummy_decision("GOOG"))

    # Chronological list (oldest to newest) since list() gives newest first
    entries = journal.repository.list()  # [GOOG, MSFT, AAPL] (newest first)

    # newest
    goog = entries[0]
    msft = entries[1]
    aapl = entries[2]

    # previous of newest (GOOG) is MSFT
    assert journal.repository.previous(goog.id) == msft
    # next of MSFT is GOOG
    assert journal.repository.next(msft.id) == goog

    # previous of AAPL is None
    assert journal.repository.previous(aapl.id) is None
    # next of GOOG is None
    assert journal.repository.next(goog.id) is None


def test_repository_list_pagination():
    journal = DecisionJournal()
    for i in range(10):
        journal.record_decision(create_dummy_decision(f"SYM{i}"))

    page1 = journal.repository.list(page=1, page_size=4)
    assert len(page1) == 4

    page3 = journal.repository.list(page=3, page_size=4)
    assert len(page3) == 2


def test_repository_search():
    journal = DecisionJournal()
    dec = create_dummy_decision()
    journal.record_decision(dec)

    results = journal.repository.search("buy")
    assert len(results) == 0  # not in explanation


def test_repository_filter():
    journal = DecisionJournal()
    journal.record_decision(create_dummy_decision("AAPL", "strat1"))
    journal.record_decision(create_dummy_decision("MSFT", "strat2"))
    journal.record_decision(create_dummy_decision("AAPL", "strat3"))

    results = journal.repository.filter(symbol="AAPL")
    assert len(results) == 2

    results = journal.repository.filter(strategy="strat2")
    assert len(results) == 1
    assert results[0].symbol == "MSFT"


def test_repository_count():
    journal = DecisionJournal()
    assert journal.repository.count() == 0
    journal.record_decision(create_dummy_decision())
    assert journal.repository.count() == 1


def test_decision_replay_service_latest():
    journal = DecisionJournal()
    service = DecisionReplayService(journal.repository)

    assert service.latest() is None

    journal.record_decision(create_dummy_decision())
    result = service.latest()
    assert result is not None
    assert isinstance(result, DecisionReplayResult)
    assert isinstance(result.snapshot, DecisionReplaySnapshot)
    assert isinstance(result.timeline, DecisionReplayTimeline)


def test_decision_replay_service_replay():
    journal = DecisionJournal()
    service = DecisionReplayService(journal.repository)

    assert service.replay("invalid") is None

    journal.record_decision(create_dummy_decision())
    latest = journal.repository.latest()

    result = service.replay(latest.id)
    assert result is not None
    assert result.snapshot.entry.id == latest.id
    assert len(result.timeline.events) == 1
    assert result.timeline.events[0] == "Decision Generated"
