import logging
import sys
import time
from unittest.mock import MagicMock

from titan.cli.common import create_runtime_engine

# Keep logs to INFO to avoid the massive YFinance debug spam
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

print("\n=== FINAL PIPELINE IGNITION ===")
try:
    mock_config = MagicMock()
    mock_config.broker.provider = "paper"
    mock_config.broker.paper_initial_cash = 1000000
    mock_config.trading.mode = "paper"

    engine = create_runtime_engine(mock_config)
    engine.target_symbol = "^NSEI"

    print(f"[1] Engine Built. Target: {engine.target_symbol}")
    print("[2] Starting Engine...")
    engine.start()

    print("[3] Waiting 30s for YFinance background poll & pipeline execution...")
    for i in range(7):
        time.sleep(5)
        
        # Safely extract internal state
        conn = getattr(engine.stream, "connected", getattr(engine.stream, "is_connected", False))
        syms = getattr(engine.stream, "symbols", [])
        
        # Safely extract pipeline executions
        execs = getattr(engine, "_pipeline_executions", 0)
        
        print(f"    [{i*5}s] Stream Connected: {conn} | Symbols: {syms} | Pipeline Executions: {execs}")

except Exception:
    import traceback
    print("\n[!] CRASH CAUGHT:")
    traceback.print_exc()
finally:
    print("\n[4] Shutting down...")
    try:
        engine.stop()
    except:
        pass
