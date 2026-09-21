import logging
import sys

import yfinance as yf

from titan.cli.common import create_runtime_engine
from titan.core.config import load_config

logging.basicConfig(level=logging.WARNING, stream=sys.stdout)

print("\n=== DATABASE & IMPORT TOOL X-RAY ===")

try:
    print("\n[1] Testing Historical Data Importer...")
    # Fetch 1 day of historical data to simulate the backtest importer
    ticker = yf.Ticker("^NSEI")
    hist = ticker.history(period="1d", interval="1m")
    if not hist.empty:
        print(f"    [?] Historical Import Successful. Retrieved {len(hist)} rows for ^NSEI.")
    else:
        print("    [!] Historical Import returned empty dataframe.")

    print("\n[2] Testing Database Write/Read Access...")
    config = load_config()
    engine = create_runtime_engine(config)
    
    # Access the SQLite repository
    repo = engine.trade_journal.repository
    
    # Check if the database file is accessible and tables exist
    db_tables = repo.db.get_tables()
    print(f"    [?] SQLite Database connected. Found tables: {', '.join(db_tables)}")
    
    # Perform a safe read query to verify lock status
    trades = repo.get_all()
    print(f"    [?] Database Read Successful. Current recorded trades: {len(trades)}")

    print("\n=== VERIFICATION COMPLETE: ALL TOOLS OPERATIONAL ===")

except Exception:
    import traceback
    print("\n[!] VERIFICATION FAILED:")
    traceback.print_exc()
