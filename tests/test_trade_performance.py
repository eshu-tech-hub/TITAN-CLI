from datetime import UTC, datetime

import pytest

from titan.trading.journal import TradeJournalEntry, TradeLifecycleState
from titan.trading.performance import PerformanceAnalyzer


def create_mock_entry(
    trade_id: str,
    net_pnl: float,
    close_offset_hours: int = 1,
    direction: str = "LONG",
    strat: str = "Strat1",
) -> TradeJournalEntry:
    return TradeJournalEntry(
        trade_id=trade_id,
        decision_id="dec123",
        runtime_session_id="run123",
        symbol="AAPL",
        exchange="NSE",
        direction=direction,
        quantity=1,
        entry_price=100.0,
        exit_price=100.0 + net_pnl,
        gross_pnl=net_pnl + 5.0,
        net_pnl=net_pnl,
        fees=5.0,
        slippage=0.0,
        strategy=strat,
        tags=(),
        decision_status="executed",
        execution_status=TradeLifecycleState.CLOSED,
        open_time=datetime(2025, 1, 1, 10, 0, tzinfo=UTC),
        close_time=datetime(2025, 1, 1, 10 + close_offset_hours, 0, tzinfo=UTC),
        lifecycle_events=(),
    )


class TestPerformanceAnalyzer:
    @pytest.fixture
    def analyzer(self):
        return PerformanceAnalyzer()

    def test_empty_analysis(self, analyzer):
        perf = analyzer.analyze([])
        assert perf.overall.total_trades == 0
        assert perf.max_drawdown == 0.0

    def test_basic_metrics(self, analyzer):
        entries = [
            create_mock_entry("t1", net_pnl=100.0),
            create_mock_entry("t2", net_pnl=-50.0),
            create_mock_entry("t3", net_pnl=200.0),
        ]
        perf = analyzer.analyze(entries)
        assert perf.overall.total_trades == 3
        assert perf.overall.winning_trades == 2
        assert perf.overall.losing_trades == 1
        assert perf.overall.net_pnl == 250.0
        assert perf.overall.largest_winner == 200.0
        assert perf.overall.largest_loser == -50.0
        assert perf.overall.win_rate == pytest.approx(0.666, 0.01)

    def test_drawdown(self, analyzer):
        entries = [
            create_mock_entry("t1", net_pnl=100.0, close_offset_hours=1),  # Peak 100
            create_mock_entry("t2", net_pnl=-50.0, close_offset_hours=2),  # Drop to 50
            create_mock_entry(
                "t3", net_pnl=-20.0, close_offset_hours=3
            ),  # Drop to 30 (DD = 70)
            create_mock_entry("t4", net_pnl=200.0, close_offset_hours=4),  # Peak 230
        ]
        perf = analyzer.analyze(entries)
        assert perf.max_drawdown == 70.0

    def test_segments(self, analyzer):
        entries = [
            create_mock_entry("t1", net_pnl=100.0, direction="LONG", strat="S1"),
            create_mock_entry("t2", net_pnl=-50.0, direction="SHORT", strat="S1"),
            create_mock_entry("t3", net_pnl=200.0, direction="LONG", strat="S2"),
        ]
        perf = analyzer.analyze(entries)
        assert perf.long_stats.total_trades == 2
        assert perf.short_stats.total_trades == 1
        assert "S1" in perf.strategy_stats
        assert "S2" in perf.strategy_stats
        assert perf.strategy_stats["S1"].total_trades == 2
        assert perf.strategy_stats["S2"].total_trades == 1


@pytest.mark.parametrize(
    "pnl,expected_win",
    [
        (10.0, 1),
        (-10.0, 0),
        (0.0, 0),
    ],
)
@pytest.mark.parametrize("i", range(10))  # Generate 30 combinations
def test_win_loss_counting(pnl, expected_win, i):
    analyzer = PerformanceAnalyzer()
    entries = [create_mock_entry(f"t{i}", net_pnl=pnl)]
    perf = analyzer.analyze(entries)
    assert perf.overall.winning_trades == expected_win
