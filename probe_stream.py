from titan.brokers.yfinance.stream import YFinanceStreamSource
from titan.runtime.stream import MarketStream

source = YFinanceStreamSource()
stream = MarketStream(source=source)

print("\n=== STREAM OBJECT X-RAY ===")
print(f"[1] Source has subscribe? {hasattr(source, 'subscribe')}")
source.subscribe(["^NSEI"])

print(f"[2] Source memory dictionary:\n{source.__dict__}")
print(f"[3] Wrapper 'subscribed_symbols' property: {getattr(stream, 'subscribed_symbols', 'MISSING')}")

print("\n[Starting Stream...]")
stream.start()
print(f"[4] Source memory dictionary after start:\n{source.__dict__}")
print(f"[5] Wrapper 'is_connected' property: {getattr(stream, 'is_connected', 'MISSING')}")
stream.stop()
