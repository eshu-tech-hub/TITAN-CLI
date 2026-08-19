"""Pure mapping functions between SmartAPI JSON payloads and TITAN models.

NO SmartAPI objects may leave this layer.
All broker responses are converted to TITAN domain models here.
"""

from collections.abc import Mapping
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from titan.brokers.models import (
    AccountProfile,
    Candle,
    Exchange,
    FundsInfo,
    Holding,
    InstrumentType,
    MarginInfo,
    MarketDepth,
    MarketDepthLevel,
    Order,
    OrderRequest,
    OrderResponse,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    ProductType,
    Quote,
    Trade,
    Validity,
)

# ---------------------------------------------------------------------------
# SmartAPI string constants
# ---------------------------------------------------------------------------

_EXCHANGE_MAP: dict[str, Exchange] = {
    "NSE": Exchange.NSE,
    "BSE": Exchange.BSE,
    "NFO": Exchange.NFO,
    "CDS": Exchange.CDS,
    "MCX": Exchange.MCX,
    "BSE_FO": Exchange.BSE_FO,
}

_SIDE_MAP: dict[str, OrderSide] = {
    "BUY": OrderSide.BUY,
    "SELL": OrderSide.SELL,
}

_ORDER_TYPE_MAP: dict[str, OrderType] = {
    "MARKET": OrderType.MARKET,
    "LIMIT": OrderType.LIMIT,
    "STOPLOSS": OrderType.STOP_LOSS,
    "STOPLOSS_LIMIT": OrderType.STOP_LOSS_LIMIT,
}

_PRODUCT_MAP: dict[str, ProductType] = {
    "DELIVERY": ProductType.DELIVERY,
    "INTRADAY": ProductType.INTRADAY,
    "MARGIN": ProductType.MARGIN,
    "OPTIONS": ProductType.OPTIONS,
    "FUTURES": ProductType.FUTURES,
}

_VALIDITY_MAP: dict[str, Validity] = {
    "DAY": Validity.DAY,
    "IOC": Validity.IOC,
    "GTC": Validity.GTC,
}

_ORDER_STATUS_MAP: dict[str, OrderStatus] = {
    "PENDING": OrderStatus.PENDING,
    "OPEN": OrderStatus.OPEN,
    "PARTIALLY_FILLED": OrderStatus.PARTIALLY_FILLED,
    "FILLED": OrderStatus.FILLED,
    "CANCELLED": OrderStatus.CANCELLED,
    "CANCELED": OrderStatus.CANCELLED,
    "REJECTED": OrderStatus.REJECTED,
    "EXPIRED": OrderStatus.EXPIRED,
}

_INSTRUMENT_TYPE_MAP: dict[str, InstrumentType] = {
    "EQ": InstrumentType.EQUITY,
    "FUT": InstrumentType.FUTURES,
    "OPT": InstrumentType.OPTIONS,
    "CE": InstrumentType.OPTIONS,
    "PE": InstrumentType.OPTIONS,
    "FUTCUR": InstrumentType.CURRENCY,
    "OPTcur": InstrumentType.CURRENCY,
    "COM": InstrumentType.COMMODITY,
    "ETF": InstrumentType.ETF,
    "INDICES": InstrumentType.INDEX,
}

# ---------------------------------------------------------------------------
# Reverse maps (TITAN → SmartAPI)
# ---------------------------------------------------------------------------

_EXCHANGE_REVERSE: dict[Exchange, str] = {v: k for k, v in _EXCHANGE_MAP.items()}
_SIDE_REVERSE: dict[OrderSide, str] = {v: k for k, v in _SIDE_MAP.items()}
_ORDER_TYPE_REVERSE: dict[OrderType, str] = {
    OrderType.STOP_LOSS: "STOPLOSS",
    OrderType.STOP_LOSS_LIMIT: "STOPLOSS_LIMIT",
    OrderType.MARKET: "MARKET",
    OrderType.LIMIT: "LIMIT",
}
_PRODUCT_REVERSE: dict[ProductType, str] = {v: k for k, v in _PRODUCT_MAP.items()}
_VALIDITY_REVERSE: dict[Validity, str] = {v: k for k, v in _VALIDITY_MAP.items()}

# ---------------------------------------------------------------------------
# SmartAPI JSON → TITAN models
# ---------------------------------------------------------------------------


def _safe_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (ValueError, TypeError):
        return None


def _safe_int(value: Any) -> int:
    if value is None:
        return 0
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _safe_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def to_exchange(value: str) -> Exchange:
    return _EXCHANGE_MAP.get(value.upper(), Exchange.NSE)


def to_order_side(value: str) -> OrderSide:
    return _SIDE_MAP.get(value.upper(), OrderSide.BUY)


