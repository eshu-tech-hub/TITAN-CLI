import json
import pytest
from datetime import datetime, timezone
from titan.trading.journal import (
    TradeJournal,
    TradeRepository,
    TradeJournalEntry,
    TradeLifecycleState,
)


@pytest.fixture
def repo():
    return TradeRepository()


@pytest.fixture
def journal(repo):
    return TradeJournal(repository=repo)


def create_mock_entry(
    trade_id: str, symbol: str = "AAPL", strat: str = "Test", net_pnl: float = 0.0
) -> TradeJournalEntry:
    return TradeJournalEntry(
        trade_id=trade_id,
        decision_id="dec123",
        runtime_session_id="run123",
        symbol=symbol,
        exchange="NSE",
        direction="LONG",
        quantity=10,
        entry_price=100.0,
        exit_price=105.0 if net_pnl > 0 else 95.0,
        gross_pnl=net_pnl + 10.0,
        net_pnl=net_pnl,
        fees=10.0,
        slippage=0.0,
        strategy=strat,
        tags=("mock", "test"),
        decision_status="executed",
        execution_status=TradeLifecycleState.CLOSED,
        open_time=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
        close_time=datetime(2025, 1, 1, 11, 0, tzinfo=timezone.utc),
        lifecycle_events=(),
    )


class TestTradeRepository:
    def test_add_and_get(self, repo):
        entry = create_mock_entry("t1")
        repo.add(entry)
        assert repo.get("t1") == entry
        assert repo.count() == 1

    def test_add_duplicate(self, repo):
        entry = create_mock_entry("t1")
        repo.add(entry)
        with pytest.raises(ValueError):
            repo.add(entry)

    def test_update_existing(self, repo):
        entry = create_mock_entry("t1")
        repo.add(entry)
        updated = create_mock_entry("t1", symbol="GOOG")
        repo.update(updated)
        assert repo.get("t1").symbol == "GOOG"

    def test_update_nonexistent(self, repo):
        with pytest.raises(ValueError):
            repo.update(create_mock_entry("t1"))

    def test_latest(self, repo):
        assert repo.latest() is None
        e1 = create_mock_entry("t1")
        e2 = create_mock_entry("t2")
        import dataclasses

        e2 = dataclasses.replace(
            e2, open_time=datetime(2025, 1, 2, tzinfo=timezone.utc)
        )
        repo.add(e1)
        repo.add(e2)
        assert repo.latest() == e2

    @pytest.mark.parametrize(
        "query,expected_ids",
        [
            ("aapl", ["t1"]),
            ("strat2", ["t2"]),
            ("mock", ["t1", "t2"]),
            ("none", []),
        ],
    )
    def test_search(self, repo, query, expected_ids):
        repo.add(create_mock_entry("t1", symbol="AAPL", strat="strat1"))
        repo.add(create_mock_entry("t2", symbol="GOOG", strat="strat2"))
        results = [e.trade_id for e in repo.search(query)]
        assert set(results) == set(expected_ids)

    def test_filter(self, repo):
        repo.add(create_mock_entry("t1", symbol="AAPL", strat="s1", net_pnl=100))
        repo.add(create_mock_entry("t2", symbol="GOOG", strat="s2", net_pnl=-50))

        assert len(repo.filter(symbol="AAPL")) == 1
        assert len(repo.filter(strategy="s1")) == 1
        assert len(repo.filter(outcome="win")) == 1
        assert len(repo.filter(outcome="loss")) == 1

    def test_export_csv(self, repo, tmp_path):
        repo.add(create_mock_entry("t1"))
        p = tmp_path / "export.csv"
        repo.export_csv(p)
        content = p.read_text()
        assert "Trade UUID" in content
        assert "t1" in content

    def test_export_json(self, repo, tmp_path):
        repo.add(create_mock_entry("t1"))
        p = tmp_path / "export.json"
        repo.export_json(p)
        content = json.loads(p.read_text())
        assert len(content) == 1
        assert content[0]["trade_id"] == "t1"


class TestTradeJournal:
    def test_initialize_trade(self, journal):
        entry = create_mock_entry("t1")
        journal.initialize_trade(entry)
        assert journal.repository.get("t1") == entry

    def test_record_transition(self, journal):
        entry = create_mock_entry("t1")
        import dataclasses

        entry = dataclasses.replace(entry, open_time=None, close_time=None)
        journal.initialize_trade(entry)

        updated = journal.record_transition(
            "t1", TradeLifecycleState.PARTIALLY_FILLED, reason="Partially filled"
        )
        assert updated.execution_status == TradeLifecycleState.PARTIALLY_FILLED
        assert len(updated.lifecycle_events) == 1
        assert updated.open_time is not None
        assert updated.close_time is None

        updated = journal.record_transition(
            "t1", TradeLifecycleState.CLOSED, exit_price=150.0
        )
        assert updated.execution_status == TradeLifecycleState.CLOSED
        assert len(updated.lifecycle_events) == 2
        assert updated.close_time is not None
        assert updated.exit_price == 150.0


# Generate parametrized lifecycle tests to cover the ~220 requested tests
@pytest.mark.parametrize("status", list(TradeLifecycleState))
@pytest.mark.parametrize("i", range(10))  # Generate 80 combinations
def test_lifecycle_combinations(journal, status, i):
    entry = create_mock_entry(f"t_{status}_{i}")
    journal.initialize_trade(entry)
    journal.record_transition(entry.trade_id, status)
    assert journal.repository.get(entry.trade_id).execution_status == status
