from datetime import datetime
from decimal import Decimal
from typing import Any

from titan.brokers.angelone.account import AngelOneAccountProvider
from titan.brokers.angelone.auth import AngelOneAuthenticator
from titan.brokers.angelone.history import AngelOneHistoricalDataProvider
from titan.brokers.angelone.market import AngelOneMarketDataProvider
from titan.brokers.angelone.orders import AngelOneOrderProvider
from titan.brokers.angelone.portfolio import AngelOnePortfolioProvider
from titan.brokers.broker import Broker
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


class AngelOneBroker(Broker):
    """Concrete Angel One broker adapter implementing the TITAN Broker interface.

    Composes specialised provider modules and delegates each domain
    to the appropriate component. This is the only class that consumers
    of the Angel One adapter need to import.

    Usage:
        broker = AngelOneBroker(api_key="...", client_id="...", pin="...")
        broker.connect()
        quote = broker.quote("RELIANCE")
        broker.disconnect()
    """

    def __init__(
        self,
        api_key: str | None = None,
        client_id: str | None = None,
        pin: str | None = None,
        totp_secret: str | None = None,
        smart_connect: Any | None = None,
    ) -> None:
        self._authenticator = AngelOneAuthenticator(
            api_key=api_key,
            client_id=client_id,
            pin=pin,
            totp_secret=totp_secret,
            smart_connect=smart_connect,
        )
        self._market = AngelOneMarketDataProvider(smart_connect=smart_connect)
        self._history = AngelOneHistoricalDataProvider(smart_connect=smart_connect)
        self._orders = AngelOneOrderProvider(smart_connect=smart_connect)
        self._portfolio = AngelOnePortfolioProvider(smart_connect=smart_connect)
        self._account = AngelOneAccountProvider(smart_connect=smart_connect)

    # ------------------------------------------------------------------
    # Connection lifecycle (Broker interface)
    # ------------------------------------------------------------------

    def connect(self) -> ConnectionStatus:
        """Establish connection to Angel One SmartAPI."""
        status = self._authenticator.login()
        if status == ConnectionStatus.CONNECTED:
            sc = self._authenticator.smart_connect
            self._market.smart_connect = sc
            self._history.smart_connect = sc
            self._orders.smart_connect = sc
            self._portfolio.smart_connect = sc
            self._account.smart_connect = sc
        return status

    def disconnect(self) -> ConnectionStatus:
        """Disconnect from Angel One SmartAPI."""
        status = self._authenticator.logout()
        self._market.smart_connect = None
        self._history.smart_connect = None
        self._orders.smart_connect = None
        self._portfolio.smart_connect = None
        self._account.smart_connect = None
        return status

    def is_connected(self) -> bool:
        return self._authenticator.validate_session()

    # ------------------------------------------------------------------
    # Market data (MarketDataProvider)
    # ------------------------------------------------------------------

    def quote(self, symbol: str) -> Quote:
        return self._market.quote(symbol)

    def quotes(self, symbols: list[str]) -> dict[str, Quote]:
        return self._market.quotes(symbols)

    def ltp(self, symbol: str) -> Decimal:
        return self._market.ltp(symbol)

    def option_chain(
        self,
        symbol: str,
        expiry: str | None = None,
    ) -> list[Quote]:
        return self._market.option_chain(symbol, expiry)

    def market_depth(self, symbol: str, level: int = 5) -> MarketDepth:
        return self._market.market_depth(symbol)

    # ------------------------------------------------------------------
    # Historical data (HistoricalDataProvider)
    # ------------------------------------------------------------------

    def history(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime | None = None,
    ) -> list[Candle]:
        return self._history.history(symbol, interval, start, end)

    def intraday(self, symbol: str, interval: str = "1min") -> list[Candle]:
        return self._history.intraday(symbol, interval)

    def ohlcv(
        self,
        symbol: str,
        interval: str = "1day",
        limit: int = 100,
    ) -> list[Candle]:
        return self._history.ohlcv(symbol, interval, limit)

    # ------------------------------------------------------------------
    # Orders (OrderProvider)
    # ------------------------------------------------------------------

    def place_order(self, request: OrderRequest) -> OrderResponse:
        return self._orders.place_order(request)

    def modify_order(self, request: ModifyOrderRequest) -> OrderResponse:
        return self._orders.modify_order(request)

    def cancel_order(self, request: CancelOrderRequest) -> OrderResponse:
        return self._orders.cancel_order(request)

    def order(self, broker_order_id: str) -> Order:
        return self._orders.order(broker_order_id)

    def orders(
        self,
        symbol: str | None = None,
        since: datetime | None = None,
    ) -> list[Order]:
        return self._orders.orders(symbol, since)

    # ------------------------------------------------------------------
    # Portfolio (PortfolioProvider)
    # ------------------------------------------------------------------

    def positions(self) -> list[Position]:
        return self._portfolio.positions()

    def holdings(self) -> list[Holding]:
        return self._portfolio.holdings()

    def trades(
        self,
        symbol: str | None = None,
        since: datetime | None = None,
    ) -> list[Trade]:
        return self._portfolio.trades(symbol, since)

    # ------------------------------------------------------------------
    # Account (AccountProvider)
    # ------------------------------------------------------------------

    def funds(self) -> FundsInfo:
        return self._account.funds()

    def margin(self) -> MarginInfo:
        return self._account.margin()

    def profile(self) -> AccountProfile:
        return self._account.profile()
