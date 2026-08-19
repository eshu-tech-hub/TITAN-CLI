from datetime import UTC, datetime

from titan.portfolio.analytics import PortfolioAnalytics
from titan.portfolio.models import ExistingPortfolio, OpenPosition
from titan.portfolio.replay_models import (
    PortfolioReplayResult,
    PortfolioReplaySnapshot,
    PortfolioReplayTimeline,
)
from titan.trading.journal import TradeJournal


class PortfolioReplayService:
    """Service for reconstructing historical portfolio states and generating point-in-time analytics.

    Operates strictly in read-only mode by consuming TradeJournal entries.
    """

    def __init__(
        self,
        trade_journal: TradeJournal,
        analytics_engine: PortfolioAnalytics | None = None,
    ) -> None:
        self.trade_journal = trade_journal
        self.analytics = analytics_engine or PortfolioAnalytics()

    def replay_to_timestamp(
        self, target_time: datetime, starting_capital: float = 100000.0
    ) -> PortfolioReplayResult:
        """Reconstruct the portfolio exactly as it was at the given timestamp."""
        all_entries = self.trade_journal.repository.list(
            page=1, page_size=10000
        )  # Get all for replay

        # Filter events that occurred up to target_time
        # An entry is open if it has open_time <= target_time and (no close_time or close_time > target_time)
        open_positions = []
        historical_entries = []
        timeline_events = []

        capital = starting_capital

        for entry in sorted(
            all_entries,
            key=lambda x: x.open_time or datetime.min.replace(tzinfo=UTC),
        ):
            if not entry.open_time or entry.open_time > target_time:
                continue

            # It was opened before/at target time. So it's part of history.
            historical_entries.append(entry)
            for event in entry.lifecycle_events:
                if event.timestamp <= target_time:
                    timeline_events.append(event)

            # Check if it was closed before/at target time
            if entry.close_time and entry.close_time <= target_time:
                # Trade is closed, add its net pnl to capital
                capital += entry.net_pnl
            else:
                # Trade is currently open at target_time
                # We simulate current price as entry price since we don't have historical tick data in this context
                pos = OpenPosition(
                    symbol=entry.symbol,
                    instrument_type="Unknown",
                    direction=entry.direction,
                    quantity=entry.quantity,
                    entry_price=entry.entry_price,
                    current_price=entry.entry_price,  # Replay approximation
                    market_value=entry.entry_price * entry.quantity,
                    pnl=0.0,  # Unrealized PnL approximation
                    sector="",
                )
                open_positions.append(pos)

        # Reconstruct portfolio
        portfolio = ExistingPortfolio(
            total_capital=capital,
            cash_reserve=capital - sum(abs(p.market_value) for p in open_positions),
            positions=tuple(open_positions),
        )

        # Generate Analytics for that point in time
        snapshot = self.analytics.generate_snapshot(portfolio)
        drawdown = self.analytics.analyze_drawdown(
            historical_entries, starting_capital=starting_capital
        )
        performance = self.analytics.analyze_performance(historical_entries)

        # Sort timeline chronologically
        timeline_events.sort(key=lambda x: x.timestamp)

        replay_snap = PortfolioReplaySnapshot(
            timestamp=target_time,
            snapshot=snapshot,
            drawdown=drawdown,
            performance=performance,
        )

        timeline = PortfolioReplayTimeline(events=tuple(timeline_events))

        return PortfolioReplayResult(snapshot=replay_snap, timeline=timeline)

    def replay_to_trade(
        self, trade_id: str, starting_capital: float = 100000.0
    ) -> PortfolioReplayResult | None:
        """Reconstruct the portfolio state exactly after a specific trade closed."""
        entry = self.trade_journal.repository.get(trade_id)
        if not entry:
            return None

        target_time = entry.close_time or entry.open_time
        if not target_time:
            # Fallback to first lifecycle event
            if entry.lifecycle_events:
                target_time = entry.lifecycle_events[-1].timestamp
            else:
                return None

        return self.replay_to_timestamp(target_time, starting_capital)
