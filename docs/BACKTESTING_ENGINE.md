# Backtesting Engine

## Overview

The Backtesting Engine (`titan/backtesting/`) replays historical market data
through the complete TITAN pipeline. It reuses the existing Trade Pipeline,
Decision Engine, Execution Orchestrator, and Paper Trading Engine — no
duplicate trading logic.

Every backtest runs through the same `Broker` interface as live trading,
ensuring that backtest results accurately represent real-world execution.

## Architecture

```
HistoricalDataset
      ↓
  ReplayEngine ──→ SimulationClock
      ↓
 TradePipeline ──→ ExecutionOrchestrator ──→ PaperBroker
      ↓                                         ├── FillEngine
  Collect Results                                ├── PositionEngine
      ↓                                         ├── PaperPortfolio
  StatisticsEngine  MetricsEngine                └── TradeJournal
      ↓
  BacktestReport
```

All components communicate through the existing TITAN interfaces. No network,
no API keys, no external dependencies.

## Quick Start

```python
from decimal import Decimal
from datetime import datetime, timezone
from titan.backtesting import (
    HistoricalDataset, BacktestEngine, HistoricalBar,
)
from titan.brokers.models import Exchange

# Create a dataset
bars = [
    HistoricalBar(
        timestamp=datetime(2026, 1, 1, 9, 15, tzinfo=timezone.utc),
        open=Decimal("100"), high=Decimal("105"),
        low=Decimal("95"),  close=Decimal("102"),
        volume=1000,
    ),
    HistoricalBar(
        timestamp=datetime(2026, 1, 1, 9, 16, tzinfo=timezone.utc),
        open=Decimal("102"), high=Decimal("108"),
        low=Decimal("101"), close=Decimal("107"),
        volume=1200,
    ),
]
dataset = HistoricalDataset(
    symbol="RELIANCE",
    exchange=Exchange.NSE,
    bars=bars,
)

# Run the backtest
engine = BacktestEngine(
    dataset=dataset,
    total_capital=Decimal("1000000"),
)
report = engine.run()

print(f"Bars processed: {report.bars_processed}")
print(f"Final equity:   {report.final_equity}")
print(f"Total P&L:      {report.total_pnl}")
print(f"Total trades:   {report.statistics.total_trades}")
print(f"Win rate:       {report.statistics.win_rate:.1%}")
print(f"Sharpe ratio:   {report.metrics.sharpe_ratio:.2f}")
```

## Creating a Dataset

### From OHLCV bars

```python
from titan.backtesting import HistoricalDataset, HistoricalBar
from titan.brokers.models import Exchange

dataset = HistoricalDataset(
    symbol="NIFTY",
    exchange=Exchange.NFO,
    bars=[...],  # list of HistoricalBar
)
```

### From broker Candle objects

```python
from titan.brokers.models import Candle
from decimal import Decimal

candles = [
    Candle(datetime=..., open=Decimal(...), high=Decimal(...),
           low=Decimal(...), close=Decimal(...), volume=...),
]
dataset = HistoricalDataset.from_broker_candles("NIFTY", Exchange.NFO, candles)
```

### Validation

The dataset validates:
- All prices are non-negative
- High >= Low for every bar
- Volume is non-negative
- Bars are in ascending chronological order

### Adding snapshots

```python
dataset.option_snapshots[timestamp] = [...]
dataset.news_snapshots[timestamp]   = [...]
dataset.event_snapshots[timestamp]  = [...]
```

## Running a Backtest

### Basic usage

```python
engine = BacktestEngine(dataset=dataset)
report = engine.run()
```

### Custom capital and broker

```python
from titan.paper import PaperBroker

broker = PaperBroker(initial_cash=Decimal("500000"))
engine = BacktestEngine(
    dataset=dataset,
    broker=broker,
    total_capital=Decimal("500000"),
)
report = engine.run()
```

### Custom pipeline injection

```python
from titan.pipeline.pipeline import TradePipeline
from titan.execution.orchestrator import ExecutionOrchestrator

orchestrator = ExecutionOrchestrator(
    planner=...,
    validator=...,
    allocator=...,
    oms=...,
    broker=paper_broker,
)
pipeline = TradePipeline(_orchestrator=orchestrator)
engine = BacktestEngine(dataset=dataset, pipeline=pipeline)
report = engine.run()
```

### Disable pipeline report collection

