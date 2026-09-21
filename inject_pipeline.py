import os
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

from titan.brokers.models import Exchange, Quote
from titan.cli.common import create_runtime_engine

if os.path.exists("pipeline_crash.log"):
    os.remove("pipeline_crash.log")

mock_config = MagicMock()
mock_config.broker.provider = "paper"
mock_config.broker.paper_initial_cash = 1000000
mock_config.trading.mode = "paper"

engine = create_runtime_engine(mock_config)
engine.target_symbol = "^NSEI"

# Build a valid Quote using the correct broker model import
quote = Quote(
    symbol="^NSEI", 
    exchange=Exchange.NSE, 
    last_price=Decimal(25000), 
    timestamp=datetime.now(UTC)
)

print("\n=== PIPELINE INJECTION X-RAY ===")
print("[1] Forcing Quote into _pipeline_runner...")
engine._pipeline_runner(quote)

print(f"[2] Executions Registered: {getattr(engine, '_pipeline_executions', 0)}")

if os.path.exists("pipeline_crash.log"):
    print("\n[!] GHOST CAUGHT! Printing pipeline_crash.log:\n")
    with open("pipeline_crash.log", "r") as f:
        print(f.read())
else:
    print("\n[?] Pipeline survived injection without crashing.")
