
path = 'titan/runtime/runtime.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target1 = """            self._start_broker()
            self._start_stream()"""
replacement1 = """            self._start_broker()
            self._warmup_historical_context()
            self._start_stream()"""
content = content.replace(target1, replacement1)

target2 = """    def _start_stream(self) -> None:"""
replacement2 = """    def _warmup_historical_context(self) -> None:
        import yfinance as yf
        from titan.market.models import Candle
        from titan.market.series import MarketDataSeries
        from titan.brokers.models import Exchange
        
        logger.info("Initiating historical context warmup")
        for symbol in self.watchlist:
            try:
                yf_sym = symbol if symbol.startswith("^") else (symbol if symbol.endswith(".NS") else f"{symbol}.NS")
                df = yf.download(yf_sym, period="2d", interval="1m", progress=False)
                if df.empty:
                    continue
                
                # Feed the last day's data through pipeline
                exchanges = self.broker.profile().enabled_exchanges
                exchange_val = exchanges[0] if exchanges else Exchange.NSE
                
                for ts, row in df.iterrows():
                    last_price = float(row["Close"].iloc[0]) if isinstance(row["Close"], pd.Series) else float(row["Close"])
                    vol_val = row.get("Volume", 0)
                    volume = int(vol_val.iloc[0]) if isinstance(vol_val, pd.Series) else int(vol_val)
                    
                    dt = ts.to_pydatetime()
                    if dt.tzinfo is None:
                        from datetime import UTC
                        dt = dt.replace(tzinfo=UTC)
                    else:
                        from datetime import UTC
                        dt = dt.astimezone(UTC)
                    
                    candle = Candle(
                        timestamp=dt,
                        open=float(row["Open"].iloc[0]) if isinstance(row["Open"], pd.Series) else float(row["Open"]),
                        high=float(row["High"].iloc[0]) if isinstance(row["High"], pd.Series) else float(row["High"]),
                        low=float(row["Low"].iloc[0]) if isinstance(row["Low"], pd.Series) else float(row["Low"]),
                        close=last_price,
                        volume=volume
                    )
                    market_data = MarketDataSeries(candles=[candle])
                    self.pipeline.run(symbol=symbol, exchange=exchange_val, market_data=market_data, abort_on_fatal=False)
                    
                logger.info(f"Historical warmup complete for {symbol}: {len(df)} candles")
            except Exception as e:
                logger.warning(f"Historical warmup failed for {symbol}: {e}")

    def _start_stream(self) -> None:"""
content = content.replace(target2, replacement2)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