def to_order_type(value: str) -> OrderType:
    return _ORDER_TYPE_MAP.get(value.upper(), OrderType.MARKET)


def to_product_type(value: str) -> ProductType:
    return _PRODUCT_MAP.get(value.upper(), ProductType.DELIVERY)


def to_validity(value: str) -> Validity:
    return _VALIDITY_MAP.get(value.upper(), Validity.DAY)


def to_order_status(value: str) -> OrderStatus:
    return _ORDER_STATUS_MAP.get(value.upper(), OrderStatus.PENDING)


def to_instrument_type(value: str) -> InstrumentType:
    return _INSTRUMENT_TYPE_MAP.get(value.upper(), InstrumentType.EQUITY)


def quote_from_smartapi(data: Mapping[str, Any]) -> Quote:
    """Convert a SmartAPI quote response to a TITAN Quote."""
    return Quote(
        symbol=_safe_str(data.get("symbol") or data.get("tradingsymbol")),
        exchange=to_exchange(_safe_str(data.get("exchange"))),
        last_price=_safe_decimal(data.get("ltp") or data.get("last_price"))
        or Decimal(0),
        bid=_safe_decimal(data.get("bid")),
        ask=_safe_decimal(data.get("ask")),
        bid_quantity=_safe_int(data.get("bid_qty") or data.get("bidquantity")),
        ask_quantity=_safe_int(data.get("ask_qty") or data.get("askquantity")),
        open=_safe_decimal(data.get("open")),
        high=_safe_decimal(data.get("high")),
        low=_safe_decimal(data.get("low")),
        close=_safe_decimal(data.get("close")),
        volume=_safe_int(data.get("volume") or data.get("volumetradedtoday")),
        oi=_safe_int(data.get("open_interest") or data.get("oi")),
        change=_safe_decimal(data.get("change")),
        change_percent=float(_safe_decimal(data.get("change_percent")) or 0),
        timestamp=_safe_datetime(data.get("timestamp")),
    )


def candle_from_smartapi(data: Mapping[str, Any]) -> Candle:
    """Convert a SmartAPI candle response to a TITAN Candle."""
    return Candle(
        datetime=_safe_datetime(data.get("timestamp") or data.get("datetime"))
        or datetime.now(UTC),
        open=_safe_decimal(data.get("open")) or Decimal(0),
        high=_safe_decimal(data.get("high")) or Decimal(0),
        low=_safe_decimal(data.get("low")) or Decimal(0),
        close=_safe_decimal(data.get("close")) or Decimal(0),
        volume=_safe_int(data.get("volume") or data.get("volumetradedtoday")),
        oi=_safe_int(data.get("open_interest") or data.get("oi")),
    )


def order_response_from_smartapi(data: Mapping[str, Any]) -> OrderResponse:
    """Convert a SmartAPI order response to a TITAN OrderResponse."""
    status = to_order_status(_safe_str(data.get("status")))
    return OrderResponse(
        broker_order_id=_safe_str(
            data.get("orderid") or data.get("order_id") or data.get("omsorderid")
        ),
        status=status,
        filled_quantity=_safe_int(data.get("filledqty") or data.get("filled_quantity")),
        pending_quantity=_safe_int(
            data.get("pendingqty") or data.get("pending_quantity")
        ),
        average_price=_safe_decimal(
            data.get("averageprice") or data.get("average_price")
        ),
        message=_safe_str(data.get("message") or data.get("text")),
    )


def order_from_smartapi(data: Mapping[str, Any]) -> Order:
    """Convert a SmartAPI order response to a TITAN Order."""
    return Order(
        broker_order_id=_safe_str(data.get("orderid") or data.get("order_id")),
        symbol=_safe_str(data.get("symbol") or data.get("tradingsymbol")),
        exchange=to_exchange(_safe_str(data.get("exchange"))),
        side=to_order_side(_safe_str(data.get("transactiontype") or data.get("side"))),
        order_type=to_order_type(
            _safe_str(data.get("ordertype") or data.get("order_type"))
        ),
        product=to_product_type(
            _safe_str(data.get("producttype") or data.get("product"))
        ),
        status=to_order_status(_safe_str(data.get("status"))),
        quantity=_safe_int(data.get("quantity") or data.get("qty")),
        filled_quantity=_safe_int(data.get("filledqty") or data.get("filled_quantity")),
        pending_quantity=_safe_int(
            data.get("pendingqty") or data.get("pending_quantity")
        ),
        average_price=_safe_decimal(
            data.get("averageprice") or data.get("average_price")
        ),
        price=_safe_decimal(data.get("price")),
        trigger_price=_safe_decimal(
            data.get("triggerprice") or data.get("trigger_price")
        ),
        validity=to_validity(_safe_str(data.get("validity"))),
        tag=_safe_str(data.get("tag")),
        rejected_reason=_safe_str(
            data.get("rejectionreason") or data.get("rejection_reason")
        ),
        placed_at=_safe_datetime(
            data.get("placedat") or data.get("placed_at") or data.get("ordertimestamp")
        ),
        filled_at=_safe_datetime(data.get("filledat") or data.get("filled_at")),
    )


