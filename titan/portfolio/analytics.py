import csv
import json
from collections.abc import Sequence
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from titan.portfolio.models import (
    AllocationAnalysis,
    DiversificationAnalysis,
    DrawdownAnalysis,
    ExistingPortfolio,
    ExposureAnalysis,
    PortfolioPerformance,
    PortfolioSnapshot,
)
from titan.trading.journal import TradeJournalEntry
from titan.trading.performance import PerformanceAnalyzer


class PortfolioAnalytics:
    """Read-only portfolio analytics engine.

    Generates institutional-grade portfolio metrics from the Trade Journal
    and current portfolio state, without calling broker APIs or mutating data.
    """

    def __init__(self, performance_analyzer: PerformanceAnalyzer | None = None) -> None:
        self.performance_analyzer = performance_analyzer or PerformanceAnalyzer()

    def generate_snapshot(self, portfolio: ExistingPortfolio) -> PortfolioSnapshot:
        """Generate a current snapshot of the portfolio."""
        capital_used = sum(p.market_value for p in portfolio.positions)
        total_market_value = capital_used
        total_pnl = sum(p.pnl for p in portfolio.positions)

        wins = sum(1 for p in portfolio.positions if p.pnl > 0)
        losses = sum(1 for p in portfolio.positions if p.pnl <= 0)

        utilization = (
            capital_used / portfolio.total_capital
            if portfolio.total_capital > 0
            else 0.0
        )

        return PortfolioSnapshot(
            total_capital=portfolio.total_capital,
            cash_reserve=portfolio.cash_reserve,
            capital_used=capital_used,
            available_capital=portfolio.total_capital - capital_used,
            total_market_value=total_market_value,
            total_pnl=total_pnl,
            position_count=len(portfolio.positions),
            winning_positions=wins,
            losing_positions=losses,
            utilization=utilization,
        )

    def analyze_exposure(self, portfolio: ExistingPortfolio) -> ExposureAnalysis:
        """Analyze portfolio exposure."""
        if not portfolio.positions:
            return ExposureAnalysis()

        gross_exposure = sum(abs(p.market_value) for p in portfolio.positions)
        net_exposure = sum(
            p.market_value if p.direction.lower() == "long" else -p.market_value
            for p in portfolio.positions
        )
        long_exposure = sum(
            p.market_value for p in portfolio.positions if p.direction.lower() == "long"
        )
        short_exposure = sum(
            p.market_value
            for p in portfolio.positions
            if p.direction.lower() == "short"
        )

        sorted_pos = sorted(
            portfolio.positions, key=lambda x: x.market_value, reverse=True
        )
        largest = sorted_pos[0]
        smallest = sorted_pos[-1]

        # Simple Herfindahl-Hirschman Index (HHI) for concentration
        total_val = sum(abs(p.market_value) for p in portfolio.positions)
        hhi = 0.0
        if total_val > 0:
            for p in portfolio.positions:
                weight = abs(p.market_value) / total_val
                hhi += (weight * 100) ** 2

        return ExposureAnalysis(
            gross_exposure=gross_exposure,
            net_exposure=net_exposure,
            long_exposure=long_exposure,
            short_exposure=short_exposure,
            position_count=len(portfolio.positions),
            largest_position_symbol=largest.symbol,
            largest_position_weight=(
                largest.market_value / total_val if total_val > 0 else 0.0
            ),
            smallest_position_symbol=smallest.symbol,
            smallest_position_weight=(
                smallest.market_value / total_val if total_val > 0 else 0.0
            ),
            concentration_score=hhi,
        )

    def analyze_allocation(self, portfolio: ExistingPortfolio) -> AllocationAnalysis:
        """Analyze capital allocation by various dimensions."""
        if not portfolio.positions:
            return AllocationAnalysis()

        total_val = sum(abs(p.market_value) for p in portfolio.positions)
        if total_val == 0:
            return AllocationAnalysis()

        by_inst: dict[str, float] = {}
        by_strat: dict[str, float] = {}
        by_sect: dict[str, float] = {}
        by_class: dict[str, float] = {}

        for p in portfolio.positions:
            w = abs(p.market_value) / total_val
            by_inst[p.symbol] = by_inst.get(p.symbol, 0.0) + w
            by_sect[p.sector or "Unknown"] = by_sect.get(p.sector or "Unknown", 0.0) + w
            by_class[p.instrument_type] = by_class.get(p.instrument_type, 0.0) + w
            # Current positions model doesn't explicitly store strategy, so we assign "Default"
            by_strat["Default"] = by_strat.get("Default", 0.0) + w

        return AllocationAnalysis(
            by_instrument=by_inst,
            by_strategy=by_strat,
            by_sector=by_sect,
            by_asset_class=by_class,
        )

    def analyze_diversification(
        self, portfolio: ExistingPortfolio
    ) -> DiversificationAnalysis:
        """Analyze portfolio diversification."""
        if not portfolio.positions:
            return DiversificationAnalysis()

        symbols = {p.symbol for p in portfolio.positions}
        # HHI interpretation: 10000 = perfectly concentrated, lower = more diversified
        exposure = self.analyze_exposure(portfolio)
        hhi = exposure.concentration_score

        # Invert HHI for a simple 0-100 diversification score (100 = perfectly diversified)
        div_score = max(0.0, 100.0 - (hhi / 100.0))

        allocation = self.analyze_allocation(portfolio)

        return DiversificationAnalysis(
            number_of_symbols=len(symbols),
            number_of_strategies=1,
            sector_distribution=allocation.by_sector,
            concentration_risk=hhi,
            diversification_score=div_score,
        )

    def analyze_drawdown(
        self, entries: Sequence[TradeJournalEntry], starting_capital: float = 0.0
    ) -> DrawdownAnalysis:
        """Analyze drawdown and equity curves from historical trades."""
        if not entries:
            return DrawdownAnalysis(
                peak_equity=starting_capital, current_equity=starting_capital
            )

        # Re-use PerformanceAnalyzer for max drawdown if available, or compute locally
        closed_entries = [e for e in entries if e.close_time is not None]
        closed_entries.sort(
            key=lambda x: x.close_time or datetime.min.replace(tzinfo=UTC)
        )

        equity = starting_capital
        peak = starting_capital
        max_dd = 0.0

        for e in closed_entries:
            equity += e.net_pnl
            peak = max(peak, equity)
            dd = peak - equity
            max_dd = max(max_dd, dd)

        current_dd = peak - equity
        recovery = 0.0
        if current_dd > 0 and max_dd > 0:
            recovery = (max_dd - current_dd) / max_dd * 100.0
        elif max_dd > 0 and current_dd == 0:
            recovery = 100.0

        return DrawdownAnalysis(
            current_drawdown=current_dd,
            max_drawdown=max_dd,
            peak_equity=peak,
            current_equity=equity,
            recovery_percentage=recovery,
        )

    def analyze_performance(
        self, entries: Sequence[TradeJournalEntry]
    ) -> PortfolioPerformance:
        """Analyze institutional portfolio performance."""
        # Delegate heavy lifting to PerformanceAnalyzer to avoid duplicating logic
        trade_perf = self.performance_analyzer.analyze(entries)

        loss_rate = (
            1.0 - trade_perf.overall.win_rate
            if trade_perf.overall.total_trades > 0
            else 0.0
        )

        return PortfolioPerformance(
            win_rate=trade_perf.overall.win_rate,
            loss_rate=loss_rate,
            profit_factor=trade_perf.overall.profit_factor,
            expectancy=trade_perf.overall.expectancy,
            average_winner=trade_perf.overall.average_winner,
            average_loser=trade_perf.overall.average_loser,
            average_holding_time=trade_perf.overall.average_hold_time_seconds,
        )

    def export_csv(
        self,
        filepath: Path,
        portfolio: ExistingPortfolio,
        entries: Sequence[TradeJournalEntry],
    ) -> None:
        """Export portfolio analytics to CSV."""
        snapshot = self.generate_snapshot(portfolio)
        exposure = self.analyze_exposure(portfolio)
        drawdown = self.analyze_drawdown(
            entries, starting_capital=portfolio.total_capital
        )
        performance = self.analyze_performance(entries)

        fields = [
            "Timestamp",
            "Total Capital",
            "Capital Used",
            "Total PnL",
            "Gross Exposure",
            "Net Exposure",
            "Concentration Score",
            "Max Drawdown",
            "Current Drawdown",
            "Win Rate",
            "Profit Factor",
        ]

        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(fields)
            writer.writerow(
                [
                    datetime.now(UTC).isoformat(),
                    snapshot.total_capital,
                    snapshot.capital_used,
                    snapshot.total_pnl,
                    exposure.gross_exposure,
                    exposure.net_exposure,
                    exposure.concentration_score,
                    drawdown.max_drawdown,
                    drawdown.current_drawdown,
                    performance.win_rate,
                    performance.profit_factor,
                ]
            )

    def export_json(
        self,
        filepath: Path,
        portfolio: ExistingPortfolio,
        entries: Sequence[TradeJournalEntry],
    ) -> None:
        """Export complete analytical state to JSON."""
        data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "snapshot": asdict(self.generate_snapshot(portfolio)),
            "exposure": asdict(self.analyze_exposure(portfolio)),
            "allocation": asdict(self.analyze_allocation(portfolio)),
            "diversification": asdict(self.analyze_diversification(portfolio)),
            "drawdown": asdict(
                self.analyze_drawdown(entries, starting_capital=portfolio.total_capital)
            ),
            "performance": asdict(self.analyze_performance(entries)),
        }

        with open(filepath, mode="w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
