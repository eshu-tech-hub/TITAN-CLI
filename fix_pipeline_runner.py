
path = 'titan/runtime/runtime.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """    def _pipeline_runner(self) -> Any:"""
replacement = """    def _pipeline_runner(self, quote=None) -> Any:"""
content = content.replace(target, replacement)

# Replace the broker.ohlcv part
target_ohlcv = """        # Fetch latest market data for the pipeline
        try:
            candles = self.broker.ohlcv(symbol=symbol, interval="1min", limit=100)
            from titan.market.series import MarketDataSeries
            market_data = MarketDataSeries(symbol=symbol, timeframe="1m", candles=candles)
        except Exception as exc:
            logger.error(f"Failed to fetch market data for pipeline: {exc}")
            market_data = None
            
        report = self.pipeline.run(symbol=symbol, exchange=exchange_val, market_data=market_data)"""

replacement_ohlcv = """        market_data = None
        if quote is not None:
            from titan.market.models import Candle
            from titan.market.series import MarketDataSeries
            candle = Candle(
                timestamp=quote.timestamp,
                open=float(quote.last_price),
                high=float(quote.last_price),
                low=float(quote.last_price),
                close=float(quote.last_price),
                volume=int(quote.volume)
            )
            market_data = MarketDataSeries(candles=[candle])

        try:
            report = self.pipeline.run(symbol=symbol, exchange=exchange_val, market_data=market_data)
        except Exception as e:
            import traceback
            with open("pipeline_crash.log", "a") as f:
                f.write(f"PIPELINE CRASH:\\n{traceback.format_exc()}\\n")
            # Return an empty report or re-raise? "Do not re-raise, let the engine survive"
            from titan.pipeline.models import PipelineReport
            report = PipelineReport()"""

content = content.replace(target_ohlcv, replacement_ohlcv)

target_fallback = """                target = self.target_symbol or "^NSEI"
                if hasattr(self.stream, "source") and hasattr(self.stream.source, "subscribe"):
                    self.stream.source.subscribe([target])"""

replacement_fallback = """                if not self.target_symbol:
                    self.target_symbol = "^NSEI"
                target = self.target_symbol
                if hasattr(self.stream, "source") and hasattr(self.stream.source, "subscribe"):
                    self.stream.source.subscribe([target])"""
content = content.replace(target_fallback, replacement_fallback)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
