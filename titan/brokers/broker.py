from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal

from titan.brokers.models import (
    AccountProfile,
    CancelOrderRequest,
    Candle,
    ConnectionStatus,
    FundsInfo,
    Holding,
    MarginInfo,
    MarketDepth,
    ModifyOrderRequest,
    Order,
    OrderRequest,
    OrderResponse,
    Position,
    Quote,
    Trade,
)


class MarketDataProvider(ABC):
    """Abstract interface for real-time and snapshot market data."""

    @abstractmethod
    def quote(self, symbol: str) -> Quote:
        """Fetch a single snapshot quote."""

    @abstractmethod
    def quotes(self, symbols: list[str]) -> dict[str, Quote]:
        """Fetch snapshot quotes for multiple symbols."""

    @abstractmethod
    def option_chain(
        self,
        symbol: str,
        expiry: str | None = None,
    ) -> list[Quote]:
        """Fetch option chain quotes for a given underlying."""

    @abstractmethod
    def market_depth(self, symbol: str, level: int = 5) -> MarketDepth:
        """Fetch order book depth."""

    @abstractmethod
    def ltp(self, symbol: str) -> Decimal:
        """Fetch the last traded price."""


class HistoricalDataProvider(ABC):
    """Abstract interface for historical market data."""

    @abstractmethod
    def history(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime | None = None,
    ) -> list[Candle]:
        """Fetch historical candles for a date range."""

    @abstractmethod
    def intraday(self, symbol: str, interval: str = "1min") -> list[Candle]:
        """Fetch intraday candles for the current trading day."""

    @abstractmethod
    def ohlcv(
        self,
        symbol: str,
        interval: str = "1day",
        limit: int = 100,
    ) -> list[Candle]:
        """Fetch the most recent OHLCV candles."""


class OrderProvider(ABC):
    """Abstract interface for order management."""

    @abstractmethod
    def place_order(self, request: OrderRequest) -> OrderResponse:
        """Place a new order."""

    @abstractmethod
    def modify_order(self, request: ModifyOrderRequest) -> OrderResponse:
        """Modify an existing open order."""

    @abstractmethod
    def cancel_order(self, request: CancelOrderRequest) -> OrderResponse:
        """Cancel an existing open order."""

    @abstractmethod
    def order(self, broker_order_id: str) -> Order:
        """Fetch details of a single order by its broker-assigned ID."""

    @abstractmethod
    def orders(
        self,
        symbol: str | None = None,
        since: datetime | None = None,
    ) -> list[Order]:
        """Fetch a list of orders, optionally filtered."""


class PortfolioProvider(ABC):
    """Abstract interface for portfolio and position data."""

    @abstractmethod
    def positions(self) -> list[Position]:
        """Fetch all open positions."""

    @abstractmethod
    def holdings(self) -> list[Holding]:
        """Fetch all demat holdings."""

    @abstractmethod
    def trades(
        self,
        symbol: str | None = None,
        since: datetime | None = None,
    ) -> list[Trade]:
        """Fetch executed trades, optionally filtered."""


class AccountProvider(ABC):
    """Abstract interface for account information."""

    @abstractmethod
    def funds(self) -> FundsInfo:
        """Fetch account funds summary."""

    @abstractmethod
    def margin(self) -> MarginInfo:
        """Fetch account margin details."""

    @abstractmethod
    def profile(self) -> AccountProfile:
        """Fetch authenticated account profile."""


class Broker(
    MarketDataProvider,
    HistoricalDataProvider,
    OrderProvider,
    PortfolioProvider,
    AccountProvider,
    ABC,
):
    """Complete broker interface combining all provider abstractions.

    Concrete broker implementations must implement every method defined
    across MarketDataProvider, HistoricalDataProvider, OrderProvider,
    PortfolioProvider, and AccountProvider.

    This interface intentionally includes NO network logic, NO
    authentication, NO API keys, NO broker SDK imports. It is a
    pure contract between TITAN and any broker adapter.
    """

    @abstractmethod
    def connect(self) -> ConnectionStatus:
        """Establish a connection to the broker.

        Returns the resulting connection status.
        """

    @abstractmethod
    def disconnect(self) -> ConnectionStatus:
        """Disconnect from the broker.

        Returns the resulting connection status.
        """

    @abstractmethod
    def is_connected(self) -> bool:
        """Return whether the broker is currently connected."""
