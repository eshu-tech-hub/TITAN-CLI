import logging
import time
from unittest.mock import MagicMock

from titan.cli.common import create_runtime_engine

# Suppress the massive YFinance debug walls, keep warnings/errors
logging.getLogger("yfinance").setLevel(logging.WARNING)
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")

print("\n=== TITAN HEADLESS MATRIX ===")
try:
    # 1. Build the configuration safely
    mock_config = MagicMock()
    mock_config.broker.provider = "paper"
    mock_config.broker.paper_initial_cash = 1000000
    mock_config.trading.mode = "paper"

    # 2. Build Engine & Lock Symbol
    engine = create_runtime_engine(mock_config)
    engine.target_symbol = "^NSEI"

    print(f"[*] Engine Built. Target: {engine.target_symbol}")
    print("[*] Igniting Background Threads...")
    engine.start()

    print("\n[      LIVE TELEMETRY FEED      ]")
    print("-" * 35)
    
    # 3. Stream live telemetry to the terminal for 60 seconds
    for i in range(13):
        time.sleep(5)
        
        # Safely extract state
        conn = getattr(engine.stream, "connected", getattr(engine.stream, "is_connected", False))
        syms = getattr(engine.stream, "symbols", getattr(engine.stream, "subscribed_symbols", []))
        execs = getattr(engine, "_pipeline_executions", 0)
        
        # Format the output
        status = "?? ONLINE " if conn else "?? OFFLINE"
        print(f"[{i*5:02}s] {status} | Executions: {execs}")

except KeyboardInterrupt:
    print("\n[!] Manual shutdown triggered.")
except Exception:
    import traceback
    print("\n[!] CRASH CAUGHT:")
    traceback.print_exc()
finally:
    print("\n[*] Shutting down engine...")
    try:
        engine.stop()
    except:
        pass
    print("=== SESSION ENDED ===")
