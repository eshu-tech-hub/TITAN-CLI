import re

path = 'titan/brokers/yfinance/stream.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

new_class = """class YFinanceStreamSource:
    \"\"\"YFinance-based stream data source that polls for the latest 1m candle.\"\"\"

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
        for s in symbols:
            self._subscriptions.add(s)

    def unsubscribe(self, symbols: list[str] | str, exchange: str | Exchange = "NSE") -> None:
        if isinstance(symbols, str):
            symbols = [symbols]
        for s in symbols:
            self._subscriptions.discard(s)

    def _poll_loop(self) -> None:
        while self._connected:
            if not self._subscriptions:
                time.sleep(1.0)
                continue
            
            symbol = list(self._subscriptions)[0]
            yf_symbol = symbol if symbol.endswith(".NS") or symbol.endswith(".BO") else f"{symbol}.NS"
            
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
                        self._on_quote(quote)
            except Exception as e:
                logger.error(f"YFinanceStreamSource poll failed for {yf_symbol}: {e}")
            
            # Sleep for the interval, checking _connected frequently
            for _ in range(int(self._poll_interval * 10)):
                if not self._connected:
                    break
                time.sleep(0.1)

    def read(self) -> Quote | None:
        return None
"""

content = re.sub(r"class YFinanceStreamSource:[\s\S]*", new_class, content)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

