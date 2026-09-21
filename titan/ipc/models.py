from datetime import datetime

from pydantic import BaseModel, Field


class PaperSessionPayload(BaseModel):
    running: bool
    connected: bool
    stream_connected: bool = False
    stream_symbols: list[str] = Field(default_factory=list)
    session_uptime_seconds: float
    start_time: datetime | None

class PaperAccountPayload(BaseModel):
    initial_cash: float
    cash_balance: float
    buying_power: float
    used_margin: float
    payout: float

class PaperPortfolioPayload(BaseModel):
    portfolio_value: float
    exposure: float
    open_positions_count: int
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float
    daily_pnl: float
    drawdown: float

class PaperPerformancePayload(BaseModel):
    closed_trades_count: int
    total_orders_count: int
    filled_orders_count: int
    win_rate: float
    loss_rate: float
    profit_factor: float
    max_drawdown: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    expectancy: float

class PaperPositionPayload(BaseModel):
    symbol: str
    quantity: int
    average_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float

class PaperOrderPayload(BaseModel):
    order_id: str
    symbol: str
    side: str
    type: str
    quantity: int
    filled_quantity: int
    status: str
    price: float
    placed_at: datetime | None

class PaperTradePayload(BaseModel):
    symbol: str
    side: str
    quantity: int
    price: float
    pnl: float
    timestamp: datetime | None

class PaperStatusResponse(BaseModel):
    status: str
    session: PaperSessionPayload
    account: PaperAccountPayload
    portfolio: PaperPortfolioPayload
    performance: PaperPerformancePayload
    positions: list[PaperPositionPayload]
    orders: list[PaperOrderPayload]
    trades: list[PaperTradePayload]
