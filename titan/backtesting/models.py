from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping

from titan.brokers.models import Exchange


class BacktestStatus(str, Enum):
    """Status of a backtest run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


@dataclass(frozen=True, slots=True)
class HistoricalBar:
    """A single historical OHLCV bar for backtesting.

    Attributes:
        timestamp: Candle timestamp (timezone-aware).
        open: Opening price.
        high: Highest traded price.
        low: Lowest traded price.
        close: Closing price.
        volume: Traded quantity.
        open_interest: Open interest (futures/options, optional).
    """

    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    open_interest: int | None = None


@dataclass(frozen=True, slots=True)
class OptionSnapshot:
    """A snapshot of option chain data at a point in time.

    Attributes:
        timestamp: When the snapshot was captured.
        symbol: Underlying symbol.
        expiry: Expiry date string.
        strike: Strike price.
        option_type: 'CE' or 'PE'.
        open: Opening price.
        high: High price.
        low: Low price.
        close: Close price.
        volume: Traded volume.
        open_interest: Open interest.
        iv: Implied volatility (optional).
    """

    timestamp: datetime
    symbol: str
    expiry: str
    strike: Decimal
    option_type: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    open_interest: int
    iv: float | None = None


@dataclass(frozen=True, slots=True)
class NewsSnapshot:
    """A news event at a point in time.

    Attributes:
        timestamp: When the news was published.
        headline: News headline.
        sentiment: Sentiment score (-1.0 to 1.0).
        source: News source.
        symbols: Related symbols.
    """

    timestamp: datetime
    headline: str
    sentiment: float = 0.0
    source: str = ""
    symbols: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class EventSnapshot:
    """A scheduled event at a point in time.

    Attributes:
        timestamp: When the event occurs.
        event_type: Type of event (earnings, economic, etc.).
        description: Event description.
        importance: Importance level (1-5).
        symbols: Related symbols.
    """

    timestamp: datetime
    event_type: str
    description: str = ""
    importance: int = 1
    symbols: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class BacktestBar:
    """A single bar of data fed through the backtest engine.

    Contains the primary OHLCV bar plus any associated snapshots
    (option chain, news, events) at this point in time.

    Attributes:
        bar: The primary OHLCV bar.
        symbol: Trading symbol.
        exchange: Exchange.
        option_snapshots: Option chain snapshots at this bar.
        news_snapshots: News events at this bar.
        event_snapshots: Scheduled events at this bar.
    """

    bar: HistoricalBar
    symbol: str
    exchange: Exchange
    option_snapshots: tuple[OptionSnapshot, ...] = field(default_factory=tuple)
    news_snapshots: tuple[NewsSnapshot, ...] = field(default_factory=tuple)
    event_snapshots: tuple[EventSnapshot, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class BacktestStatistics:
    """Trading statistics computed from a backtest run.

    Attributes:
        total_trades: Total number of completed trades.
        winning_trades: Number of profitable trades.
        losing_trades: Number of unprofitable trades.
        win_rate: Ratio of winning trades to total trades.
        loss_rate: Ratio of losing trades to total trades.
        profit_factor: Gross profit divided by gross loss.
        average_gain: Average profit per winning trade.
        average_loss: Average loss per losing trade.
        expectancy: Average expected P&L per trade.
        max_consecutive_wins: Maximum consecutive winning trades.
        max_consecutive_losses: Maximum consecutive losing trades.
        max_drawdown: Maximum peak-to-trough decline.
        recovery_factor: Net profit divided by max drawdown.
    """

    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    loss_rate: float = 0.0
    profit_factor: float = 0.0
    average_gain: Decimal = Decimal("0")
    average_loss: Decimal = Decimal("0")
    expectancy: Decimal = Decimal("0")
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    max_drawdown: Decimal = Decimal("0")
    recovery_factor: float = 0.0


@dataclass(frozen=True, slots=True)
class BacktestMetrics:
    """Performance metrics computed from a backtest run.

    Attributes:
        daily_return: Average daily return.
        monthly_return: Average monthly return.
        annualized_return: Annualized return.
        volatility: Annualized volatility.
        sharpe_ratio: Risk-adjusted return (placeholder ready).
        sortino_ratio: Downside risk-adjusted return (placeholder ready).
        calmar_ratio: Return over max drawdown.
        mar_ratio: Compound annual growth rate over max drawdown.
    """

    daily_return: float = 0.0
    monthly_return: float = 0.0
    annualized_return: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    mar_ratio: float = 0.0


@dataclass(frozen=True, slots=True)
class EquityPoint:
    """A single point on the equity curve.

    Attributes:
        timestamp: When this snapshot was taken.
        equity: Total account equity at this point.
        cash: Cash balance at this point.
        drawdown: Drawdown from peak at this point.
    """

    timestamp: datetime
    equity: Decimal
    cash: Decimal
    drawdown: Decimal = Decimal("0")


@dataclass(frozen=True, slots=True)
class BacktestReport:
    """Complete report generated after a backtest run.

    Attributes:
        backtest_id: Unique identifier for this backtest.
        symbol: Trading symbol tested.
        exchange: Exchange used.
        status: Final backtest status.
        bars_processed: Number of bars processed.
        start_time: Backtest start timestamp.
        end_time: Backtest end timestamp.
        duration_seconds: Wall-clock duration of the run.
        total_capital: Starting capital.
        final_equity: Ending account equity.
        total_pnl: Total profit or loss.
        total_return: Total return as a decimal ratio.
        statistics: Computed trading statistics.
        metrics: Computed performance metrics.
        equity_curve: Sequence of equity snapshots.
        pipeline_reports: Pipeline reports from each bar.
        warnings: Warnings generated during backtest.
        errors: Errors encountered during backtest.
    """

    backtest_id: str
    symbol: str
    exchange: str
    status: BacktestStatus
    bars_processed: int
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    total_capital: Decimal
    final_equity: Decimal
    total_pnl: Decimal
    total_return: Decimal
    statistics: BacktestStatistics
    metrics: BacktestMetrics
    equity_curve: tuple[EquityPoint, ...] = field(default_factory=tuple)
    pipeline_reports: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class BacktestExplanation:
    """Human-readable explanation of backtest results.

    Attributes:
        dataset: Summary of the dataset used.
        simulation: Summary of the simulation run.
        performance: Summary of performance metrics.
        risk: Summary of risk metrics.
        portfolio: Summary of portfolio state.
        summary: One-line overall summary.
    """

    dataset: str = ""
    simulation: str = ""
    performance: str = ""
    risk: str = ""
    portfolio: str = ""
    summary: str = ""
