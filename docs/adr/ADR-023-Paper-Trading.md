# ADR-023: Paper Trading Engine

**Status:** Accepted (Milestone M6.2)

**Date:** 2026-07-04

**Author:** TITAN Architecture Team

## Context

TITAN's Trade Pipeline (ADR-022) orchestrates the complete trading workflow from
market data to broker execution. The Execution Orchestrator (ADR-021) submits
orders through a `Broker` abstraction (ADR-017). Currently, the only concrete
broker implementation is YFinance (ADR-019), which requires network access and
a live yfinance account.

Before this ADR:

- There was no way to test the full trading pipeline without a live broker
  connection.
- Strategy development required risking real capital or complex mock setups.
- There was no trade journal, position tracker, or performance analytics
  integrated with the pipeline for simulation purposes.
- No deterministic fill simulation existed for offline testing.

## Decision

We introduce `titan/paper/` with the following architecture:

### PaperBroker

`PaperBroker` implements the full `Broker` ABC from `titan/brokers/broker.py`,
making it a drop-in replacement for any live broker (YFinanceBroker, etc.).
Upstream code (Trade Pipeline, Execution Orchestrator, Decision Engine) does
not need to change.

### Internal Architecture

```
PaperBroker
  ├── FillEngine       — Deterministic order fill simulation
  ├── PositionEngine   — Open position tracking with P&L, MFE, MAE
  ├── PaperPortfolio   — Cash, equity, buying power, drawdown
  ├── TradeJournal     — Chronological event log with full audit trail
  └── PerformanceEngine — Win rate, profit factor, expectancy, etc.
```

Every sub-engine is injectable via the constructor for testing.

### Fill Simulation

- **Market orders:** Fill immediately at the current simulated price.
- **Limit orders:** Fill only when the limit price is achievable (buy: limit >=
  ask; sell: limit <= bid).
- **Stop orders:** Convert to market fills when the trigger price is crossed.
- **Slippage:** Pluggable via `SlippageModel` callable (default: 0.1%).
- **Latency:** Pluggable via `LatencyModel` callable (default: 50ms).
- **Commission:** Flat fee (10) + percentage (0.01%) of trade value.

### Position Tracking

- Weighted average entry price.
- Realized and unrealized P&L.
- Maximum Favorable Excursion (MFE) and Maximum Adverse Excursion (MAE).
- Full close detection and position cleanup.

### Portfolio

- Initial cash balance (configurable, default 100,000).
- Cash debited on buys, credited on sells.
- Equity computed as cash + position market value.
- Drawdown tracking from peak equity.
- Daily P&L tracker.

### Trade Journal

- Every order, fill, modification, cancellation, and position change is
  recorded with a UTC timestamp.
- Orders can be looked up by internal ID or broker-assigned ID.
- Filtered queries by symbol and time range.

### Performance Metrics

- Win rate, loss rate, profit factor, expectancy.
- Average winner, average loser, average holding time.
- Sharpe and Sortino ratio placeholders (return 0.0).

### Reports

- `PaperTradingReport`: Aggregates orders, trades, positions, portfolio state,
  and performance metrics in a single frozen dataclass.
- `PaperTradingExplanation`: Human-readable sections for execution, portfolio,
  performance, open/closed positions, and a one-line summary.
- Evidence generation: Produces `EvidenceCategory.EXECUTION` evidence with
  metadata about paper execution, simulation mode, fill quality, and latency.

### BrokerType

`BrokerType.PAPER` ("paper") added to the broker enum for factory registration.

## Consequences

### Positive

1. **Full pipeline testing offline.** The Trade Pipeline can be configured with
   PaperBroker and run without network, API keys, or live accounts.
2. **Interchangeable.** PaperBroker implements the same `Broker` interface as
   live brokers; swap via `BrokerFactory` or constructor injection.
3. **Deterministic fills.** Market, limit, and stop orders fill according to
   simple, predictable rules — ideal for unit and integration tests.
4. **Complete audit trail.** Every event is journaled with timestamps for
   post-trade analysis and debugging.
5. **Performance analytics.** Win rate, profit factor, and other metrics are
   computed automatically from journal data.
6. **Extensible.** Slippage and latency models are pluggable callables; future
   backtesting, walk-forward, and multi-broker simulation can reuse the same
   architecture.

### Negative

1. **No market simulation.** PaperBroker does not simulate price movement,
   volatility, or order book dynamics. Prices must be set manually via
   `set_price()`.
2. **No historical replay.** FillEngine only supports current-price fills.
   Historical replay requires a separate engine (future work).
3. **Deterministic fills only.** Partial fills, iceberging, and smart order
   routing are not simulated.

### Neutral

1. **BrokerType enum extended.** A new `PAPER` value was added. Existing
   broker registrations are unaffected.

## Future Work

- Historical replay engine for backtesting.
- Walk-forward analysis harness.
- Multi-broker and multi-account simulation.
- Probabilistic fill models with partial fills.
- Distributed simulation across multiple processes.
