import json
from datetime import UTC, datetime, timedelta

import pytest

from titan.portfolio.analytics import PortfolioAnalytics
from titan.portfolio.models import (
    ExistingPortfolio,
    OpenPosition,
)
from titan.trading.journal import TradeJournalEntry, TradeLifecycleState


@pytest.fixture
def empty_portfolio():
    return ExistingPortfolio(total_capital=100000.0, cash_reserve=100000.0)


@pytest.fixture
def mixed_portfolio():
    return ExistingPortfolio(
        total_capital=100000.0,
        cash_reserve=50000.0,
        positions=(
            OpenPosition(
                "AAPL", "Equity", "Long", 100, 150.0, 160.0, 16000.0, 1000.0, "Tech"
            ),
            OpenPosition(
                "MSFT", "Equity", "Short", 50, 300.0, 290.0, 14500.0, 500.0, "Tech"
            ),
            OpenPosition(
                "TSLA", "Equity", "Long", 20, 200.0, 180.0, 3600.0, -400.0, "Auto"
            ),
        ),
    )


@pytest.fixture
def analytics_engine():
    return PortfolioAnalytics()


@pytest.fixture
def sample_trades():
    now = datetime.now(UTC)
    return [
        TradeJournalEntry(
            trade_id=f"t{i}",
            decision_id=f"d{i}",
            runtime_session_id="s1",
            symbol="AAPL",
            exchange="NASDAQ",
            direction="Long",
            quantity=10,
            entry_price=100.0,
            exit_price=110.0 if i % 2 == 0 else 90.0,
            gross_pnl=100.0 if i % 2 == 0 else -100.0,
            net_pnl=95.0 if i % 2 == 0 else -105.0,
            fees=5.0,
            slippage=0.0,
            strategy="Trend",
            tags=(),
            decision_status="executed",
            execution_status=TradeLifecycleState.CLOSED,
            open_time=now - timedelta(days=i + 1),
            close_time=now - timedelta(days=i),
        )
        for i in range(20)
    ]


class TestPortfolioAnalytics:
    def test_snapshot_empty(self, analytics_engine, empty_portfolio):
        snap = analytics_engine.generate_snapshot(empty_portfolio)
        assert snap.total_capital == 100000.0
        assert snap.capital_used == 0.0
        assert snap.position_count == 0

    def test_snapshot_mixed(self, analytics_engine, mixed_portfolio):
        snap = analytics_engine.generate_snapshot(mixed_portfolio)
        assert snap.position_count == 3
        assert snap.total_pnl == 1100.0
        assert snap.winning_positions == 2
        assert snap.losing_positions == 1

    @pytest.mark.parametrize("i", range(50))
    def test_exposure_combinations(self, analytics_engine, i):
        portfolio = ExistingPortfolio(
            total_capital=10000,
            positions=tuple(
                OpenPosition(
                    f"SYM{j}",
                    "Eq",
                    "Long" if j % 2 == 0 else "Short",
                    1,
                    10,
                    10,
                    100,
                    0,
                    "Sec",
                )
                for j in range(i)
            ),
        )
        exp = analytics_engine.analyze_exposure(portfolio)
        assert exp.position_count == i
        if i > 0:
            assert exp.gross_exposure == i * 100

    @pytest.mark.parametrize("i", range(50))
    def test_allocation_combinations(self, analytics_engine, i):
        portfolio = ExistingPortfolio(
            total_capital=10000,
            positions=tuple(
                OpenPosition(f"SYM{j}", "Eq", "Long", 1, 10, 10, 100, 0, f"Sec{j % 3}")
                for j in range(i)
            ),
        )
        alloc = analytics_engine.analyze_allocation(portfolio)
        if i > 0:
            assert len(alloc.by_sector) == min(i, 3)

    @pytest.mark.parametrize("i", range(50))
    def test_diversification_combinations(self, analytics_engine, i):
        portfolio = ExistingPortfolio(
            total_capital=10000,
            positions=tuple(
                OpenPosition(f"SYM{j}", "Eq", "Long", 1, 10, 10, 100, 0, "Sec")
                for j in range(i)
            ),
        )
        div = analytics_engine.analyze_diversification(portfolio)
        assert div.number_of_symbols == i

    @pytest.mark.parametrize("i", range(50))
    def test_drawdown_combinations(self, analytics_engine, i):
        trades = [
            TradeJournalEntry(
                trade_id=str(j),
                decision_id="",
                runtime_session_id="",
                symbol="",
                exchange="",
                direction="Long",
                quantity=1,
                entry_price=10,
                exit_price=11,
                gross_pnl=1,
                net_pnl=-1,
                fees=0,
                slippage=0,
                strategy="",
                tags=(),
                decision_status="",
                execution_status=TradeLifecycleState.CLOSED,
                open_time=datetime.now(UTC),
                close_time=datetime.now(UTC),
            )
            for j in range(i)
        ]
        dd = analytics_engine.analyze_drawdown(trades, 1000.0)
        assert dd.current_equity == 1000.0 - i

    def test_performance(self, analytics_engine, sample_trades):
        perf = analytics_engine.analyze_performance(sample_trades)
        assert perf.win_rate == 0.5
        assert perf.loss_rate == 0.5

    def test_exports(self, analytics_engine, mixed_portfolio, sample_trades, tmp_path):
        csv_path = tmp_path / "export.csv"
        json_path = tmp_path / "export.json"

        analytics_engine.export_csv(csv_path, mixed_portfolio, sample_trades)
        analytics_engine.export_json(json_path, mixed_portfolio, sample_trades)

        assert csv_path.exists()
        assert json_path.exists()

        with open(json_path) as f:
            data = json.load(f)
            assert "snapshot" in data
            assert "exposure" in data
