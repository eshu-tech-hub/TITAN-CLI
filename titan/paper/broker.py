from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from titan.brokers.broker import Broker
from titan.brokers.models import (
    AccountProfile,
    CancelOrderRequest,
    Candle,
    ConnectionStatus,
    Exchange,
    FundsInfo,
    Holding,
    MarginInfo,
    MarketDepth,
    MarketDepthLevel,
    ModifyOrderRequest,
    Order,
    OrderRequest,
    OrderResponse,
    OrderStatus,
    Position,
    Quote,
    Trade,
)
from titan.paper.exceptions import PaperOrderError
from titan.paper.fills import FillEngine
from titan.paper.journal import TradeJournal
from titan.paper.models import PaperFill, PaperOrder
from titan.paper.performance import PerformanceEngine
from titan.paper.portfolio import PaperPortfolio
from titan.paper.positions import PositionEngine


class PaperBroker(Broker):
    """Paper trading broker that simulates order execution.

    Implements the full Broker interface without any external
    API dependencies. All order execution is simulated using
    the FillEngine, with positions tracked by PositionEngine,
    capital tracked by PaperPortfolio, and events recorded
    by TradeJournal.

    Live Broker and Paper Broker are interchangeable without
    changing any upstream code.
    """

    def __init__(
        self,
        initial_cash: Decimal = Decimal(100000),
        fill_engine: FillEngine | None = None,
        position_engine: PositionEngine | None = None,
        portfolio: PaperPortfolio | None = None,
        journal: TradeJournal | None = None,
        performance: PerformanceEngine | None = None,
    ) -> None:
        """Initialize the paper broker.

        Args:
            initial_cash: Starting cash balance.
            fill_engine: Custom fill engine (uses default if None).
            position_engine: Custom position engine (uses default if None).
            portfolio: Custom portfolio tracker (uses default if None).
            journal: Custom trade journal (uses default if None).
            performance: Custom performance engine (uses default if None).
        """
        self._connected: bool = False
        self._prices: dict[str, Decimal] = {}
        self._account_id: str = str(uuid4())
        self._order_counter: int = 0
        self._initial_cash: Decimal = initial_cash

        self.fill_engine: FillEngine = fill_engine or FillEngine()
        self.position_engine: PositionEngine = position_engine or PositionEngine()
        self.portfolio: PaperPortfolio = portfolio or PaperPortfolio(
            initial_cash=initial_cash
        )
        self.journal: TradeJournal = journal or TradeJournal()
        self.performance: PerformanceEngine = performance or PerformanceEngine(
            journal=self.journal
        )

    # ── Connection ─────────────────────────────────────────────

    def connect(self) -> ConnectionStatus:
        """Establish simulated connection."""
        self._connected = True
        return ConnectionStatus.CONNECTED

    def disconnect(self) -> ConnectionStatus:
        """Disconnect simulated connection."""
        self._connected = False
        return ConnectionStatus.DISCONNECTED

    def is_connected(self) -> bool:
        """Return connection status."""
        return self._connected

    # ── Market Data ────────────────────────────────────────────

    def quote(self, symbol: str) -> Quote:
        """Return a simulated quote for the given symbol."""
        price = self._get_price(symbol)
        spread = price * Decimal("0.001")
        return Quote(
            symbol=symbol,
            exchange=Exchange.NSE,
            last_price=price,
            bid=price - spread,
            ask=price + spread,
            bid_quantity=1000,
            ask_quantity=1000,
            open=price,
            high=price * Decimal("1.01"),
            low=price * Decimal("0.99"),
            close=price,
            volume=100000,
            timestamp=datetime.now(UTC),
        )

    def quotes(self, symbols: list[str]) -> dict[str, Quote]:
        """Return simulated quotes for multiple symbols."""
        return {s: self.quote(s) for s in symbols}

    def option_chain(
        self,
        symbol: str,
        expiry: str | None = None,
    ) -> list[Quote]:
        """Return empty option chain (not simulated)."""
        return []

    def market_depth(self, symbol: str, level: int = 5) -> MarketDepth:
        """Return simulated market depth."""
        price = self._get_price(symbol)
        bid_levels: list[MarketDepthLevel] = []
        for i in range(level):
            offset = Decimal(str(i + 1)) * Decimal("0.50")
            bid_levels.append(
                MarketDepthLevel(
                    price=price - offset,
                    quantity=1000 * (level - i),
                    orders=10 * (level - i),
                )
            )
        ask_levels: list[MarketDepthLevel] = []
        for i in range(level):
            offset = Decimal(str(i + 1)) * Decimal("0.50")
            ask_levels.append(
                MarketDepthLevel(
                    price=price + offset,
                    quantity=1000 * (level - i),
                    orders=10 * (level - i),
                )
            )
        return MarketDepth(
            symbol=symbol,
            exchange=Exchange.NSE,
            bids=tuple(bid_levels),
            asks=tuple(ask_levels),
            timestamp=datetime.now(UTC),
        )

    def ltp(self, symbol: str) -> Decimal:
        """Return the last traded price for a symbol."""
        return self._get_price(symbol)

    # ── Historical Data ────────────────────────────────────────

    def history(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime | None = None,
    ) -> list[Candle]:
        """Return empty list (historical data not simulated)."""
        return []

    def intraday(self, symbol: str, interval: str = "1min") -> list[Candle]:
        """Return empty list (intraday data not simulated)."""
        return []

    def ohlcv(
        self,
        symbol: str,
        interval: str = "1day",
        limit: int = 100,
    ) -> list[Candle]:
        """Return empty list (OHLCV data not simulated)."""
        return []

    # ── Order Management ───────────────────────────────────────

    def place_order(self, request: OrderRequest) -> OrderResponse:
        """Place and simulate a paper order.

        Creates an internal order, runs the fill engine,
        updates positions and portfolio, journals all events,
        and returns an OrderResponse.

        Args:
            request: The order request to simulate.

        Returns:
            OrderResponse with simulated fill details.

        Raises:
            PaperOrderError: If broker is not connected.
        """
        if not self._connected:
            raise PaperOrderError("Broker is not connected.")

        self._order_counter += 1
        order_id = str(uuid4())
        broker_order_id = f"PAPER-{self._order_counter:06d}"

        paper_order = PaperOrder(
            order_id=order_id,
            broker_order_id=broker_order_id,
            symbol=request.symbol,
            exchange=request.exchange,
            side=request.side,
            order_type=request.order_type,
            quantity=request.quantity,
            price=request.price,
            trigger_price=request.trigger_price,
            product=request.product,
            status=OrderStatus.OPEN,
            tag=request.tag,
            placed_at=datetime.now(UTC),
        )

        self.journal.record_order(paper_order)

        quote = self.quote(request.symbol)
        fills = self.fill_engine.fill(
            request=request,
            quote=quote,
            order_id=order_id,
            broker_order_id=broker_order_id,
        )

        if not fills:
            rejected = PaperOrder(
                order_id=paper_order.order_id,
                broker_order_id=paper_order.broker_order_id,
                symbol=paper_order.symbol,
                exchange=paper_order.exchange,
                side=paper_order.side,
                order_type=paper_order.order_type,
                quantity=paper_order.quantity,
                price=paper_order.price,
                trigger_price=paper_order.trigger_price,
                product=paper_order.product,
                status=OrderStatus.REJECTED,
                tag=paper_order.tag,
                rejected_reason="Order could not be filled at current price",
                placed_at=paper_order.placed_at,
            )
            self.journal.update_order(rejected)
            return OrderResponse(
                broker_order_id=broker_order_id,
                status=OrderStatus.REJECTED,
                message="Order could not be filled at current price",
            )

        for fill in fills:
            self.journal.record_fill(fill, paper_order)
            self.position_engine.apply_fill(fill)
            self.portfolio.apply_fill(fill)

        filled_order = self.journal.get_order(order_id)
        final_order = filled_order if filled_order is not None else paper_order

        pos = self.position_engine.get_position(request.symbol)
        if pos is not None and pos.quantity == 0:
            self.position_engine.close_position(request.symbol)

        return OrderResponse(
            broker_order_id=broker_order_id,
            status=OrderStatus.FILLED,
            filled_quantity=final_order.filled_quantity,
            pending_quantity=final_order.pending_quantity,
            average_price=self._compute_avg_price(fills),
            message="Order filled successfully",
            timestamp=datetime.now(UTC),
        )

    def modify_order(self, request: ModifyOrderRequest) -> OrderResponse:
        """Modify an existing pending order.

        Args:
            request: Modification request.

        Returns:
            OrderResponse with modification result.

        Raises:
            PaperOrderError: If order not found or already terminal.
        """
        paper_order = self.journal.get_order_by_broker_id(request.broker_order_id)
        if paper_order is None:
            raise PaperOrderError(f"Order {request.broker_order_id} not found.")

        if paper_order.status in (
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
        ):
            raise PaperOrderError(f"Cannot modify {paper_order.status.value} order.")

        old_quantity = paper_order.quantity
        modified = PaperOrder(
            order_id=paper_order.order_id,
            broker_order_id=paper_order.broker_order_id,
            symbol=paper_order.symbol,
            exchange=paper_order.exchange,
            side=paper_order.side,
            order_type=paper_order.order_type,
            quantity=request.quantity if request.quantity > 0 else paper_order.quantity,
            filled_quantity=paper_order.filled_quantity,
            pending_quantity=paper_order.pending_quantity,
            price=request.price if request.price is not None else paper_order.price,
            trigger_price=(
                request.trigger_price
                if request.trigger_price is not None
                else paper_order.trigger_price
            ),
            product=paper_order.product,
            status=OrderStatus.OPEN,
            fills=paper_order.fills,
            tag=paper_order.tag,
            placed_at=paper_order.placed_at,
        )
        self.journal.update_order(modified)
        self.journal.record_modification(
            order_id=modified.order_id,
            field_name="quantity",
            old_value=old_quantity,
            new_value=modified.quantity,
        )

        return OrderResponse(
            broker_order_id=request.broker_order_id,
            status=OrderStatus.OPEN,
            message="Order modified successfully",
        )

    def cancel_order(self, request: CancelOrderRequest) -> OrderResponse:
        """Cancel an existing pending order.

        Args:
            request: Cancellation request.

        Returns:
            OrderResponse with cancellation result.

        Raises:
            PaperOrderError: If order not found.
        """
        paper_order = self.journal.get_order_by_broker_id(request.broker_order_id)
        if paper_order is None:
            raise PaperOrderError(f"Order {request.broker_order_id} not found.")

        self.journal.record_cancellation(
            paper_order.order_id,
            reason=request.reason,
        )

        return OrderResponse(
            broker_order_id=request.broker_order_id,
            status=OrderStatus.CANCELLED,
            message="Order cancelled",
        )

    def order(self, broker_order_id: str) -> Order:
        """Fetch a single order by broker-assigned ID.

        Args:
            broker_order_id: The broker order ID.

        Returns:
            Broker Order model.

        Raises:
            PaperOrderError: If order not found.
        """
        paper_order = self.journal.get_order_by_broker_id(broker_order_id)
        if paper_order is None:
            raise PaperOrderError(f"Order {broker_order_id} not found.")
        return self.journal.to_broker_order(paper_order)

    def orders(
        self,
        symbol: str | None = None,
        since: datetime | None = None,
    ) -> list[Order]:
        """Fetch orders, optionally filtered.

        Args:
            symbol: Filter by symbol.
            since: Filter by placement time.

        Returns:
            List of broker Order models.
        """
        return self.journal.to_broker_orders(symbol, since)

    # ── Portfolio ──────────────────────────────────────────────

    def positions(self) -> list[Position]:
        """Fetch all open positions.

        Returns:
            List of broker Position models.
        """
        return self.position_engine.to_broker_positions()

    def holdings(self) -> list[Holding]:
        """Fetch all holdings.

        Returns:
            List of broker Holding models.
        """
        return self.position_engine.to_broker_holdings()

    def trades(
        self,
        symbol: str | None = None,
        since: datetime | None = None,
    ) -> list[Trade]:
        """Fetch executed trades, optionally filtered.

        Args:
            symbol: Filter by symbol.
            since: Filter by trade time.

        Returns:
            List of broker Trade models.
        """
        return self.journal.to_broker_trades(symbol, since)

    # ── Account ────────────────────────────────────────────────

    def funds(self) -> FundsInfo:
        """Fetch account funds summary.

        Returns:
            FundsInfo based on current portfolio state.
        """
        state = self.portfolio.compute_state(
            self.position_engine.open_positions(),
        )
        return self.portfolio.to_funds_info(state)

    def margin(self) -> MarginInfo:
        """Fetch account margin details.

        Returns:
            MarginInfo based on current portfolio state.
        """
        return self.portfolio.to_margin_info()

    def profile(self) -> AccountProfile:
        """Fetch simulated account profile.

        Returns:
            AccountProfile for the paper account.
        """
        return AccountProfile(
            account_id=self._account_id,
            name="Paper Trader",
            email="paper@titan.local",
            broker="paper",
            account_type="simulation",
            enabled_exchanges=(Exchange.NSE, Exchange.BSE),
        )

    # ── Internal Helpers ───────────────────────────────────────

    def set_price(self, symbol: str, price: Decimal) -> None:
        """Manually set a price for a symbol (for testing).

        Args:
            symbol: Trading symbol.
            price: Price to set.
        """
        self._prices[symbol] = price

    def reset(self) -> None:
        """Reset all paper trading state.

        Clears positions, portfolio, journal, and prices.
        """
        self.position_engine.reset()
        self.portfolio.reset()
        self.journal.reset()
        self._prices.clear()
        self._order_counter = 0

    def _get_price(self, symbol: str) -> Decimal:
        """Get the current simulated price for a symbol.

        Uses the explicit price set via set_price(), or
        falls back to a default price of 100.0.
        """
        return self._prices.get(symbol, Decimal("100.0"))

    def _compute_avg_price(
        self,
        fills: list[PaperFill],
    ) -> Decimal | None:
        """Compute the average fill price from a list of fills."""
        if not fills:
            return None
        total_value = sum(f.price * Decimal(str(f.quantity)) for f in fills)
        total_qty = sum(f.quantity for f in fills)
        if total_qty == 0:
            return None
        return (total_value / Decimal(str(total_qty))).quantize(Decimal("0.01"))
