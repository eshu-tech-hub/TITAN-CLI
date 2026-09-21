
path = 'titan/brokers/yfinance/stream.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """            symbol = list(self._subscriptions)[0]
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
                                err_f.write(f"Pipeline Execution Crash:\\n{traceback.format_exc()}\\n")
            except Exception as e:
                logger.error(f"YFinanceStreamSource poll failed for {yf_symbol}: {e}")
            
            # Sleep for the interval, checking _connected frequently
            for _ in range(int(self._poll_interval * 10)):
                if not self._connected:
                    break
                time.sleep(0.1)"""

replacement = """            for symbol in list(self._subscriptions):
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
                                    err_f.write(f"Pipeline Execution Crash:\\n{traceback.format_exc()}\\n")
                except Exception as e:
                    logger.error(f"YFinanceStreamSource poll failed for {yf_symbol}: {e}")
                    
                time.sleep(1.0)  # Avoid hammering YF between symbols
            
            # Sleep for the remaining interval, checking _connected frequently
            for _ in range(int(self._poll_interval * 10)):
                if not self._connected:
                    break
                time.sleep(0.1)"""

content = content.replace(target, replacement)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
