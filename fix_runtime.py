import re

path = 'titan/runtime/runtime.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix start() to not catch exceptions and hide them using 'from exc' if it means they die silently? Wait, the prompt says "REMOVE any try...except: pass blocks inside _start_stream or start. If the stream fails to start, log the exact traceback to tui_ipc_debug.log so we can see it, but do not let it die silently."

start_stream_code = """    def _start_stream(self) -> None:
        \"\"\"Start the market data stream.\"\"\"
        if self.stream is not None:
            try:
                if hasattr(self.stream.source, "subscribe"):
                    self.stream.source.subscribe([self.target_symbol or "RELIANCE"])
                self.stream.start()
                self.health.report_healthy("stream")
            except Exception as e:
                import traceback
                with open("tui_ipc_debug.log", "a") as f:
                    f.write(f"Stream Start Error: {traceback.format_exc()}\\n")
                self.health.report_unhealthy("stream", error=str(e))
                raise"""

content = re.sub(r"    def _start_stream\(self\) -> None:[\s\S]*?(?=\n    def _stop_stream)", start_stream_code, content)


# Fix start() to also log tracebacks just in case
start_code = """    def start(self) -> None:
        \"\"\"Start the runtime engine and all components.\"\"\"
        if self._status in (RuntimeStatus.RUNNING, RuntimeStatus.STARTING):
            raise RuntimeError("Runtime is already running.")
        if self._status == RuntimeStatus.PAUSED:
            raise RuntimeError("Runtime is paused. Use resume() to continue.")

        self._status = RuntimeStatus.STARTING
        self._error = ""
        self._start_time = datetime.now(UTC)
        self._stop_event.clear()

        try:
            self._validate_configuration()
            self._validate_environment()
            self._validate_storage()
            self._validate_trade_journal()
            self._validate_decision_journal()
            self._start_recovery()
            self._start_supervisor()
            self._start_scheduler()
            self._start_broker()
            self._start_stream()
            self._start_monitoring()

            self._status = RuntimeStatus.RUNNING
            self.health.report_healthy("runtime")

            self.event_bus.publish_type(
                RuntimeEventType.RUNTIME_STARTED,
                "runtime",
                data={"start_time": self._start_time.isoformat()},
            )

        except Exception as exc:
            import traceback
            with open("tui_ipc_debug.log", "a") as f:
                f.write(f"Runtime Start Error: {traceback.format_exc()}\\n")
            self._status = RuntimeStatus.ERROR
            self._error = str(exc)
            self.health.report_unhealthy("runtime", error=str(exc))
            self.event_bus.publish_type(
                RuntimeEventType.RUNTIME_ERROR,
                "runtime",
                data={"error": str(exc)},
            )
            self._shutdown_components()
            raise RuntimeError(f"Failed to start runtime: {exc}") from exc"""

content = re.sub(r"    def start\(self\) -> None:[\s\S]*?(?=\n    def run_until_stopped)", start_code, content)


# Fix _pipeline_runner
pipeline_code = """    def _pipeline_runner(self, quote=None) -> Any:
        \"\"\"Default pipeline runner for the scheduler.\"\"\"
        self.supervisor.evaluate()
        self.supervisor.touch("pipeline")
        self.supervisor.touch("scheduler")
        self.supervisor.touch("broker")
        self.supervisor.touch("event_bus")

        self._pipeline_executions += 1
        exchanges = self.broker.profile().enabled_exchanges
        exchange_val = exchanges[0] if exchanges else Exchange.NSE
        symbol = self.target_symbol or "RELIANCE"
        
        market_data = None
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
            
        report = self.pipeline.run(symbol=symbol, exchange=exchange_val, market_data=market_data)
        
        self.supervisor.record_pipeline_execution(
            success=True,
            duration=0.01,
        )
        return report"""

content = re.sub(r"    def _pipeline_runner\(self\) -> Any:[\s\S]*?(?=\n    def _validate_configuration)", pipeline_code, content)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

