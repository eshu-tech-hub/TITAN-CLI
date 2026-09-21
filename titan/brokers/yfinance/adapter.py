import time
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pandas as pd
import yfinance as yf

from titan.brokers.broker import Broker
from titan.brokers.exceptions import BrokerError
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
    ModifyOrderRequest,
    Order,
    OrderRequest,
    OrderResponse,
    Position,
    Quote,
    Trade,
)


class YahooFinanceBroker(Broker):
    """Yahoo Finance broker adapter for market data.
    
    Provides real-time quotes and historical data without authentication.
    Orders and portfolio management are explicitly mocked or disabled.
    """

    def __init__(self, store: Any | None = None, **kwargs: Any) -> None:
        self._connected = False
        self._quote_cache: dict[str, tuple[Quote, float]] = {}
        self._quote_ttl = 5.0  # 5 seconds TTL to avoid IP bans
        
        if store is None:
            from titan.storage.market_data import MarketDataStore
            self.store = MarketDataStore(":memory:")
        else:
            self.store = store

    def _map_symbol(self, symbol: str) -> str:
        """Map TITAN symbol to yfinance format (e.g. RELIANCE -> RELIANCE.NS)."""
        if not symbol.endswith(".NS") and not symbol.endswith(".BO"):
            return f"{symbol}.NS"
        return symbol

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> ConnectionStatus:
        self._connected = True
        return ConnectionStatus.CONNECTED

    def disconnect(self) -> ConnectionStatus:
        self._connected = False
        self._quote_cache.clear()
        return ConnectionStatus.DISCONNECTED

    def is_connected(self) -> bool:
        return self._connected

    # ------------------------------------------------------------------
    # Market data
    # ------------------------------------------------------------------

    def quote(self, symbol: str) -> Quote:
        now = time.time()
        
        # Check cache
        if symbol in self._quote_cache:
            cached_quote, timestamp = self._quote_cache[symbol]
            if now - timestamp < self._quote_ttl:
                return cached_quote

        yf_symbol = self._map_symbol(symbol)
        try:
            ticker = yf.Ticker(yf_symbol)
            fast_info = ticker.fast_info
            
            # fast_info might be missing keys if invalid symbol
            last_price = Decimal(str(fast_info.last_price))
            
            # Construct a basic Quote
            q = Quote(
                symbol=symbol,
                exchange=Exchange.NSE,
                last_price=last_price,
                open=Decimal(str(fast_info.open)) if hasattr(fast_info, 'open') else None,
                high=Decimal(str(fast_info.day_high)) if hasattr(fast_info, 'day_high') else None,
                low=Decimal(str(fast_info.day_low)) if hasattr(fast_info, 'day_low') else None,
                close=Decimal(str(fast_info.previous_close)) if hasattr(fast_info, 'previous_close') else None,
                volume=int(fast_info.last_volume) if hasattr(fast_info, 'last_volume') else 0,
                timestamp=datetime.now(UTC),
            )
            
            self._quote_cache[symbol] = (q, now)
            return q
        except Exception as e:
            raise BrokerError(f"Failed to fetch quote for {symbol}: {e}") from e

    def quotes(self, symbols: list[str]) -> dict[str, Quote]:
        return {s: self.quote(s) for s in symbols}

    def ltp(self, symbol: str) -> Decimal:
        return self.quote(symbol).last_price

    def option_chain(self, symbol: str, expiry: str | None = None) -> list[Quote]:
        return []  # Mocked

    def market_depth(self, symbol: str, level: int = 5) -> MarketDepth:
        return MarketDepth(symbol=symbol, exchange=Exchange.NSE)  # Mocked

    def _extract_val(self, row: Any, col: str) -> float:
        val = row[col]
        return float(val.iloc[0]) if isinstance(val, pd.Series) else float(val)

    # ------------------------------------------------------------------
    # Historical data
    # ------------------------------------------------------------------

    def history(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime | None = None,
    ) -> list[Candle]:
        yf_symbol = self._map_symbol(symbol)
        
        interval_map = {
            "1min": "1m", "5min": "5m", "15min": "15m", "30min": "30m",
            "60min": "1h", "1hour": "1h", "1day": "1d", "1wk": "1wk", "1mo": "1mo"
        }
        yf_interval = interval_map.get(interval, "1d")
        
        target_start = start.astimezone(UTC) if start.tzinfo else start.replace(tzinfo=UTC)
        target_end = (end or datetime.now(UTC)).astimezone(UTC) if end else datetime.now(UTC)
        
        # Load local data block
        cached_candles = self.store.load_candles(symbol, interval)
        
        fetch_ranges = []
        if not cached_candles:
            fetch_ranges.append((target_start, target_end))
        else:
            local_start = cached_candles[0].timestamp
            local_end = cached_candles[-1].timestamp
            
            if local_start > target_start:
                fetch_ranges.append((target_start, local_start))
            if local_end < target_end:
                fetch_ranges.append((local_end, target_end))
                
        for fetch_start, fetch_end in fetch_ranges:
            try:
                df = yf.download(
                    yf_symbol, 
                    start=fetch_start, 
                    end=fetch_end, 
                    interval=yf_interval,
                    progress=False
                )
                
                if not df.empty:
                    new_candles = []
                    for index, row in df.iterrows():
                        dt = index.to_pydatetime()
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=UTC)
                        else:
                            dt = dt.astimezone(UTC)
                            
                        new_candles.append(Candle(
                            timestamp=dt,
                            open=float(self._extract_val(row, "Open")),
                            high=float(self._extract_val(row, "High")),
                            low=float(self._extract_val(row, "Low")),
                            close=float(self._extract_val(row, "Close")),
                            volume=int(self._extract_val(row, "Volume")),
                        ))
                    if new_candles:
                        self.store.save_candles(symbol, interval, new_candles)
            except Exception:
                # Let the final load fulfill what it can
                pass

        # Final Return
        return self.store.load_candles(symbol, interval, start=target_start, end=target_end)

    def intraday(self, symbol: str, interval: str = "1min") -> list[Candle]:
        # yf requires a range for 1m data (max 7 days)
        # We can just fetch the last 1 day
        yf_symbol = self._map_symbol(symbol)
        try:
            df = yf.download(yf_symbol, period="1d", interval="1m", progress=False)
            if df.empty:
                return []
                
            candles = []
            for index, row in df.iterrows():
                dt = index.to_pydatetime()
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=UTC)
                    
                candles.append(Candle(
                    datetime=dt,
                    open=Decimal(str(self._extract_val(row, "Open"))),
                    high=Decimal(str(self._extract_val(row, "High"))),
                    low=Decimal(str(self._extract_val(row, "Low"))),
                    close=Decimal(str(self._extract_val(row, "Close"))),
                    volume=int(self._extract_val(row, "Volume")),
                ))
            return candles
        except Exception as e:
            raise BrokerError(f"Failed to fetch intraday for {symbol}: {e}") from e

    def ohlcv(
        self,
        symbol: str,
        interval: str = "1day",
        limit: int = 100,
    ) -> list[Candle]:
        # Fetch standard history for a period depending on interval
        yf_symbol = self._map_symbol(symbol)
        period = "1y" if interval in ("1day", "1d") else "1mo"
        interval_map = {
            "1min": "1m", "5min": "5m", "15min": "15m", "30min": "30m",
            "60min": "1h", "1hour": "1h", "1day": "1d", "1wk": "1wk", "1mo": "1mo"
        }
        yf_interval = interval_map.get(interval, "1d")
        
        try:
            df = yf.download(yf_symbol, period=period, interval=yf_interval, progress=False)
            if df.empty:
                return []
                
            # Limit the rows
            df = df.tail(limit)
                
            candles = []
            for index, row in df.iterrows():
                dt = index.to_pydatetime()
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=UTC)
                    
                candles.append(Candle(
                    datetime=dt,
                    open=Decimal(str(self._extract_val(row, "Open"))),
                    high=Decimal(str(self._extract_val(row, "High"))),
                    low=Decimal(str(self._extract_val(row, "Low"))),
                    close=Decimal(str(self._extract_val(row, "Close"))),
                    volume=int(self._extract_val(row, "Volume")),
                ))
            return candles
        except Exception as e:
            raise BrokerError(f"Failed to fetch ohlcv for {symbol}: {e}") from e

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    def place_order(self, request: OrderRequest) -> OrderResponse:
        raise NotImplementedError("YFinance does not support live execution.")

    def modify_order(self, request: ModifyOrderRequest) -> OrderResponse:
        raise NotImplementedError("YFinance does not support live execution.")

    def cancel_order(self, request: CancelOrderRequest) -> OrderResponse:
        raise NotImplementedError("YFinance does not support live execution.")

    def order(self, broker_order_id: str) -> Order:
        raise BrokerError("YFinance does not support order querying.")

    def orders(
        self,
        symbol: str | None = None,
        since: datetime | None = None,
    ) -> list[Order]:
        return []

    # ------------------------------------------------------------------
    # Portfolio
    # ------------------------------------------------------------------

    def positions(self) -> list[Position]:
        return []

    def holdings(self) -> list[Holding]:
        return []

    def trades(
        self,
        symbol: str | None = None,
        since: datetime | None = None,
    ) -> list[Trade]:
        return []

    # ------------------------------------------------------------------
    # Account
    # ------------------------------------------------------------------

    def funds(self) -> FundsInfo:
        return FundsInfo(
            available_cash=Decimal("1000000.00"),
            used_cash=Decimal("0.00"),
        )

    def margin(self) -> MarginInfo:
        return MarginInfo(
            total_margin=Decimal("1000000.00"),
            available_margin=Decimal("1000000.00"),
        )

    def profile(self) -> AccountProfile:
        return AccountProfile(
            account_id="YF_PAPER_01",
            name="Yahoo Finance Paper Trading",
            broker="yfinance",
            account_type="paper",
        )