def position_from_smartapi(data: Mapping[str, Any]) -> Position:
    """Convert a SmartAPI position response to a TITAN Position."""
    return Position(
        symbol=_safe_str(data.get("symbol") or data.get("tradingsymbol")),
        exchange=to_exchange(_safe_str(data.get("exchange"))),
        instrument_type=to_instrument_type(
            _safe_str(data.get("instrumenttype") or data.get("instrument_type"))
        ),
        product=to_product_type(
            _safe_str(data.get("producttype") or data.get("product"))
        ),
        quantity=_safe_int(
            data.get("netqty") or data.get("quantity") or data.get("netquantity")
        ),
        buy_quantity=_safe_int(
            data.get("buyqty") or data.get("buy_quantity") or data.get("buyquantity")
        ),
        sell_quantity=_safe_int(
            data.get("sellqty") or data.get("sell_quantity") or data.get("sellquantity")
        ),
        buy_price=_safe_decimal(
            data.get("buyavgprice") or data.get("buy_price") or data.get("buyavg")
        ),
        sell_price=_safe_decimal(
            data.get("sellavgprice") or data.get("sell_price") or data.get("sellavg")
        ),
        current_price=_safe_decimal(data.get("ltp") or data.get("last_price")),
        pnl=_safe_decimal(
            data.get("pnl") or data.get("unrealised") or data.get("unrealisedpnl")
        ),
        realised_pnl=_safe_decimal(data.get("realised") or data.get("realisedpnl")),
        multiplier=_safe_int(data.get("multiplier")),
    )


def holding_from_smartapi(data: Mapping[str, Any]) -> Holding:
    """Convert a SmartAPI holding response to a TITAN Holding."""
    return Holding(
        symbol=_safe_str(data.get("symbol") or data.get("tradingsymbol")),
        exchange=to_exchange(_safe_str(data.get("exchange"))),
        instrument_type=to_instrument_type(
            _safe_str(data.get("instrumenttype") or data.get("instrument_type"))
        ),
        quantity=_safe_int(data.get("quantity") or data.get("totalqty")),
        available_quantity=_safe_int(
            data.get("availablequantity") or data.get("availableqty")
        ),
        buy_price=_safe_decimal(data.get("buyavgprice") or data.get("averageprice")),
        current_price=_safe_decimal(data.get("ltp") or data.get("last_price")),
        pnl=_safe_decimal(data.get("pnl") or data.get("unrealisedpnl")),
    )


def trade_from_smartapi(data: Mapping[str, Any]) -> Trade:
    """Convert a SmartAPI trade response to a TITAN Trade."""
    return Trade(
        trade_id=_safe_str(
            data.get("tradeid") or data.get("trade_id") or data.get("fillid")
        ),
        broker_order_id=_safe_str(data.get("orderid") or data.get("order_id")),
        symbol=_safe_str(data.get("symbol") or data.get("tradingsymbol")),
        exchange=to_exchange(_safe_str(data.get("exchange"))),
        side=to_order_side(_safe_str(data.get("transactiontype") or data.get("side"))),
        quantity=_safe_int(
            data.get("filledqty") or data.get("quantity") or data.get("fillqty")
        ),
        price=_safe_decimal(
            data.get("fillprice") or data.get("price") or data.get("tradeprice")
        )
        or Decimal(0),
        product=to_product_type(
            _safe_str(data.get("producttype") or data.get("product"))
        ),
        trade_time=_safe_datetime(
            data.get("filltime") or data.get("trade_time") or data.get("tradetime")
        ),
    )


def market_depth_from_smartapi(data: Mapping[str, Any]) -> MarketDepth:
    """Convert a SmartAPI market depth response to a TITAN MarketDepth."""
    bids_raw = data.get("bids") or data.get("Bids") or []
    asks_raw = data.get("asks") or data.get("Asks") or []

    bids = tuple(
        MarketDepthLevel(
            price=_safe_decimal(b.get("price") or b.get("bidprice")) or Decimal(0),
            quantity=_safe_int(b.get("quantity") or b.get("bidqty")),
            orders=_safe_int(b.get("orders") or b.get("numorders")),
        )
        for b in bids_raw
    )
    asks = tuple(
        MarketDepthLevel(
            price=_safe_decimal(a.get("price") or a.get("askprice")) or Decimal(0),
            quantity=_safe_int(a.get("quantity") or a.get("askqty")),
            orders=_safe_int(a.get("orders") or a.get("numorders")),
        )
        for a in asks_raw
    )

    return MarketDepth(
        symbol=_safe_str(data.get("symbol") or data.get("tradingsymbol")),
        exchange=to_exchange(_safe_str(data.get("exchange"))),
        bids=bids,
        asks=asks,
        timestamp=_safe_datetime(data.get("timestamp")),
    )


