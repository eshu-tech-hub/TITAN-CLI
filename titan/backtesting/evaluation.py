"""Historical Strategy Analytics Engine.

Provides deterministic evaluation of historical backtest performance,
decomposing metrics by strategy and market regime.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from titan.backtesting.models import BacktestReport
from titan.trading.journal import TradeJournalEntry


@dataclass(frozen=True, slots=True)
class RegimePerformance:
    """Performance breakdown for a strategy within a specific market regime."""

    regime: str = "UNKNOWN"
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    net_pnl: float = 0.0
    average_trade: float = 0.0


@dataclass(frozen=True, slots=True)
class StrategyMetrics:
    """Comprehensive performance metrics for a specific strategy."""

    strategy_name: str = "Default"
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    gross_pnl: float = 0.0
    net_pnl: float = 0.0
    max_drawdown: float = 0.0
    average_winner: float = 0.0
    average_loser: float = 0.0
    average_holding_time: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    regime_breakdown: Mapping[str, RegimePerformance] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class StrategyEvaluationReport:
    """Master report containing strategy analytics and evaluation scorecards."""

    strategies: tuple[StrategyMetrics, ...] = field(default_factory=tuple)
    overall_best_strategy: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Mapping[str, Any] = field(default_factory=dict)


class StrategyEvaluator:
    """Evaluates historical strategy performance across market regimes."""

    def evaluate_trades(
        self, entries: Sequence[TradeJournalEntry]
    ) -> StrategyEvaluationReport:
        """Evaluate a collection of journal entries grouped by strategy."""
        if not entries:
            return StrategyEvaluationReport()

        by_strategy: dict[str, list[TradeJournalEntry]] = {}
        for entry in entries:
            strat = entry.strategy or "Default"
            by_strategy.setdefault(strat, []).append(entry)

        metrics_list: list[StrategyMetrics] = []
        best_pnl = float("-inf")
        best_strat_name = ""

        for strat_name, strat_entries in by_strategy.items():
            metrics = self._compute_strategy_metrics(strat_name, strat_entries)
            metrics_list.append(metrics)

            if metrics.net_pnl > best_pnl:
                best_pnl = metrics.net_pnl
                best_strat_name = strat_name

        return StrategyEvaluationReport(
            strategies=tuple(metrics_list),
            overall_best_strategy=best_strat_name,
        )

    def evaluate_backtest_report(self, report: BacktestReport) -> StrategyMetrics:
        """Convert a BacktestReport into standardized StrategyMetrics."""
        stats = report.statistics
        metrics = report.metrics

        return StrategyMetrics(
            strategy_name=report.symbol or "BacktestStrategy",
            total_trades=stats.total_trades,
            winning_trades=stats.winning_trades,
            losing_trades=stats.losing_trades,
            win_rate=float(stats.win_rate),
            profit_factor=float(stats.profit_factor),
            expectancy=float(stats.expectancy),
            net_pnl=float(report.total_pnl),
            max_drawdown=float(stats.max_drawdown),
            sharpe_ratio=float(metrics.sharpe_ratio),
            sortino_ratio=float(metrics.sortino_ratio),
        )

    def _compute_strategy_metrics(
        self, strat_name: str, entries: Sequence[TradeJournalEntry]
    ) -> StrategyMetrics:
        """Compute metrics for a specific subset of strategy trades."""
        total_trades = len(entries)
        if total_trades == 0:
            return StrategyMetrics(strategy_name=strat_name)

        wins = [e for e in entries if e.net_pnl > 0]
        losses = [e for e in entries if e.net_pnl < 0]

        gross_profit = sum(e.gross_pnl for e in wins)
        gross_loss = abs(sum(e.gross_pnl for e in losses))
        net_pnl = sum(e.net_pnl for e in entries)

        win_rate = len(wins) / total_trades if total_trades > 0 else 0.0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
        avg_winner = gross_profit / len(wins) if wins else 0.0
        avg_loser = gross_loss / len(losses) if losses else 0.0

        expectancy = (win_rate * avg_winner) - ((1.0 - win_rate) * avg_loser)

        total_hold_time = sum(e.holding_time_seconds for e in entries)
        avg_hold_time = total_hold_time / total_trades if total_trades > 0 else 0.0

        # Calculate regime breakdown based on tags (e.g. "regime:trending")
        regime_trades: dict[str, list[TradeJournalEntry]] = {}
        for e in entries:
            regime = "UNKNOWN"
            for tag in e.tags:
                if tag.startswith("regime:"):
                    regime = tag.split(":", 1)[1].upper()
                    break
            regime_trades.setdefault(regime, []).append(e)

        regime_breakdown: dict[str, RegimePerformance] = {}
        for reg_name, r_entries in regime_trades.items():
            r_total = len(r_entries)
            r_wins = [e for e in r_entries if e.net_pnl > 0]
            r_losses = [e for e in r_entries if e.net_pnl < 0]
            r_gp = sum(e.gross_pnl for e in r_wins)
            r_gl = abs(sum(e.gross_pnl for e in r_losses))
            r_net = sum(e.net_pnl for e in r_entries)
            r_pf = r_gp / r_gl if r_gl > 0 else float("inf")

            regime_breakdown[reg_name] = RegimePerformance(
                regime=reg_name,
                total_trades=r_total,
                winning_trades=len(r_wins),
                losing_trades=len(r_losses),
                win_rate=len(r_wins) / r_total if r_total > 0 else 0.0,
                profit_factor=r_pf,
                gross_profit=r_gp,
                gross_loss=r_gl,
                net_pnl=r_net,
                average_trade=r_net / r_total if r_total > 0 else 0.0,
            )

        return StrategyMetrics(
            strategy_name=strat_name,
            total_trades=total_trades,
            winning_trades=len(wins),
            losing_trades=len(losses),
            win_rate=win_rate,
            profit_factor=profit_factor,
            expectancy=expectancy,
            gross_pnl=gross_profit - gross_loss,
            net_pnl=net_pnl,
            average_winner=avg_winner,
            average_loser=avg_loser,
            average_holding_time=avg_hold_time,
            regime_breakdown=regime_breakdown,
        )

    def export_csv(self, filepath: Path, report: StrategyEvaluationReport) -> None:
        """Export strategy evaluation report to a CSV file."""
        fields = [
            "Strategy Name",
            "Total Trades",
            "Win Rate",
            "Profit Factor",
            "Expectancy",
            "Net PnL",
            "Sharpe Ratio",
            "Max Drawdown",
        ]

        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(fields)
            for strat in report.strategies:
                writer.writerow(
                    [
                        strat.strategy_name,
                        strat.total_trades,
                        f"{strat.win_rate * 100:.1f}%",
                        f"{strat.profit_factor:.2f}",
                        f"{strat.expectancy:.2f}",
                        f"{strat.net_pnl:.2f}",
                        f"{strat.sharpe_ratio:.2f}",
                        f"{strat.max_drawdown:.2f}",
                    ]
                )

    def export_json(self, filepath: Path, report: StrategyEvaluationReport) -> None:
        """Export strategy evaluation report to a JSON file."""

        def custom_serializer(obj: Any) -> Any:
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")

        data = asdict(report)
        with open(filepath, mode="w", encoding="utf-8") as f:
            json.dump(data, f, default=custom_serializer, indent=2)
