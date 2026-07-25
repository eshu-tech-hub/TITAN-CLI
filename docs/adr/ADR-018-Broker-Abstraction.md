# ADR-018: Broker Abstraction Layer

**Status:** Accepted (Milestone M5.1)

**Date:** 2026-07-04

**Author:** TITAN Architecture Team

## Context

TITAN requires connectivity to external brokers for market data, order
execution, and portfolio management. Multiple brokers are supported
(Angel One, Zerodha, Dhan, Upstox, Interactive Brokers, Alpaca,
Binance), each with proprietary SDKs, authentication flows, data models,
and network protocols.

Prior to this ADR, broker integration was ad-hoc. The existing
`titan/broker/` (singular) package defined a minimal `Broker` ABC with
`login`, `logout`, `is_authenticated`, and `get_history` — insufficient
for the breadth of operations TITAN now requires (orders, positions,
holdings, trades, market depth, option chains, account management).

Without a comprehensive abstraction layer:
- Core TITAN modules risk depending directly on broker SDKs.
- Adding a new broker requires changes across the platform.
- Testing core logic requires live broker connectivity.
- The platform is coupled to specific broker data models.

## Decision

We introduce `titan/brokers/` (plural) — a pure abstraction package
that defines the complete contract between TITAN and any broker.

### Package Structure

```
titan/brokers/
    __init__.py       # Public API exports
    exceptions.py     # Domain exception hierarchy
    models.py         # Frozen dataclasses and enums
    broker.py         # ABC interfaces (5 providers + 1 composite)
    factory.py        # Registry-based factory
```

### Interfaces

Six abstract base classes:

1. **`MarketDataProvider`** — `quote()`, `quotes()`, `option_chain()`,
   `market_depth()`, `ltp()`
2. **`HistoricalDataProvider`** — `history()`, `intraday()`, `ohlcv()`
3. **`OrderProvider`** — `place_order()`, `modify_order()`,
   `cancel_order()`, `order()`, `orders()`
4. **`PortfolioProvider`** — `positions()`, `holdings()`, `trades()`
5. **`AccountProvider`** — `funds()`, `margin()`, `profile()`
6. **`Broker`** — Composite of all five providers + `connect()`,
   `disconnect()`, `is_connected()`

### Models

All models are frozen dataclasses with `slots=True`:

- **Enums:** `BrokerType`, `ConnectionStatus`, `OrderStatus`,
  `OrderSide`, `OrderType`, `ProductType`, `Validity`,
  `InstrumentType`, `Exchange`
- **Dataclasses:** `OrderRequest`, `OrderResponse`,
  `ModifyOrderRequest`, `CancelOrderRequest`, `Order`, `Position`,
  `Holding`, `Trade`, `Quote`, `MarketDepthLevel`, `MarketDepth`,
  `MarginInfo`, `FundsInfo`, `AccountProfile`, `Candle`

### Factory Pattern

`BrokerFactory` uses a registry pattern:

```python
factory = BrokerFactory()
factory.register(BrokerType.ZERODHA, ZerodhaBroker)
broker = factory.create(BrokerType.ZERODHA, api_key="...")
```

The factory enforces:
- Each `BrokerType` can be registered at most once.
- Registered classes must implement the `Broker` interface.
- `supported_brokers()` returns available types.

### Exception Hierarchy

```
BrokerError (base)
├── ConnectionError
├── AuthenticationError
├── OrderError
├── MarketDataError
└── ValidationError
```

### Strict Boundaries

The abstraction layer MUST NOT contain:
- HTTP requests or network logic
- Broker SDK imports (SmartAPI, etc.)
- API keys, tokens, or credentials
- Authentication or session management
- Any broker-specific implementation

### Relationship to Existing `titan/broker/`

The existing `titan/broker/` (singular) package and its Angel One
implementation are preserved as-is during this milestone. Future
milestones will migrate broker adapters from the old interface to
the new `titan/brokers/` abstraction.

## Alternatives Considered

### Protocol-Based Abstraction (Protocol/Structural Typing)

Using `typing.Protocol` instead of ABCs.

- *Rejected due to:* ABCs provide clearer intent, enforce method
  implementation at instantiation time, and are more discoverable
  in IDE tooling. Protocol compatibility is still possible for
  duck-typing consumers.

### Single Monolithic Broker Interface

A single ABC with all methods defined in one class.

- *Rejected due to:* Violates Interface Segregation Principle.
  Consumers that only need market data should not depend on order
  methods. The five-provider decomposition allows narrow interfaces.

### Configuration-Driven Factory

Factory that reads broker configuration from YAML/JSON and
auto-registers implementations.

- *Rejected due to:* Premature. The registry pattern keeps
  registration explicit. Configuration-driven registration can be
  added as a convenience wrapper later.

### Shared Mutable Models

Dataclasses with mutable fields.

- *Rejected due to:* Frozen dataclasses prevent accidental mutation,
  enable safe sharing across threads, and make model contracts
  explicit. `slots=True` reduces memory overhead for high-frequency
  trading data.

## Consequences

### Positive

1. **Dependency inversion.** Core TITAN modules depend on abstractions,
   not concrete brokers. Broker SDKs are isolated to adapter packages.
2. **Testability.** Core logic can be tested with mock brokers.
   `_TestBroker` in the test suite provides a complete in-memory broker.
3. **Extensibility.** Adding a new broker requires only implementing
   the `Broker` ABC and registering it with the factory.
4. **Future-proofing.** The abstraction supports all targeted brokers
   (Angel One, Zerodha, Dhan, Upstox, Interactive Brokers, Alpaca,
   Binance) without redesign.
5. **Frozen contracts.** All models are immutable — no subtle mutation
   bugs across provider boundaries.
6. **Rich type information.** Every method has precise return types,
   enabling MyPy validation and IDE autocompletion.
7. **Separation of concerns.** Five narrow provider interfaces prevent
   unnecessary coupling.

### Negative

1. **Interface surface area.** The `Broker` composite requires 20+
   method implementations per adapter. Smaller providers can be
   implemented individually.
2. **Abstraction overhead.** Simple operations (e.g., fetching LTP)
   require a method call through the interface rather than direct SDK
   usage. This is acceptable for the architectural benefits.
3. **New package.** Adds `titan/brokers/` alongside existing
   `titan/broker/`. Coexistence requires clear documentation.

### Neutral

1. Some broker-specific capabilities (e.g., unique order types, custom
   market data fields) require the `broker_params: Mapping[str, Any]`
   escape hatch on models.
2. The factory currently supports only single-broker construction.
   Multi-broker orchestration is a future concern.
3. `OrderResponse.timestamp` uses `datetime.UTC` now; brokers may
   return timestamps in different timezones — normalization is the
   adapter's responsibility.

## Future Evolution

### Short Term

- Migrate the existing Angel One adapter from `titan/broker/` to
  `titan/brokers/angel_one/`.
- Add Zerodha, Dhan, Upstox adapter implementations.
- Add streaming market data interface (`MarketDataStream`).

### Medium Term

- Add broker-agnostic order management (order routing, retry, status
  reconciliation).
- Add multi-broker portfolio aggregation.
- Add configuration-driven broker auto-discovery.

### Long Term

- Smart order routing across brokers.
- Broker failover and redundancy.
- Unified position consolidation across multiple broker accounts.