def funds_from_smartapi(data: Mapping[str, Any]) -> FundsInfo:
    """Convert a SmartAPI funds response to a TITAN FundsInfo."""
    return FundsInfo(
        available_cash=_safe_decimal(
            data.get("availablecash") or data.get("available_cash")
        ),
        used_cash=_safe_decimal(data.get("usedcash") or data.get("used_cash")),
        payin=_safe_decimal(data.get("payin")),
        payout=_safe_decimal(data.get("payout")),
        realised_pnl=_safe_decimal(data.get("realisedpnl") or data.get("realised_pnl")),
        unrealised_pnl=_safe_decimal(
            data.get("unrealisedpnl") or data.get("unrealised_pnl")
        ),
    )


def margin_from_smartapi(data: Mapping[str, Any]) -> MarginInfo:
    """Convert a SmartAPI margin response to a TITAN MarginInfo."""
    return MarginInfo(
        total_margin=_safe_decimal(data.get("totalmargin") or data.get("total_margin")),
        used_margin=_safe_decimal(data.get("usedmargin") or data.get("used_margin")),
        available_margin=_safe_decimal(
            data.get("availablemargin") or data.get("available_margin")
        ),
        delivery_margin=_safe_decimal(
            data.get("deliverymargin") or data.get("delivery_margin")
        ),
        span_margin=_safe_decimal(data.get("spanmargin") or data.get("span_margin")),
        exposure_margin=_safe_decimal(
            data.get("exposuremargin") or data.get("exposure_margin")
        ),
    )


def profile_from_smartapi(data: Mapping[str, Any]) -> AccountProfile:
    """Convert a SmartAPI profile response to a TITAN AccountProfile."""
    exchanges_raw = data.get("exchanges") or []
    enabled = tuple(
        to_exchange(e) if isinstance(e, str) else Exchange.NSE for e in exchanges_raw
    )

    return AccountProfile(
        account_id=_safe_str(
            data.get("clientid") or data.get("client_id") or data.get("account_id")
        ),
        name=_safe_str(data.get("name") or data.get("username")),
        email=_safe_str(data.get("email")),
        phone=_safe_str(data.get("phone") or data.get("mobile")),
        broker="Angel One",
        account_type=_safe_str(data.get("accounttype") or data.get("account_type")),
        enabled_exchanges=enabled,
    )


# ---------------------------------------------------------------------------
# TITAN models → SmartAPI JSON payloads
# ---------------------------------------------------------------------------


def order_request_to_smartapi(request: OrderRequest) -> dict[str, Any]:
    """Convert a TITAN OrderRequest to a SmartAPI order payload."""
    payload: dict[str, Any] = {
        "symbol": request.symbol,
        "exchange": _EXCHANGE_REVERSE.get(request.exchange, "NSE"),
        "transactiontype": _SIDE_REVERSE.get(request.side, "BUY"),
        "ordertype": _ORDER_TYPE_REVERSE.get(request.order_type, "MARKET"),
        "quantity": request.quantity,
        "producttype": _PRODUCT_REVERSE.get(request.product, "DELIVERY"),
        "validity": _VALIDITY_REVERSE.get(request.validity, "DAY"),
        "price": str(request.price) if request.price is not None else "0",
        "triggerprice": (
            str(request.trigger_price) if request.trigger_price is not None else "0"
        ),
        "discloseqty": request.disclose_quantity,
    }
    if request.tag:
        payload["tag"] = request.tag
    return payload


def modify_request_to_smartapi(
    broker_order_id: str,
    quantity: int,
    price: str | None = None,
    trigger_price: str | None = None,
    validity: str | None = None,
) -> dict[str, Any]:
    """Convert modification parameters to a SmartAPI modify payload."""
    payload: dict[str, Any] = {
        "orderid": broker_order_id,
        "quantity": quantity,
    }
    if price:
        payload["price"] = price
    if trigger_price:
        payload["triggerprice"] = trigger_price
    if validity:
        payload["validity"] = validity
    return payload


def cancel_request_to_smartapi(broker_order_id: str) -> dict[str, Any]:
    """Convert cancellation parameters to a SmartAPI cancel payload."""
    return {"orderid": broker_order_id}
