# ADR-024: Backtesting Engine

**Status:** Accepted (Milestone M6.3)

**Date:** 2026-07-07

**Author:** TITAN Architecture Team

## Context

TITAN's Trade Pipeline (ADR-022) orchestrates the complete trading workflow from
market data to broker execution. The Paper Trading Engine (ADR-023) provides a
broker-independent simulation layer for the `Broker` interface.

Before this ADR:

- There was no way to test strategies against historical data through the full
  TITAN pipeline.
- Strategy evaluation required live market data or manual simulation.
- There was no integrated replay engine, statistics engine, or performance
  metrics engine tied to the pipeline.
- Walk-forward analysis, Monte Carlo simulation, and parameter optimization
  had no foundation to build upon.

## Decision

We introduce `titan/backtesting/` with the following architecture:

### HistoricalDataset

A validated container for historical OHLCV bars with support for optional
option chain snapshots, news snapshots, and event snapshots indexed by
timestamp. Validates prices, volumes, and chronological ordering on
construction. Provides conversion between broker-layer `Candle` (Decimal)
and internal `HistoricalBar` (Decimal for precision).

### SimulationClock

Controls time progression during a backtest. Supports pause, resume, seek,
next bar, previous bar, and progress tracking. Maintains no reference to
market data — purely a time-index controller.

### ReplayEngine

Wraps `HistoricalDataset` and `SimulationClock` to provide chronological
data access. Exposes `start()`, `advance()`, `seek()`, and `reset()` methods.
Converts historical data into `MarketDataSeries` for the pipeline and
`Decimal` prices for the `PaperBroker`. No look-ahead bias by construction
— only the current and past bars are visible.

### BacktestEngine

Orchestrates the full backtest loop:

1. Creates a `ReplayEngine` from the dataset
2. Connects the `PaperBroker`
3. For each bar: sets the broker price, creates market data, runs the
   `TradePipeline`, collects the `PipelineReport`, snapshots portfolio state
4. After all bars: computes statistics and metrics
5. Returns a `BacktestReport`

The `BacktestEngine` accepts dependency injection for pipeline, broker, clock,
statistics engine, and metrics engine. All components have sensible defaults.

### StatisticsEngine

Computes trading statistics from a stream of P&L values:
- Win/loss counts and rates
- Profit factor
- Expectancy
- Average win/loss
- Maximum consecutive wins/losses
- Maximum drawdown
- Recovery factor

### MetricsEngine

Computes performance metrics from the equity curve:
- Daily, monthly, and annualized return
- Volatility (annualized)
- Sharpe ratio (annualized return - risk-free rate / volatility)
- Sortino ratio (annualized return - risk-free rate / downside volatility)
- Calmar ratio (annualized return / max drawdown)
- MAR ratio (CAGR / max drawdown)

Placeholder implementations are acceptable — the engine returns 0.0 for
metrics that cannot be computed from available data.

### Reports

`BacktestReport` is a frozen dataclass containing:
- Backtest identity and status
- Dataset summary (symbol, exchange, bars processed)
- Portfolio summary (start/end equity, P&L, return)
- `BacktestStatistics`
- `BacktestMetrics`
- Equity curve as a sequence of `EquityPoint` snapshots
- Pipeline reports from each bar
- Warnings and errors

### Evidence and Explanation

`generate_evidence()` produces an `Evidence` item with
`EvidenceCategory.SYSTEM` and metadata about the backtest run.

`generate_explanation()` produces a `BacktestExplanation` with sections
for dataset, simulation, performance, risk, portfolio, and summary.

## Key Design Decisions

1. **No duplicate trading logic.** The backtest engine reuses the existing
   `TradePipeline`, `ExecutionOrchestrator`, and `PaperBroker`. No order
   routing, fill simulation, or position tracking logic exists in the
   backtesting module.

2. **Deterministic replay.** The `ReplayEngine` exposes bars in strict
   chronological order. The `SimulationClock` prevents out-of-order access.
   No future data is ever visible to the pipeline.

3. **Dependency injection.** Every component can be replaced for testing
   or customization. The `BacktestEngine` accepts custom pipeline, broker,
   clock, statistics, and metrics implementations.

4. **Frozen dataclasses.** All models use `frozen=True` and `slots=True`
   for immutability and memory efficiency.

5. **Decimal precision.** Historical data is stored with `Decimal` prices
   for precision. Conversion to `float` happens only at the pipeline
   boundary where `MarketDataSeries` expects float values.

6. **Timezone-aware timestamps.** All timestamps use
   `datetime(timezone.utc)` throughout.

## Consequences

### Positive

- Strategies can be tested against historical data through the full TITAN
  pipeline without modification.
- Backtest results are directly comparable to live trading since the same
  pipeline and broker interfaces are used.
- No look-ahead bias by construction — the replay engine only exposes
  current and past bars.
- Future features (walk-forward, Monte Carlo, optimization) can build on
  the existing architecture without redesign.

### Negative

- Current backtests are single-symbol, single-timeframe. Multi-symbol and
  multi-timeframe support require additional orchestration.
- The `TradePipeline` is designed for single-bar analysis — some strategy
  patterns that require multi-bar state may need custom pipeline handlers.

### Neutral

- The metrics engine uses placeholder implementations for advanced metrics
  that require risk-free rate data or higher-frequency return data.
- The statistics engine tracks trades by P&L values recorded externally —
  integration with the `TradeJournal` for automated trade capture is
  future work.

## Future Work

- Walk-forward analysis engine
- Monte Carlo simulation engine
- Parameter optimization framework
- Multi-symbol portfolio backtesting
- Multi-timeframe backtesting
- Distributed backtesting execution
- Cloud-based backtesting
- Automated trade capture from `TradeJournal`
- Integration with the Decision Engine for strategy evaluation
