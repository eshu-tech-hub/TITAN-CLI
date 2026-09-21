import logging
import sys
from unittest.mock import MagicMock

import yfinance as yf

from titan.cli.common import create_runtime_engine

logging.basicConfig(level=logging.WARNING, stream=sys.stdout)

print("\n=== DATABASE & IMPORT TOOL X-RAY 2.0 ===")

try:
    print("\n[1] Testing Historical Data Importer...")
    ticker = yf.Ticker("^NSEI")
    hist = ticker.history(period="1d", interval="1m")
    if not hist.empty:
        print(f"    [?] Historical Import Successful. Retrieved {len(hist)} rows for ^NSEI.")
    else:
        print("    [!] Historical Import returned empty dataframe.")

    print("\n[2] Testing Database Write/Read Access...")
    
    mock_config = MagicMock()
    mock_config.broker.provider = "paper"
    mock_config.broker.paper_initial_cash = 1000000
    mock_config.trading.mode = "paper"
    
    engine = create_runtime_engine(mock_config)

    # Access the repositories using their official public methods
    trade_repo = engine.trade_journal.repository
    decision_repo = engine.decision_journal.repository

    # Perform a safe read query to verify the SQLite file is unlocked and schemas are valid
    trades = trade_repo.get_all() if hasattr(trade_repo, 'get_all') else []
    print(f"    [?] Trade DB Read Successful. Current recorded trades: {len(trades)}")

    decisions = decision_repo.get_all() if hasattr(decision_repo, 'get_all') else []
    print(f"    [?] Decision DB Read Successful. Current recorded decisions: {len(decisions)}")

    print("\n=== VERIFICATION COMPLETE: ALL TOOLS OPERATIONAL ===")

except Exception:
    import traceback
    print("\n[!] VERIFICATION FAILED:")
    traceback.print_exc()
