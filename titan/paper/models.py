from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from titan.brokers.models import (
    Exchange,
    OrderSide,
    OrderStatus,
    OrderType,
    ProductType,
)


@dataclass(frozen=True, slots=True)
class PaperFill:
    """A single simulated fill event.

    Attributes:
        fill_id: Unique identifier for this fill.
        order_id: Internal order ID this fill belongs to.
        broker_order_id: Broker-assigned order identifier.
        symbol: Trading symbol.
        exchange: Exchange.
        side: Buy or sell.
        quantity: Quantity filled in this event.
        price: Fill price.
        product: Product type.
        commission: Simulated commission charged.
        slippage: Price slippage applied.
        latency_ms: Simulated execution latency.
        timestamp: When the fill occurred.
    """

    fill_id: str
    order_id: str
    broker_order_id: str
    symbol: str
    exchange: Exchange
    side: OrderSide
    quantity: int
    price: Decimal
    product: ProductType = ProductType.DELIVERY
    commission: Decimal = Decimal(0)
    slippage: Decimal = Decimal(0)
    latency_ms: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class PaperOrder:
    """Internal representation of a paper order with full lifecycle.

    Attributes:
        order_id: Internal unique identifier for this order.
        broker_order_id: Broker-assigned order identifier.
        symbol: Trading symbol.
        exchange: Exchange.
        side: Buy or sell.
        order_type: Market, limit, or stop-loss.
        quantity: Original order quantity.
        filled_quantity: Total quantity filled.
        pending_quantity: Quantity still pending.
        price: Limit price (if applicable).
        trigger_price: Stop-loss trigger (if applicable).
        product: Product type.
        status: Current order status.
        fills: Tuple of fills applied to this order.
        tag: Client-provided identifier.
        rejected_reason: Reason for rejection (if rejected).
        placed_at: When the order was placed.
        filled_at: When the order was fully filled.
        metadata: Additional order metadata.
        created_at: When this record was created.
    """

    order_id: str
    broker_order_id: str
    symbol: str
    exchange: Exchange
    side: OrderSide
    order_type: OrderType
    quantity: int
    filled_quantity: int = 0
    pending_quantity: int = 0
    price: Decimal | None = None
    trigger_price: Decimal | None = None
    product: ProductType = ProductType.DELIVERY
    status: OrderStatus = OrderStatus.PENDING
    fills: tuple[PaperFill, ...] = field(default_factory=tuple)
    tag: str = ""
    rejected_reason: str = ""
    placed_at: datetime | None = None
    filled_at: datetime | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class PaperPosition:
    """Internal representation of an open position.

    Attributes:
        symbol: Trading symbol.
        exchange: Exchange.
        quantity: Net quantity (positive = long, negative = short).
        average_price: Average entry price.
        buy_quantity: Total quantity bought.
        sell_quantity: Total quantity sold.
        buy_value: Total value of buys.
        sell_value: Total value of sells.
        realized_pnl: Realized profit or loss.
        unrealized_pnl: Unrealized profit or loss.
        current_price: Last known price.
        mfe: Maximum favorable excursion.
        mae: Maximum adverse excursion.
        opened_at: When the position was first opened.
        updated_at: When the position was last updated.
    """

    symbol: str
    exchange: Exchange
    quantity: int = 0
    average_price: Decimal | None = None
    buy_quantity: int = 0
    sell_quantity: int = 0
    buy_value: Decimal = Decimal(0)
    sell_value: Decimal = Decimal(0)
    realized_pnl: Decimal = Decimal(0)
    unrealized_pnl: Decimal = Decimal(0)
    current_price: Decimal | None = None
    mfe: Decimal = Decimal(0)
    mae: Decimal = Decimal(0)
    opened_at: datetime | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class PaperPortfolioState:
    """Snapshot of the paper portfolio at a point in time.

    Attributes:
        cash: Available cash balance.
        equity: Total equity (cash + position value).
        buying_power: Available buying power.
        margin_used: Margin currently in use.
        daily_pnl: Today's profit or loss.
        total_return: Total return since inception.
        total_pnl: Total profit or loss.
        drawdown: Current drawdown from peak.
        exposure: Current portfolio exposure.
        position_count: Number of open positions.
        timestamp: When the snapshot was captured.
    """

    cash: Decimal = Decimal(0)
    equity: Decimal = Decimal(0)
    buying_power: Decimal = Decimal(0)
    margin_used: Decimal = Decimal(0)
    daily_pnl: Decimal = Decimal(0)
    total_return: Decimal = Decimal(0)
    total_pnl: Decimal = Decimal(0)
    drawdown: Decimal = Decimal(0)
    exposure: Decimal = Decimal(0)
    position_count: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class PaperPerformanceMetrics:
    """Performance metrics computed from paper trading history.

    Attributes:
        total_trades: Total number of completed trades.
        winning_trades: Number of profitable trades.
        losing_trades: Number of unprofitable trades.
        win_rate: Ratio of winning trades to total trades.
        loss_rate: Ratio of losing trades to total trades.
        profit_factor: Gross profit divided by gross loss.
        expectancy: Average expected P&L per trade.
        avg_winner: Average profit per winning trade.
        avg_loser: Average loss per losing trade.
        avg_holding_time_seconds: Average holding time in seconds.
        max_drawdown: Maximum peak-to-trough decline.
        sharpe_ratio: Sharpe ratio (placeholder).
        sortino_ratio: Sortino ratio (placeholder).
    """

    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    loss_rate: float = 0.0
    profit_factor: float = 0.0
    expectancy: Decimal = Decimal(0)
    avg_winner: Decimal = Decimal(0)
    avg_loser: Decimal = Decimal(0)
    avg_holding_time_seconds: float = 0.0
    max_drawdown: Decimal = Decimal(0)
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
