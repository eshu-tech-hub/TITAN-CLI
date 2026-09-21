from __future__ import annotations

import time
from datetime import UTC
from decimal import Decimal

import pandas as pd
import yfinance as yf

from titan.brokers.models import ConnectionStatus, Exchange, Quote
from titan.core.logger import logger


class YFinanceStreamSource:
    """YFinance-based stream data source that polls for the latest 1m candle."""

    def __init__(self, poll_interval: float = 60.0) -> None:
        self._connected = False
        self._subscriptions: set[str] = set()
        self._poll_interval = poll_interval
        self._on_quote = None
        self._thread = None

    def set_on_quote(self, callback) -> None:
        self._on_quote = callback

    def connect(self) -> ConnectionStatus:
        self._connected = True
        return ConnectionStatus.CONNECTED

    def disconnect(self) -> ConnectionStatus:
        self.stop()
        self._subscriptions.clear()
        return ConnectionStatus.DISCONNECTED

    def start(self) -> None:
        self._connected = True
        if self._thread is None or not self._thread.is_alive():
            import threading
            self._thread = threading.Thread(target=self._poll_loop, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._connected = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def is_connected(self) -> bool:
        return self._connected

    def subscribe(self, symbols: list[str] | str, exchange: str | Exchange = "NSE") -> None:
        if isinstance(symbols, str):
            symbols = [symbols]
            
        normalized = []
        for sym in symbols:
            if sym.startswith("^"):
                normalized.append(sym)
            elif not sym.endswith(".NS") and not sym.endswith(".BO"):
                normalized.append(f"{sym}.NS")
            else:
                normalized.append(sym)
        self._subscriptions.update(normalized)

    def unsubscribe(self, symbols: list[str] | str, exchange: str | Exchange = "NSE") -> None:
        if isinstance(symbols, str):
            symbols = [symbols]
            
        normalized = []
        for sym in symbols:
            if sym.startswith("^"):
                normalized.append(sym)
            elif not sym.endswith(".NS") and not sym.endswith(".BO"):
                normalized.append(f"{sym}.NS")
            else:
                normalized.append(sym)
        for sym in normalized:
            self._subscriptions.discard(sym)
    def _poll_loop(self) -> None:
        while self._connected:
            if not self._subscriptions:
                time.sleep(1.0)
                continue
            
            for symbol in list(self._subscriptions):
                if not self._connected:
                    break
                
                yf_symbol = symbol
                
                try:
                    df = yf.download(yf_symbol, period="1d", interval="1m", progress=False)
                    if not df.empty:
                        latest_row = df.iloc[-1]
                        last_price = float(latest_row["Close"].iloc[0]) if isinstance(latest_row["Close"], pd.Series) else float(latest_row["Close"])
                        
                        vol_val = latest_row.get("Volume", 0)
                        volume = int(vol_val.iloc[0]) if isinstance(vol_val, pd.Series) else int(vol_val)
            
                        dt = df.index[-1].to_pydatetime()
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=UTC)
                        else:
                            dt = dt.astimezone(UTC)
            
                        quote = Quote(
                            symbol=symbol,
                            exchange=Exchange.NSE,
                            last_price=Decimal(str(last_price)),
                            volume=volume,
                            timestamp=dt,
                        )
                        
                        if self._on_quote:
                            try:
                                self._on_quote(quote)
                            except Exception:
                                import traceback
                                with open("titan_crash.log", "a") as err_f:
                                    err_f.write(f"Pipeline Execution Crash:\n{traceback.format_exc()}\n")
                except Exception as e:
                    logger.error(f"YFinanceStreamSource poll failed for {yf_symbol}: {e}")
                    
                time.sleep(1.0)  # Avoid hammering YF between symbols
            
            # Sleep for the remaining interval, checking _connected frequently
            for _ in range(int(self._poll_interval * 10)):
                if not self._connected:
                    break
                time.sleep(0.1)

    def read(self) -> Quote | None:
        return None
