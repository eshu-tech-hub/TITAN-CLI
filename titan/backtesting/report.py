from decimal import Decimal

from titan.backtesting.models import (
    BacktestExplanation,
    BacktestReport,
)
from titan.core.evidence.confidence import Confidence
from titan.core.evidence.evidence import Evidence
from titan.core.evidence.models import EvidenceCategory, EvidenceSignal
from titan.core.evidence.score import Score


def generate_evidence(report: BacktestReport) -> Evidence:
    """Generate evidence from a backtest report.

    Produces an Evidence item with category SYSTEM and metadata
    describing the backtest run.

    Args:
        report: The backtest report to generate evidence from.

    Returns:
        Evidence item describing the backtest execution.
    """
    signal: EvidenceSignal = EvidenceSignal.NEUTRAL
    if report.total_pnl > Decimal("0"):
        signal = EvidenceSignal.BULLISH
    elif report.total_pnl < Decimal("0"):
        signal = EvidenceSignal.BEARISH

    score_value = min(abs(float(report.total_pnl)), 100.0)

    reasons: list[str] = []
    reasons.append(f"Backtest completed: {report.bars_processed} bars processed")
    reasons.append(f"Total trades: {report.statistics.total_trades}")
    reasons.append(f"Win rate: {report.statistics.win_rate:.1%}")
    reasons.append(f"P&L: {report.total_pnl}")

    metadata: dict[str, object] = {
        "backtest_run": True,
        "dataset_symbol": report.symbol,
        "dataset_exchange": report.exchange,
        "bars_processed": report.bars_processed,
        "replay_duration_seconds": report.duration_seconds,
        "total_trades": report.statistics.total_trades,
        "win_rate": report.statistics.win_rate,
        "profit_factor": report.statistics.profit_factor,
        "total_pnl": str(report.total_pnl),
        "total_return": str(report.total_return),
        "max_drawdown": str(report.statistics.max_drawdown),
        "sharpe_ratio": report.metrics.sharpe_ratio,
    }

    return Evidence(
        source="titan.backtesting",
        category=EvidenceCategory.SYSTEM,
        signal=signal,
        score=Score(score_value),
        confidence=Confidence(1.0),
        weight=1.0,
        reasons=tuple(reasons),
        metadata=metadata,
    )


def generate_explanation(report: BacktestReport) -> BacktestExplanation:
    """Generate a human-readable explanation of backtest results.

    Args:
        report: The backtest report to explain.

    Returns:
        BacktestExplanation with section summaries.
    """
    dataset_str = (
        f"Symbol: {report.symbol} on {report.exchange}, "
        f"{report.bars_processed} bars from "
        f"{report.start_time} to {report.end_time}"
    )

    bars_per_sec = (
        f"{report.bars_processed / report.duration_seconds:.0f}"
        if report.duration_seconds > 0
        else "N/A"
    )
    simulation_str = (
        f"Processed {report.bars_processed} bars in "
        f"{report.duration_seconds:.2f}s "
        f"({bars_per_sec} bars/s)"
    )

    s = report.statistics
    performance_str = (
        f"Win rate: {s.win_rate:.1%}, "
        f"Profit factor: {s.profit_factor:.2f}, "
        f"Total trades: {s.total_trades}, "
        f"Max drawdown: {s.max_drawdown}"
    )

    m = report.metrics
    risk_str = (
        f"Sharpe: {m.sharpe_ratio:.2f}, "
        f"Sortino: {m.sortino_ratio:.2f}, "
        f"Calmar: {m.calmar_ratio:.2f}, "
        f"Volatility: {m.volatility:.2%}"
    )

    portfolio_str = (
        f"Capital: {report.total_capital} -> "
        f"{report.final_equity}, "
        f"Return: {report.total_return:.2%}"
    )

    summary_str = (
        f"Backtest of {report.symbol} completed: "
        f"{report.statistics.total_trades} trades, "
        f"P&L={report.total_pnl}, "
        f"return={report.total_return:.2%}"
    )

    return BacktestExplanation(
        dataset=dataset_str,
        simulation=simulation_str,
        performance=performance_str,
        risk=risk_str,
        portfolio=portfolio_str,
        summary=summary_str,
    )
