from dataclasses import dataclass, field
from datetime import datetime

from titan.portfolio.models import (
    DrawdownAnalysis,
    PortfolioPerformance,
    PortfolioSnapshot,
)
from titan.trading.journal import TradeLifecycleEvent


@dataclass(frozen=True, slots=True)
class PortfolioReplaySnapshot:
    """A reconstructed point-in-time snapshot of the portfolio."""

    timestamp: datetime
    snapshot: PortfolioSnapshot
    drawdown: DrawdownAnalysis
    performance: PortfolioPerformance


@dataclass(frozen=True, slots=True)
class PortfolioReplayTimeline:
    """Chronological sequence of lifecycle events that occurred up to the snapshot."""

    events: tuple[TradeLifecycleEvent, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class PortfolioReplayResult:
    """The aggregate result of a portfolio historical replay."""

    snapshot: PortfolioReplaySnapshot
    timeline: PortfolioReplayTimeline
