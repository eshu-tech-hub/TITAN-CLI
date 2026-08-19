import tempfile
from datetime import UTC, datetime
from pathlib import Path

from titan.backtesting.evaluation import (
    RegimePerformance,
    StrategyEvaluationReport,
    StrategyEvaluator,
    StrategyMetrics,
)
from titan.trading.journal import TradeJournalEntry, TradeLifecycleState


def make_sample_entry(
    trade_id: str,
    strategy: str,
    net_pnl: float,
    gross_pnl: float,
    regime_tag: str = "regime:trending",
) -> TradeJournalEntry:
    return TradeJournalEntry(
        trade_id=trade_id,
        decision_id="dec-1",
        runtime_session_id="sess-1",
        symbol="NIFTY",
        exchange="NSE",
        direction="LONG",
        quantity=10,
        entry_price=100.0,
        exit_price=110.0 if net_pnl > 0 else 90.0,
        gross_pnl=gross_pnl,
        net_pnl=net_pnl,
        fees=1.0,
        slippage=0.5,
        strategy=strategy,
        tags=(regime_tag,),
        decision_status="APPROVED",
        execution_status=TradeLifecycleState.CLOSED,
        open_time=datetime.now(UTC),
        close_time=datetime.now(UTC),
    )


def test_strategy_metrics_defaults():
    metrics = StrategyMetrics()
    assert metrics.strategy_name == "Default"
    assert metrics.total_trades == 0
    assert metrics.win_rate == 0.0


def test_strategy_evaluator_empty():
    evaluator = StrategyEvaluator()
    report = evaluator.evaluate_trades([])
    assert isinstance(report, StrategyEvaluationReport)
    assert len(report.strategies) == 0


def test_strategy_evaluator_trade_grouping():
    evaluator = StrategyEvaluator()
    entries = [
        make_sample_entry("t1", "TrendFollower", 100.0, 105.0, "regime:trending"),
        make_sample_entry("t2", "TrendFollower", -50.0, -45.0, "regime:trending"),
        make_sample_entry("t3", "MeanReversion", 200.0, 205.0, "regime:ranging"),
    ]

    report = evaluator.evaluate_trades(entries)
    assert len(report.strategies) == 2
    assert report.overall_best_strategy in ("MeanReversion", "TrendFollower")

    tf_metrics = next(
        s for s in report.strategies if s.strategy_name == "TrendFollower"
    )
    assert tf_metrics.total_trades == 2
    assert tf_metrics.winning_trades == 1
    assert tf_metrics.losing_trades == 1
    assert tf_metrics.win_rate == 0.5
    assert tf_metrics.net_pnl == 50.0

    # Regime check
    assert "TRENDING" in tf_metrics.regime_breakdown
    trending = tf_metrics.regime_breakdown["TRENDING"]
    assert isinstance(trending, RegimePerformance)
    assert trending.total_trades == 2


def test_strategy_evaluator_exports():
    evaluator = StrategyEvaluator()
    entries = [
        make_sample_entry("t1", "AlphaStrategy", 150.0, 155.0),
    ]
    report = evaluator.evaluate_trades(entries)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        json_path = tmp / "eval.json"
        csv_path = tmp / "eval.csv"

        evaluator.export_json(json_path, report)
        evaluator.export_csv(csv_path, report)

        assert json_path.exists()
        assert csv_path.exists()
        assert "AlphaStrategy" in csv_path.read_text()
