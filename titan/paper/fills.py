from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable
from uuid import uuid4

from titan.brokers.models import OrderRequest, OrderType, Quote

from titan.paper.exceptions import PaperFillError
from titan.paper.models import PaperFill

SlippageModel = Callable[[OrderRequest, Quote], Decimal]
LatencyModel = Callable[[OrderRequest], float]


def default_slippage(request: OrderRequest, quote: Quote) -> Decimal:
    """Default slippage model: 0.1% of last price for market orders."""
    if request.order_type != OrderType.MARKET:
        return Decimal("0")
    return quote.last_price * Decimal("0.001")


def default_latency(request: OrderRequest) -> float:
    """Default latency model: 50ms for all orders."""
    return 50.0


@dataclass(slots=True)
class FillEngine:
    """Simulates order fills for paper trading.

    Determines whether an order fills based on order type and
    current market conditions. Supports pluggable slippage and
    latency models for future realism.

    Attributes:
        slippage_model: Callable that computes slippage for a fill.
        latency_model: Callable that computes simulated latency.
    """

    slippage_model: SlippageModel = default_slippage
    latency_model: LatencyModel = default_latency

    def fill(
        self,
        request: OrderRequest,
        quote: Quote,
        order_id: str,
        broker_order_id: str,
    ) -> list[PaperFill]:
        """Determine fills for an order given current market conditions.

        Args:
            request: The order request to simulate.
            quote: Current market quote for the symbol.
            order_id: Internal order ID.
            broker_order_id: Broker-assigned order ID.

        Returns:
            A list of PaperFill events. Currently returns a single
            fill for market orders that can be filled immediately.
            Limit and stop orders are checked against quote prices.

        Raises:
            PaperFillError: If fill simulation fails.
        """
        if request.quantity <= 0:
            raise PaperFillError("Order quantity must be positive.")

        fill_price = self._determine_fill_price(request, quote)
        if fill_price is None:
            return []

        slippage = self.slippage_model(request, quote)
        latency = self.latency_model(request)

        price_with_slippage = fill_price + slippage

        commission = self._compute_commission(
            price=price_with_slippage,
            quantity=request.quantity,
        )

        fill = PaperFill(
            fill_id=str(uuid4()),
            order_id=order_id,
            broker_order_id=broker_order_id,
            symbol=request.symbol,
            exchange=request.exchange,
            side=request.side,
            quantity=request.quantity,
            price=price_with_slippage,
            product=request.product,
            commission=commission,
            slippage=slippage,
            latency_ms=latency,
            timestamp=datetime.now(timezone.utc),
        )

        return [fill]

    def _determine_fill_price(
        self,
        request: OrderRequest,
        quote: Quote,
    ) -> Decimal | None:
        """Determine fill price or None if the order would not fill.

        Market orders fill immediately at the current price.
        Limit orders fill only if the limit price is attainable.
        Stop orders convert to market when the trigger is hit.
        """
        if request.order_type == OrderType.MARKET:
            return self._market_fill_price(request, quote)

        if request.order_type == OrderType.LIMIT:
            return self._limit_fill_price(request, quote)

        if request.order_type in (OrderType.STOP_LOSS, OrderType.STOP_LOSS_LIMIT):
            return self._stop_fill_price(request, quote)

        return None

    def _market_fill_price(self, request: OrderRequest, quote: Quote) -> Decimal:
        """Market orders fill at the current price.

        Buys use the ask price (or last_price + spread estimate).
        Sells use the bid price (or last_price - spread estimate).
        """
        if request.side.value == "buy":
            return quote.ask if quote.ask is not None else quote.last_price
        return quote.bid if quote.bid is not None else quote.last_price

    def _limit_fill_price(self, request: OrderRequest, quote: Quote) -> Decimal | None:
        """Limit orders fill only when price is achievable.

        Buy limit fills if limit price >= ask (or last_price).
        Sell limit fills if limit price <= bid (or last_price).
        Returns the fill price or None if not fillable.
        """
        if request.price is None:
            return None

        if request.side.value == "buy":
            reference = quote.ask if quote.ask is not None else quote.last_price
            if request.price >= reference:
                return reference
            return None

        reference = quote.bid if quote.bid is not None else quote.last_price
        if request.price <= reference:
            return reference
        return None

    def _stop_fill_price(
        self,
        request: OrderRequest,
        quote: Quote,
    ) -> Decimal | None:
        """Stop orders trigger when the stop price is crossed.

        Stop-buy (stop-loss buy) triggers when last_price >= trigger.
        Stop-sell (stop-loss sell) triggers when last_price <= trigger.
        Once triggered, fills like a market order.
        """
        trigger = request.trigger_price
        if trigger is None:
            return None

        if request.side.value == "buy":
            if quote.last_price >= trigger:
                return self._market_fill_price(request, quote)
            return None

        if quote.last_price <= trigger:
            return self._market_fill_price(request, quote)
        return None

    def _compute_commission(
        self,
        price: Decimal,
        quantity: int,
    ) -> Decimal:
        """Compute simulated commission.

        Currently uses a flat per-order fee plus a small
        percentage of the trade value.
        """
        trade_value = price * Decimal(str(quantity))
        percentage_fee = trade_value * Decimal("0.0001")
        flat_fee = Decimal("10")
        result = flat_fee + percentage_fee
        return result.quantize(Decimal("0.01"))
