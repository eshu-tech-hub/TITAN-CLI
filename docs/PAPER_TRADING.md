# Paper Trading Engine

## Overview

The Paper Trading Engine (`titan/paper/`) is a broker-independent simulation
layer that executes the complete TITAN trading workflow without sending orders
to a live broker. It implements the same `Broker` interface as live adapters,
making it a drop-in replacement for testing, strategy development, and
pipeline validation.

## Architecture

```
Trade Pipeline → Execution Orchestrator → PaperBroker
                                            ├── FillEngine
                                            ├── PositionEngine
                                            ├── PaperPortfolio
                                            ├── TradeJournal
                                            └── PerformanceEngine
```

All components communicate through the `Broker` ABC. No network, no API keys,
no external dependencies.

## Quick Start

### Python API

```python
from decimal import Decimal
from titan.paper import PaperBroker
from titan.brokers.models import (
    OrderRequest, OrderSide, OrderType, Exchange,
)

# Create and connect
broker = PaperBroker(initial_cash=Decimal("100000"))
broker.connect()

# Set a simulated price
broker.set_price("RELIANCE", Decimal("2500.00"))

# Place a market buy order
request = OrderRequest(
    symbol="RELIANCE",
    exchange=Exchange.NSE,
    side=OrderSide.BUY,
    order_type=OrderType.MARKET,
    quantity=10,
)
response = broker.place_order(request)
print(f"Filled: {response.filled_quantity} @ {response.average_price}")

# Check positions and funds
positions = broker.positions()
funds = broker.funds()
```

### CLI Lifecycle

```bash
# Start a paper trading session
titan paper start --verbose

# Check session status
titan paper status
titan paper status --json
titan paper status --verbose

# Generate a report
titan paper report
titan paper report --json
titan paper report --verbose
titan paper report --export report.json
titan paper report --export report.csv

# Stop the session
titan paper stop --verbose

# Restart with new cash
titan paper restart --cash 200000

# Reset all state
titan paper reset
```

## Constructor Options

| Parameter       | Default              | Description                       |
|-----------------|----------------------|-----------------------------------|
| `initial_cash`  | `Decimal("100000")`  | Starting cash balance             |
| `fill_engine`   | `FillEngine()`       | Custom fill simulation engine     |
| `position_engine` | `PositionEngine()` | Custom position tracker           |
| `portfolio`     | `PaperPortfolio()`   | Custom portfolio tracker          |
| `journal`       | `TradeJournal()`     | Custom trade journal              |
| `performance`   | `PerformanceEngine()`| Custom performance engine         |

## Fill Engine

The `FillEngine` determines whether an order fills and at what price:

- **Market orders:** Fill immediately at the simulated quote price.
- **Limit orders:** Fill only when the limit price is achievable.
- **Stop orders:** Convert to market fills when the trigger price is crossed.

### Custom Slippage and Latency

```python
from decimal import Decimal
from titan.paper.fills import FillEngine
from titan.brokers.models import OrderRequest, Quote

def my_slippage(request: OrderRequest, quote: Quote) -> Decimal:
    return quote.last_price * Decimal("0.0005")  # 0.05%

engine = FillEngine(slippage_model=my_slippage)
```

## Managed Methods

PaperBroker implements all 21 abstract methods of the `Broker` ABC:

| Category             | Method                          | Behaviour                     |
|----------------------|---------------------------------|-------------------------------|
| Connection           | `connect()`                     | Sets connected state          |
| Connection           | `disconnect()`                  | Clears connected state        |
| Connection           | `is_connected()`                | Returns connection flag       |
| Market Data          | `quote()`                       | Simulated quote at set price  |
| Market Data          | `quotes()`                      | Batch simulated quotes        |
| Market Data          | `option_chain()`                | Returns empty list            |
| Market Data          | `market_depth()`                | Simulated 5-level depth       |
| Market Data          | `ltp()`                         | Returns set price             |
| Historical Data      | `history()`                     | Returns empty list            |
| Historical Data      | `intraday()`                    | Returns empty list            |
| Historical Data      | `ohlcv()`                       | Returns empty list            |
| Order Management     | `place_order()`                 | Simulates fill + track        |
| Order Management     | `modify_order()`                | Updates pending order         |
| Order Management     | `cancel_order()`                | Cancels pending order         |
| Order Management     | `order()`                       | Looks up by broker ID         |
| Order Management     | `orders()`                      | Filtered order list           |
| Portfolio            | `positions()`                   | From PositionEngine           |
| Portfolio            | `holdings()`                    | From PositionEngine           |
| Portfolio            | `trades()`                      | From TradeJournal             |
| Account              | `funds()`                       | From PaperPortfolio           |
| Account              | `margin()`                      | From PaperPortfolio           |
| Account              | `profile()`                     | Simulated profile             |

## Reports

### PaperTradingReport

```python
from titan.paper import PaperTradingReport, generate_evidence, generate_explanation

report = PaperTradingReport(orders=..., trades=..., portfolio_state=...)
evidence = generate_evidence(report)
explanation = generate_explanation(report)
```

## Integration with Pipeline

```python
from titan.paper import PaperBroker
from titan.execution import ExecutionOrchestrator
from titan.pipeline import TradePipeline

broker = PaperBroker(initial_cash=Decimal("100000"))
orchestrator = ExecutionOrchestrator(broker=broker, ...)
pipeline = TradePipeline(orchestrator=orchestrator, ...)
```

## Future Compatibility

The architecture supports without redesign:
- Historical replay via a price feed that provides historical candles
- Walk-forward testing by resetting state between windows
- Multi-broker simulation by creating multiple PaperBroker instances
- Multi-account simulation by sharing a FillEngine across instances
- Distributed simulation via serialisable PaperTradingReport

## Testing

The paper trading module includes 108+ tests covering:

- FillEngine: market, limit, stop, slippage, latency, commission
- PositionEngine: open, close, reduce, multiple symbols, broker conversion
- PaperPortfolio: cash, equity, drawdown, funds/margin conversion
- TradeJournal: record, fill, modify, cancel, filter, reset
- PerformanceEngine: metrics computation
- PaperBroker: full Broker interface compliance
- Evidence generation
- Serialization
- Error handling and exception hierarchy

## TUI Screen

The Paper Trading TUI screen (`titan/tui/screens/paper.py`) provides real-time monitoring of a live paper trading session.

### Navigation

Press `F3` from the Dashboard to switch to the Paper Trading screen. Press `escape` to return to the Dashboard.

### Widgets

| Widget | Data | Refresh |
|--------|------|---------|
| `PaperSessionWidget` | Status, uptime, mode | Auto |
| `AccountSummaryWidget` | Cash, margin, payin/payout | Auto |
| `PortfolioWidget` | Cash, equity, unrealized/realized P&L | Auto |
| `PositionWidget` | Open positions (dynamic) | Auto |
| `ActiveOrdersWidget` | Pending/open orders (dynamic) | Auto |
| `PerformanceWidget` | Win rate, profit factor, expectancy, max drawdown | Auto |
| `TradeHistoryWidget` | Last 20 closed trades (dynamic) | Auto |

### State Builder

`build_paper_state()` in `layout.py` reads the `PaperBroker` singleton via `_get_broker()`. All access is `try/except` guarded — if no session is active, widgets render defaults.

### Testing

129 tests in `tests/test_tui_paper.py` cover models, widgets, state builders, and screen bindings.


## Architecture

For technical details on how the runtime is managed in the background, see [Runtime Service Architecture](RUNTIME_SERVICE.md).
