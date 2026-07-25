from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Mapping, Sequence

from titan.trading.journal import TradeJournalEntry


@dataclass(frozen=True, slots=True)
class SegmentPerformance:
    """Performance metrics for a specific segment (overall, long, short, strategy)."""

    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    gross_pnl: float = 0.0
    net_pnl: float = 0.0
    average_winner: float = 0.0
    average_loser: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    largest_winner: float = 0.0
    largest_loser: float = 0.0
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    average_hold_time_seconds: float = 0.0
    average_r_multiple: float = 0.0
    average_win_percent: float = 0.0
    average_loss_percent: float = 0.0


@dataclass(frozen=True, slots=True)
class TradePerformance:
    """Complete institutional performance report."""

    overall: SegmentPerformance = field(default_factory=SegmentPerformance)
    max_drawdown: float = 0.0
    best_day: float = 0.0
    worst_day: float = 0.0
    daily_pnl: Mapping[date, float] = field(default_factory=dict)
    monthly_pnl: Mapping[str, float] = field(default_factory=dict)
    long_stats: SegmentPerformance = field(default_factory=SegmentPerformance)
    short_stats: SegmentPerformance = field(default_factory=SegmentPerformance)
    strategy_stats: Mapping[str, SegmentPerformance] = field(default_factory=dict)


class PerformanceAnalyzer:
    """Read-only analytics engine over Trade Journal entries."""

    def analyze(self, entries: Sequence[TradeJournalEntry]) -> TradePerformance:
        """Calculate complete performance metrics for a set of trades."""
        if not entries:
            return TradePerformance()

        # Sort entries by closing time to accurately calculate drawdown and consecutive metrics
        closed_entries = [e for e in entries if e.close_time is not None]
        closed_entries.sort(
            key=lambda x: x.close_time or datetime.min.replace(tzinfo=timezone.utc)
        )

        overall = self._analyze_segment(closed_entries)

        longs = [e for e in closed_entries if e.direction.lower() == "long"]
        shorts = [e for e in closed_entries if e.direction.lower() == "short"]

        long_stats = self._analyze_segment(longs)
        short_stats = self._analyze_segment(shorts)

        strategies = defaultdict(list)
        for e in closed_entries:
            strategies[e.strategy].append(e)

        strategy_stats = {
            strat: self._analyze_segment(trades) for strat, trades in strategies.items()
        }

        daily_pnl: dict[date, float] = defaultdict(float)
        monthly_pnl: dict[str, float] = defaultdict(float)

        for e in closed_entries:
            if not e.close_time:
                continue
            d = e.close_time.date()
            daily_pnl[d] += e.net_pnl
            month_key = f"{d.year}-{d.month:02d}"
            monthly_pnl[month_key] += e.net_pnl

        best_day = max(daily_pnl.values()) if daily_pnl else 0.0
        worst_day = min(daily_pnl.values()) if daily_pnl else 0.0

        # Max drawdown calculation
        max_drawdown = 0.0
        peak = 0.0
        cumulative_pnl = 0.0
        for e in closed_entries:
            cumulative_pnl += e.net_pnl
            if cumulative_pnl > peak:
                peak = cumulative_pnl
            drawdown = peak - cumulative_pnl
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        return TradePerformance(
            overall=overall,
            max_drawdown=max_drawdown,
            best_day=best_day,
            worst_day=worst_day,
            daily_pnl=dict(daily_pnl),
            monthly_pnl=dict(monthly_pnl),
            long_stats=long_stats,
            short_stats=short_stats,
            strategy_stats=strategy_stats,
        )

    def _analyze_segment(
        self, entries: Sequence[TradeJournalEntry]
    ) -> SegmentPerformance:
        """Calculate metrics for a specific subset of trades."""
        if not entries:
            return SegmentPerformance()

        total_trades = len(entries)
        wins = [e for e in entries if e.net_pnl > 0]
        losses = [e for e in entries if e.net_pnl <= 0]

        winning_trades = len(wins)
        losing_trades = len(losses)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0

        gross_pnl = sum(e.gross_pnl for e in entries)
        net_pnl = sum(e.net_pnl for e in entries)

        gross_profits = sum(e.gross_pnl for e in wins)
        gross_losses = abs(sum(e.gross_pnl for e in losses))

        average_winner = (
            sum(e.net_pnl for e in wins) / winning_trades if winning_trades > 0 else 0.0
        )
        average_loser = (
            sum(e.net_pnl for e in losses) / losing_trades if losing_trades > 0 else 0.0
        )

        profit_factor = (
            gross_profits / gross_losses
            if gross_losses > 0
            else (gross_profits if gross_profits > 0 else 0.0)
        )

        # Expectancy = (Win Rate * Avg Win) - (Loss Rate * Avg Loss)
        loss_rate = losing_trades / total_trades if total_trades > 0 else 0.0
        expectancy = (win_rate * average_winner) - (loss_rate * abs(average_loser))

        largest_winner = max((e.net_pnl for e in entries), default=0.0)
        largest_loser = min((e.net_pnl for e in entries), default=0.0)

        # Consecutive wins/losses
        max_cons_wins = 0
        max_cons_losses = 0
        current_cons_wins = 0
        current_cons_losses = 0

        for e in entries:
            if e.net_pnl > 0:
                current_cons_wins += 1
                current_cons_losses = 0
                max_cons_wins = max(max_cons_wins, current_cons_wins)
            else:
                current_cons_losses += 1
                current_cons_wins = 0
                max_cons_losses = max(max_cons_losses, current_cons_losses)

        average_hold_time_seconds = (
            sum(e.holding_time_seconds for e in entries) / total_trades
            if total_trades > 0
            else 0.0
        )

        # Simplified R-Multiple (assuming Risk was 1x Loser)
        # In a real system, entry would store initial risk. Here we approximate if not available.
        # Let's say R is approximated by the average loser for now, or just 0 if no losses.
        avg_r_multiple = 0.0
        if average_loser < 0:
            avg_r_multiple = average_winner / abs(average_loser)

        # Average win/loss percent (assuming trade size = entry_price * quantity)
        win_percents = []
        loss_percents = []
        for e in entries:
            basis = e.entry_price * e.quantity if e.entry_price and e.quantity else 1.0
            if basis <= 0:
                basis = 1.0
            pct = (e.net_pnl / basis) * 100.0
            if pct > 0:
                win_percents.append(pct)
            else:
                loss_percents.append(pct)

        average_win_percent = (
            sum(win_percents) / len(win_percents) if win_percents else 0.0
        )
        average_loss_percent = (
            sum(loss_percents) / len(loss_percents) if loss_percents else 0.0
        )

        return SegmentPerformance(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            gross_pnl=gross_pnl,
            net_pnl=net_pnl,
            average_winner=average_winner,
            average_loser=average_loser,
            profit_factor=profit_factor,
            expectancy=expectancy,
            largest_winner=largest_winner,
            largest_loser=largest_loser,
            consecutive_wins=max_cons_wins,
            consecutive_losses=max_cons_losses,
            average_hold_time_seconds=average_hold_time_seconds,
            average_r_multiple=avg_r_multiple,
            average_win_percent=average_win_percent,
            average_loss_percent=average_loss_percent,
        )
