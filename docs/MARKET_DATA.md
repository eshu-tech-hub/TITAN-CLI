# Market Data Foundation

## Architecture

The market data layer is the broker-independent boundary for TITAN OS. Broker
adapters and external data vendors implement `MarketDataProvider`; application
modules consume `MarketDataService` and normalized domain models.

This keeps analysis, risk, execution, AI, backtesting, option chains, and news
workflows independent from any one broker API shape.

## Responsibilities

- `MarketDataProvider`: abstract adapter contract for external data sources.
- `MarketDataService`: application service that validates requests, calls a
  provider, validates returned candles, and returns `MarketDataSeries`.
- `Symbol`: broker-independent instrument identity.
- `Candle`: normalized historical OHLCV candle.
- `Timeframe`: canonical candle interval enum used across TITAN.
- `validator.py`: domain validation for symbols, timeframes, requests, and
  provider responses.
- `exceptions.py`: market-specific exception hierarchy.

## Class Diagram

```text
+--------------------+        +----------------------+
| MarketDataService  |------->| MarketDataProvider   |
|--------------------|        |----------------------|
| +get_historical... |        | +get_historical...   |
+---------+----------+        +----------+-----------+
          |                              ^
          |                              |
          v                              |
+--------------------+        +----------------------+
| MarketDataSeries   |        | Broker/Vendor Adapter|
|--------------------|        |----------------------|
| candles: list      |        | normalizes raw API   |
+---------+----------+        | responses            |
          |                   +----------------------+
          v
+--------------------+        +----------------------+
| Candle             |        | Symbol               |
|--------------------|        |----------------------|
| timestamp          |        | exchange             |
| open/high/low/...  |        | ticker               |
+--------------------+        +----------------------+
```

## Future Extensions

- Add quote, tick, market depth, option chain, and corporate action provider
  interfaces without changing existing consumers.
- Add provider capability discovery for supported exchanges and intervals.
- Add caching and retry policies around `MarketDataService`.
- Add streaming market data using a separate provider contract.
- Add symbol search and instrument master synchronization.

## Integration Rule

TITAN modules should depend on `MarketDataService` or market domain models, not
directly on broker clients. Broker-specific code belongs behind
`MarketDataProvider` implementations.


## TUI Integration

The Market Intelligence Screen in the TITAN TUI provides a read-only operational dashboard visualizing the output of this engine/component. No business logic or analytics are executed in the presentation layer.
