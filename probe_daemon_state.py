import time
from unittest.mock import MagicMock

from titan.cli.common import create_runtime_engine

mock_config = MagicMock()
mock_config.broker.provider = "paper"
mock_config.broker.paper_initial_cash = 1000000
mock_config.trading.mode = "paper"

engine = create_runtime_engine(mock_config)
engine.target_symbol = "^NSEI"

print("[1] Starting engine...")
engine.start()
time.sleep(2)

print("\n=== ENGINE STATE REPORT ===")
print(f"Engine target_symbol: {engine.target_symbol}")
print(f"Engine stream object: {engine.stream}")
if engine.stream:
    print(f"  - stream.connected: {getattr(engine.stream, 'connected', 'MISSING')}")
    print(f"  - stream.is_connected: {getattr(engine.stream, 'is_connected', 'MISSING')}")
    print(f"  - stream.symbols: {getattr(engine.stream, 'symbols', 'MISSING')}")
    print(f"  - stream.subscribed_symbols: {getattr(engine.stream, 'subscribed_symbols', 'MISSING')}")

print(f"\nRuntime Stats dictionary: {engine.get_runtime_stats()}")

engine.stop()
print("[2] Test complete.")
