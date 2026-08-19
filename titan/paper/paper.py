from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from titan.core.evidence.confidence import Confidence
from titan.core.evidence.evidence import Evidence
from titan.core.evidence.models import EvidenceCategory, EvidenceSignal
from titan.core.evidence.score import Score
from titan.paper.models import (
    PaperFill,
    PaperOrder,
    PaperPerformanceMetrics,
    PaperPortfolioState,
    PaperPosition,
)


@dataclass(frozen=True, slots=True)
class PaperTradingReport:
    """Comprehensive report of paper trading activity.

    Aggregates all orders, trades, positions, portfolio state,
    performance metrics, warnings, and errors from a paper
    trading session.

    Attributes:
        orders: All orders placed during the session.
        trades: All fills executed.
        positions: Current open positions.
        portfolio_state: Latest portfolio snapshot.
        performance: Computed performance metrics.
        warnings: Any warnings generated.
        errors: Any errors encountered.
        timestamp: When the report was generated.
    """

    orders: tuple[PaperOrder, ...] = field(default_factory=tuple)
    trades: tuple[PaperFill, ...] = field(default_factory=tuple)
    positions: tuple[PaperPosition, ...] = field(default_factory=tuple)
    portfolio_state: PaperPortfolioState = field(default_factory=PaperPortfolioState)
    performance: PaperPerformanceMetrics = field(
        default_factory=PaperPerformanceMetrics
    )
    warnings: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class PaperTradingExplanation:
    """Human-readable explanation of paper trading results.

    Attributes:
        execution: Summary of order execution activity.
        portfolio: Summary of portfolio state.
        performance: Summary of performance metrics.
        open_positions: Summary of open positions.
        closed_positions: Summary of closed positions.
        summary: One-line overall summary.
    """

    execution: str = ""
    portfolio: str = ""
    performance: str = ""
    open_positions: str = ""
    closed_positions: str = ""
    summary: str = ""


def generate_evidence(
    report: PaperTradingReport,
) -> Evidence:
    """Generate evidence from a paper trading report.

    Produces an Evidence item with category EXECUTION and
    metadata describing the paper execution simulation.

    Args:
        report: The paper trading report to generate evidence from.

    Returns:
        Evidence item describing the paper execution.
    """
    total_orders = len(report.orders)
    filled_orders = sum(1 for o in report.orders if o.status.value == "filled")

    total_pnl = report.portfolio_state.total_pnl
    execution_count = report.portfolio_state.position_count

    signal: EvidenceSignal = EvidenceSignal.NEUTRAL
    if total_pnl > Decimal(0):
        signal = EvidenceSignal.BULLISH
    elif total_pnl < Decimal(0):
        signal = EvidenceSignal.BEARISH

    score_value = min(
        abs(float(total_pnl)),
        100.0,
    )
    reasons: list[str] = []
    if total_orders > 0:
        reasons.append(f"{filled_orders} of {total_orders} orders filled")
    reasons.append(f"P&L: {total_pnl}")

    metadata: dict[str, Any] = {
        "paper_execution": True,
        "simulation": True,
        "fill_quality": "deterministic",
        "execution_latency_ms": 50,
        "total_orders": total_orders,
        "filled_orders": filled_orders,
        "open_positions": execution_count,
    }

    return Evidence(
        source="titan.paper",
        category=EvidenceCategory.EXECUTION,
        signal=signal,
        score=Score(score_value),
        confidence=Confidence(1.0),
        weight=1.0,
        reasons=tuple(reasons),
        metadata=metadata,
    )


def generate_explanation(
    report: PaperTradingReport,
) -> PaperTradingExplanation:
    """Generate a human-readable explanation of paper trading results.

    Args:
        report: The paper trading report to explain.

    Returns:
        PaperTradingExplanation with section summaries.
    """
    total_orders = len(report.orders)
    filled_orders = sum(1 for o in report.orders if o.status.value == "filled")
    pending_orders = sum(
        1 for o in report.orders if o.status.value in ("pending", "open")
    )

    execution = (
        f"Placed {total_orders} order(s), "
        f"{filled_orders} filled, "
        f"{pending_orders} pending"
    )

    ps = report.portfolio_state
    portfolio = f"Cash: {ps.cash}, Equity: {ps.equity}, P&L: {ps.total_pnl}"

    perf = report.performance
    performance_str = (
        f"Win rate: {perf.win_rate:.1%}, "
        f"Profit factor: {perf.profit_factor:.2f}, "
        f"Total trades: {perf.total_trades}"
    )

    open_pos = report.positions
    if open_pos:
        open_str = "; ".join(
            f"{p.symbol}: qty={p.quantity}, "
            f"avg={p.average_price}, "
            f"P&L={p.unrealized_pnl}"
            for p in open_pos
        )
    else:
        open_str = "No open positions"

    closed_str = "No closed positions"

    summary = (
        f"Paper trading completed: "
        f"{filled_orders} filled / {total_orders} total orders, "
        f"P&L={ps.total_pnl}"
    )

    return PaperTradingExplanation(
        execution=execution,
        portfolio=portfolio,
        performance=performance_str,
        open_positions=open_str,
        closed_positions=closed_str,
        summary=summary,
    )