```python
engine = BacktestEngine(
    dataset=dataset,
    collect_pipeline_reports=False,
)
report = engine.run()
```

## BacktestReport Fields

| Field | Type | Description |
|---|---|---|
| `backtest_id` | `str` | Unique identifier |
| `symbol` | `str` | Traded symbol |
| `exchange` | `str` | Exchange code |
| `status` | `BacktestStatus` | PENDING / RUNNING / COMPLETED / FAILED / ABORTED |
| `bars_processed` | `int` | Number of bars replayed |
| `start_time` | `datetime` | Backtest start time |
| `end_time` | `datetime` | Backtest end time |
| `total_capital` | `Decimal` | Starting capital |
| `final_equity` | `Decimal` | Ending equity |
| `total_pnl` | `Decimal` | Net profit or loss |
| `total_return` | `Decimal` | Return ratio |
| `statistics` | `BacktestStatistics` | Trade statistics |
| `metrics` | `BacktestMetrics` | Performance metrics |
| `equity_curve` | `tuple[EquityPoint]` | Equity curve snapshots |
| `pipeline_reports` | `tuple[dict]` | Per-bar pipeline results |
| `warnings` | `tuple[str]` | Warnings |

## Statistics

| Metric | Description |
|---|---|
| `total_trades` | Total completed trades |
| `winning_trades` | Profitable trades |
| `losing_trades` | Unprofitable trades |
| `win_rate` | Win / total ratio |
| `profit_factor` | Gross profit / gross loss |
| `expectancy` | Average P&L per trade |
| `average_gain` | Average winning trade |
| `average_loss` | Average losing trade |
| `max_consecutive_wins` | Longest win streak |
| `max_consecutive_losses` | Longest loss streak |
| `max_drawdown` | Peak-to-trough decline |
| `recovery_factor` | Net profit / max drawdown |

## Metrics

| Metric | Description |
|---|---|
| `daily_return` | Average daily return |
| `monthly_return` | Average monthly return |
| `annualized_return` | Annualized return |
| `volatility` | Annualized volatility |
| `sharpe_ratio` | Risk-adjusted return |
| `sortino_ratio` | Downside risk-adjusted return |
| `calmar_ratio` | Return / max drawdown |
| `mar_ratio` | CAGR / max drawdown |

## Evidence

The engine generates `EvidenceCategory.SYSTEM` evidence with metadata
describing the backtest run, dataset, replay duration, and trade count.

## Explanation

The engine generates a `BacktestExplanation` with sections for dataset,
simulation, performance, risk, portfolio, and summary.

## Future Compatibility

The architecture supports without redesign:
- Walk-forward analysis
- Monte Carlo simulation
- Parameter optimization
- Multi-symbol testing
- Multi-timeframe testing
- Distributed execution
- Cloud backtesting

## CLI Usage

The backtesting engine is accessible through the TITAN CLI:

```bash
# Run a backtest from CSV data
titan backtest run RELIANCE nse --csv data.csv

# Run with custom capital and risk profile
titan backtest run RELIANCE nse --csv data.csv --capital 500000 --risk CONSERVATIVE

# Run with verbose progress display
titan backtest run RELIANCE nse --csv data.csv --verbose

# Check status
titan backtest status
titan backtest status --json

# View detailed report
titan backtest report
titan backtest report --json
titan backtest report --verbose
titan backtest report --export report.json
titan backtest report 1  # Specific backtest by index

# List all completed backtests
titan backtest list
titan backtest list --json
```

**CSV format**: `timestamp,open,high,low,close,volume` with ISO-8601 timestamps.

Example CSV:
```csv
timestamp,open,high,low,close,volume
2024-01-01T09:15:00+00:00,100,105,98,102,10000
2024-01-02T09:15:00+00:00,102,108,100,106,12000
```

## Testing

```bash
pytest tests/test_backtesting.py -v
```

The test suite covers:
- Replay engine: start, advance, seek, reset, market data conversion
- Simulation clock: initialize, pause, resume, seek, progress
- Dataset: validation, conversion, resampling
- Backtest engine: full pipeline integration, equity curve, reports
- Statistics: win/loss, profit factor, consecutive streaks, drawdown
- Metrics: Sharpe, Sortino, Calmar, MAR ratios
- Report generation: evidence, explanation, serialization
- No look-ahead bias: deterministic replay by construction
