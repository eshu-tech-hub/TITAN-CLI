from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping


class BrokerType(str, Enum):
    """Supported broker platforms.

    Values are used for factory registration and configuration lookup.
    """

    ANGEL_ONE = "angel_one"
    ZERODHA = "zerodha"
    DHAN = "dhan"
    UPSTOX = "upstox"
    INTERACTIVE_BROKERS = "interactive_brokers"
    ALPACA = "alpaca"
    BINANCE = "binance"
    PAPER = "paper"


class ConnectionStatus(str, Enum):
    """Current state of the broker connection."""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class OrderStatus(str, Enum):
    """Lifecycle status of a broker order."""

    PENDING = "pending"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class OrderSide(str, Enum):
    """Direction of an order."""

    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Pricing model for an order."""

    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    STOP_LOSS_LIMIT = "stop_loss_limit"


class ProductType(str, Enum):
    """Product category for an order or position."""

    DELIVERY = "delivery"
    INTRADAY = "intraday"
    MARGIN = "margin"
    OPTIONS = "options"
    FUTURES = "futures"


class Validity(str, Enum):
    """Time validity of an order."""

    DAY = "day"
    IOC = "ioc"
    GTC = "gtc"


class InstrumentType(str, Enum):
    """Type of financial instrument."""

    EQUITY = "equity"
    FUTURES = "futures"
    OPTIONS = "options"
    CURRENCY = "currency"
    COMMODITY = "commodity"
    ETF = "etf"
    INDEX = "index"


class Exchange(str, Enum):
    """Supported exchanges."""

    NSE = "nse"
    BSE = "bse"
    NFO = "nfo"
    CDS = "cds"
    MCX = "mcx"
    BSE_FO = "bse_fo"


@dataclass(frozen=True, slots=True)
class OrderRequest:
    """Request to place a new order.

    Attributes:
        symbol: Trading symbol recognised by the broker.
        exchange: Exchange to route the order to.
        side: Buy or sell.
        order_type: Market, limit, or stop-loss.
        quantity: Number of units or contracts.
        product: Product type (delivery, intraday, margin, etc.).
        validity: Time validity of the order.
        price: Limit price (required for LIMIT orders).
        trigger_price: Trigger price for stop-loss orders.
        disclose_quantity: Quantity to disclose on the order book.
        tag: Client-provided identifier for reconciliation.
        broker_params: Broker-specific extension parameters.
    """

    symbol: str
    exchange: Exchange
    side: OrderSide
    order_type: OrderType
    quantity: int
    product: ProductType = ProductType.DELIVERY
    validity: Validity = Validity.DAY
    price: Decimal | None = None
    trigger_price: Decimal | None = None
    disclose_quantity: int = 0
    tag: str = ""
    broker_params: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class OrderResponse:
    """Response returned after placing an order.

    Attributes:
        broker_order_id: Broker-assigned order identifier.
        status: Current order status.
        filled_quantity: Quantity filled so far.
        pending_quantity: Quantity still pending.
        average_price: Average fill price.
        message: Broker response message.
        metadata: Broker-specific metadata.
        timestamp: When the response was generated.
    """

    broker_order_id: str
    status: OrderStatus
    filled_quantity: int = 0
    pending_quantity: int = 0
    average_price: Decimal | None = None
    message: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True, slots=True)
class ModifyOrderRequest:
    """Request to modify an existing open order.

    Attributes:
        broker_order_id: Order to modify.
        quantity: New quantity (0 = no change).
        price: New limit price (None = no change).
        trigger_price: New trigger price (None = no change).
        validity: New validity.
        disclose_quantity: New disclosed quantity.
    """

    broker_order_id: str
    quantity: int = 0
    price: Decimal | None = None
    trigger_price: Decimal | None = None
    validity: Validity | None = None
    disclose_quantity: int | None = None


@dataclass(frozen=True, slots=True)
class CancelOrderRequest:
    """Request to cancel an existing open order.

    Attributes:
        broker_order_id: Order to cancel.
        reason: Optional cancellation reason.
    """

    broker_order_id: str
    reason: str = ""


@dataclass(frozen=True, slots=True)
class Order:
    """Full representation of an order, past or present.

    Attributes:
        broker_order_id: Broker-assigned order identifier.
        symbol: Trading symbol.
        exchange: Exchange the order was routed to.
        side: Buy or sell.
        order_type: Market, limit, or stop-loss.
        product: Product type.
        status: Current lifecycle status.
        quantity: Original order quantity.
        filled_quantity: Quantity filled.
        pending_quantity: Quantity still pending.
        average_price: Average fill price.
        price: Limit price (if applicable).
        trigger_price: Stop-loss trigger (if applicable).
        validity: Time validity.
        tag: Client-provided identifier.
        rejected_reason: Reason for rejection (if rejected).
        placed_at: When the order was placed.
        filled_at: When the order was fully filled.
        broker_params: Broker-specific metadata.
    """

    broker_order_id: str
    symbol: str
    exchange: Exchange
    side: OrderSide
    order_type: OrderType
    product: ProductType
    status: OrderStatus
    quantity: int
    filled_quantity: int = 0
    pending_quantity: int = 0
    average_price: Decimal | None = None
    price: Decimal | None = None
    trigger_price: Decimal | None = None
    validity: Validity = Validity.DAY
    tag: str = ""
    rejected_reason: str = ""
    placed_at: datetime | None = None
    filled_at: datetime | None = None
    broker_params: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Position:
    """An open position held in the portfolio.

    Attributes:
        symbol: Trading symbol.
        exchange: Exchange the position is on.
        instrument_type: Type of instrument.
        product: Product type.
        quantity: Net quantity (positive = long, negative = short).
        buy_quantity: Total quantity bought.
        sell_quantity: Total quantity sold.
        buy_price: Average buy price.
        sell_price: Average sell price.
        current_price: Last traded price.
        pnl: Unrealised profit or loss.
        realised_pnl: Realised profit or loss.
        multiplier: Contract multiplier (for futures/options).
        broker_params: Broker-specific metadata.
    """

    symbol: str
    exchange: Exchange
    instrument_type: InstrumentType
    product: ProductType
    quantity: int
    buy_quantity: int = 0
    sell_quantity: int = 0
    buy_price: Decimal | None = None
    sell_price: Decimal | None = None
    current_price: Decimal | None = None
    pnl: Decimal | None = None
    realised_pnl: Decimal | None = None
    multiplier: int = 1
    broker_params: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Holding:
    """A security held in the demat account.

    Attributes:
        symbol: Trading symbol.
        exchange: Exchange.
        instrument_type: Type of instrument.
        quantity: Total quantity held.
        available_quantity: Quantity available for trading.
        buy_price: Average buy price.
        current_price: Last traded price.
        pnl: Unrealised profit or loss.
    """

    symbol: str
    exchange: Exchange
    instrument_type: InstrumentType
    quantity: int
    available_quantity: int = 0
    buy_price: Decimal | None = None
    current_price: Decimal | None = None
    pnl: Decimal | None = None


@dataclass(frozen=True, slots=True)
class Trade:
    """An executed trade (fill).

    Attributes:
        trade_id: Broker-assigned trade identifier.
        broker_order_id: Parent order identifier.
        symbol: Trading symbol.
        exchange: Exchange.
        side: Buy or sell.
        quantity: Filled quantity for this trade.
        price: Fill price.
        product: Product type.
        trade_time: When the trade was executed.
    """

    trade_id: str
    broker_order_id: str
    symbol: str
    exchange: Exchange
    side: OrderSide
    quantity: int
    price: Decimal
    product: ProductType = ProductType.DELIVERY
    trade_time: datetime | None = None


@dataclass(frozen=True, slots=True)
class Quote:
    """Real-time or snapshot quote for a single instrument.

    Attributes:
        symbol: Trading symbol.
        exchange: Exchange.
        last_price: Last traded price.
        bid: Highest bid price.
        ask: Lowest ask price.
        bid_quantity: Quantity available at the bid.
        ask_quantity: Quantity available at the ask.
        open: Today's open price.
        high: Today's high price.
        low: Today's low price.
        close: Yesterday's close price.
        volume: Today's traded volume.
        oi: Open interest (futures/options).
        change: Price change from previous close.
        change_percent: Percentage change from previous close.
        timestamp: When the quote was captured.
    """

    symbol: str
    exchange: Exchange
    last_price: Decimal
    bid: Decimal | None = None
    ask: Decimal | None = None
    bid_quantity: int = 0
    ask_quantity: int = 0
    open: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None
    close: Decimal | None = None
    volume: int = 0
    oi: int | None = None
    change: Decimal | None = None
    change_percent: float = 0.0
    timestamp: datetime | None = None


@dataclass(frozen=True, slots=True)
class MarketDepthLevel:
    """Single level in the order book (bid or ask side).

    Attributes:
        price: Price level.
        quantity: Quantity available at this level.
        orders: Number of orders at this level.
    """

    price: Decimal
    quantity: int
    orders: int = 0


@dataclass(frozen=True, slots=True)
class MarketDepth:
    """Order book depth snapshot.

    Attributes:
        symbol: Trading symbol.
        exchange: Exchange.
        bids: Bid levels (sorted descending by price).
        asks: Ask levels (sorted ascending by price).
        timestamp: When the snapshot was captured.
    """

    symbol: str
    exchange: Exchange
    bids: tuple[MarketDepthLevel, ...] = field(default_factory=tuple)
    asks: tuple[MarketDepthLevel, ...] = field(default_factory=tuple)
    timestamp: datetime | None = None


@dataclass(frozen=True, slots=True)
class MarginInfo:
    """Margin details for the account.

    Attributes:
        total_margin: Total margin available.
        used_margin: Margin currently in use.
        available_margin: Margin available for new trades.
        delivery_margin: Margin blocked for delivery positions.
        span_margin: SPAN margin (futures/options).
        exposure_margin: Additional exposure margin.
        broker_params: Broker-specific margin details.
    """

    total_margin: Decimal | None = None
    used_margin: Decimal | None = None
    available_margin: Decimal | None = None
    delivery_margin: Decimal | None = None
    span_margin: Decimal | None = None
    exposure_margin: Decimal | None = None
    broker_params: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FundsInfo:
    """Funds summary for the account.

    Attributes:
        available_cash: Cash available for withdrawals and trading.
        used_cash: Cash already allocated to orders/positions.
        payin: Funds pay-in pending settlement.
        payout: Funds payout pending settlement.
        realised_pnl: Realised profit or loss.
        unrealised_pnl: Unrealised profit or loss.
        broker_params: Broker-specific fund details.
    """

    available_cash: Decimal | None = None
    used_cash: Decimal | None = None
    payin: Decimal | None = None
    payout: Decimal | None = None
    realised_pnl: Decimal | None = None
    unrealised_pnl: Decimal | None = None
    broker_params: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AccountProfile:
    """Profile information for the authenticated account.

    Attributes:
        account_id: Unique account identifier.
        name: Account holder name.
        email: Registered email address.
        phone: Registered phone number.
        broker: Broker platform name.
        account_type: Type of account (individual, corporate, etc.).
        enabled_exchanges: Exchanges the account can trade on.
        broker_params: Broker-specific profile details.
    """

    account_id: str = ""
    name: str = ""
    email: str = ""
    phone: str = ""
    broker: str = ""
    account_type: str = ""
    enabled_exchanges: tuple[Exchange, ...] = field(default_factory=tuple)
    broker_params: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Candle:
    """OHLCV data point for historical data.

    Attributes:
        datetime: Candle timestamp.
        open: Open price.
        high: High price.
        low: Low price.
        close: Close price.
        volume: Traded volume.
        oi: Open interest (futures/options).
    """

    datetime: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    oi: int | None = None
