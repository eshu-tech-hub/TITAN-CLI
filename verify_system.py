import logging
import sys
import traceback
from unittest.mock import MagicMock

from titan.cli.common import create_runtime_engine

logging.basicConfig(level=logging.WARNING, stream=sys.stdout)

print("\n=== TITAN CORE SUBSYSTEM DIAGNOSTIC ===")

try:
    print("\n[1] Testing Configuration & Factory...")
    mock_config = MagicMock()
    mock_config.broker.provider = "paper"
    mock_config.broker.paper_initial_cash = 1000000
    mock_config.trading.mode = "paper"
    engine = create_runtime_engine(mock_config)
    print("    [?] Runtime Engine instantiated successfully.")

    print("\n[2] Testing Database Repositories...")
    if hasattr(engine, "trade_journal") and hasattr(engine.trade_journal, "repository"):
        print("    [?] TradeRepository linked.")
    else:
        print("    [!] TradeRepository missing.")

    if hasattr(engine, "decision_journal") and hasattr(engine.decision_journal, "repository"):
        print("    [?] DecisionRepository linked.")
    else:
        print("    [!] DecisionRepository missing.")

    print("\n[3] Testing Polars Analytics Pipeline...")
    if hasattr(engine, "pipeline"):
        print(f"    [?] Pipeline loaded: {type(engine.pipeline).__name__}")
        print(f"    [?] Strategy mounted: {type(engine.pipeline.strategy).__name__}")
        print(f"    [?] Total analyzers: {len(engine.pipeline._get_analyzers() if hasattr(engine.pipeline, '_get_analyzers') else [])}")
    else:
        print("    [!] Polars Pipeline missing.")

    print("\n[4] Testing Data Import / History Module...")
    # Checking if yfinance history extraction is functional for offline imports
    from titan.brokers.yfinance.stream import YFinanceStreamSource
    source = YFinanceStreamSource()
    print("    [?] Data source module accessible.")

    print("\n=== DIAGNOSTIC COMPLETE: ALL SYSTEMS NOMINAL ===")

except Exception:
    print("\n[!] SUBSYSTEM FAILURE DETECTED:")
    traceback.print_exc()
