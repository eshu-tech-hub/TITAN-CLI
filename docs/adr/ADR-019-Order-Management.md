# ADR-019: Order Management System (OMS)

**Status:** Accepted (Milestone M5.3)

**Date:** 2026-07-04

**Author:** TITAN Architecture Team

## Context

TITAN's decision pipeline (ADR-016) produces `TradeDecision` objects
that specify what to trade, in which direction, with what instrument
type, and with what risk parameters. Prior to this ADR, there was no
systematic layer to convert a `TradeDecision` into an executable order,
manage its lifecycle through to completion, and maintain a reliable
audit trail.

Without an OMS:

- Order lifecycle management is ad-hoc, duplicated across broker
  adapters.
- No central source of truth for order state exists.
- State transitions are not enforced — invalid transitions can occur.
- Audit trail requires separate instrumentation in every adapter.
- Future execution algorithms (TWAP, VWAP, iceberg, bracket) have no
  foundation to build on.
- Multiple broker support lacks a unified order routing layer.

## Decision

We introduce `titan/execution/` — a broker-independent Order Management
System that owns the complete lifecycle of every order in the platform.

### Package Structure

```
titan/execution/
    __init__.py       # Public API exports with __all__
    exceptions.py     # Domain exception hierarchy
    models.py         # Frozen dataclasses and enums
    order.py          # Order domain model
    book.py           # OrderBook — central order repository
    state.py          # OrderStateMachine — enforced transitions
    router.py         # OrderRouter — broker abstraction bridge
    execution.py      # ExecutionEngine — orchestrator
```

### Architecture

The OMS is composed of four core components:

1. **OrderStateMachine** — A deterministic finite state machine that
   defines valid transitions among 11 states and records every
   transition as an `OrderEvent`.

2. **OrderBook** — An in-memory repository of all orders. The single
   source of truth for order state. Supports query by ID, symbol,
   state, and time.

3. **OrderRouter** — Bridges the OMS to the broker abstraction layer.
   Converts TITAN `Order` objects to broker `OrderRequest` objects,
   routes them via the `Broker.place_order()` interface, and
   normalises broker `OrderStatus` responses back to TITAN
   `OrderState` values.

4. **ExecutionEngine** — The entry point that orchestrates the full
   flow: validates requests, creates orders, transitions through
   states, routes to brokers, and produces `ExecutionResult` with
   audit trail.

### Order States

```
NEW → VALIDATED → SUBMITTED → ACKNOWLEDGED → PARTIALLY_FILLED → FILLED
                                  │                                  │
                            ┌─────┼─────┐                     REJECTED
                            │     │     │                     CANCELLED
                        MODIFIED  |  EXPIRED                   EXPIRED
                            │     │     │                      FAILED
                            └─── REJECTED
                                  FAILED
```

Eleven states total, five terminal.

### State Machine Design

The `OrderStateMachine` uses a transition map (`dict[OrderState,
set[OrderState]]`) that defines all legal transitions. The
`transition()` method validates every attempted move and raises
`InvalidStateTransitionError` for illegal transitions. Every
transition produces an `OrderEvent` with timestamp, from/to states,
reason, broker reference, and optional error.

### Data Models

All data models are frozen dataclasses with `slots=True`:

| Model | Purpose |
|---|---|
| `OrderState` | Enum of 11 lifecycle states |
| `ExecutionAction` | Enum: ROUTE, BLOCK, DEFER, SPLIT |
| `OrderEvent` | Single lifecycle event |
| `OrderRoute` | Broker routing information |
| `OrderAudit` | Full audit trail container |
| `ExecutionRequest` | Input to the ExecutionEngine |
| `ExecutionReport` | Per-action execution report |
| `ExecutionResult` | Final execution output |
| `ExecutionExplanation` | Human-readable outcome explanation |
| `Order` | TITAN internal order representation |

### Order (`titan/execution/order.py`)

The OMS `Order` is distinct from the broker's `Order` model
(`titan/brokers/models.py`). The OMS Order:

- Has a TITAN-internal UUID `order_id`
- Tracks OMS `OrderState` (not broker `OrderStatus`)
- Maintains an immutable event list for audit
- Contains routing information
- Can exist before being sent to a broker (NEW, VALIDATED states)
- Uses `with_state()` for immutable state transitions (returns a new
  instance)

### Exception Hierarchy

```
ExecutionError (base)
├── OrderNotFoundError
├── InvalidStateTransitionError
├── OrderValidationError
├── BrokerUnavailableError
└── RouteNotFoundError
```

### Broker Independence

The OMS imports from `titan.brokers` (the broker abstraction layer)
but NOT from any concrete broker adapter. The `OrderRouter` uses the
`Broker` ABC interface. No yfinance, YFinance, or other
broker-specific imports exist in `titan/execution/`.

## Alternatives Considered

### State Machine as External Library

Using a general-purpose state machine library (e.g., `transitions`,
`automaton`).

- *Rejected due to:* Adding a dependency for a small, deterministic
  state machine. The OMS state machine has 11 states and ~25
  transitions — a 60-line implementation is simpler and avoids
  external coupling. Custom implementation also gives us full control
  over event recording for audit purposes.

### Mutable Order Model

Using mutable dataclasses and updating fields in place.

- *Rejected due to:* Frozen dataclasses with `with_state()` provide
  immutable audit trails, prevent accidental mutation, and make
  concurrency safe. Every state change produces a new `Order`
  instance with an appended event.

### Single Monolithic `OrderManager`

A single class handling validation, state, book, and routing.

- *Rejected due to:* Violates Single Responsibility Principle. The
  four-component decomposition (state machine, book, router, engine)
  allows independent testing, replacement, and extension.

### Direct Broker Calls from ExecutionEngine

The engine calls `Broker.place_order()` directly instead of going
through a router.

- *Rejected due to:* The router provides a single point for status
  normalisation, broker selection, and future smart routing. The
  engine should not know about broker interfaces.

## Consequences

### Positive

1. **Single source of truth.** Every order's complete lifecycle is
   tracked in the OrderBook with immutable events.
2. **Enforced state machine.** Invalid transitions are impossible at
   the model level — caught immediately by `InvalidStateTransitionError`.
3. **Broker independent.** The OMS contains zero broker-specific logic.
   New brokers require only a `Broker` ABC implementation.
4. **Audit trail.** Every state transition is recorded with timestamp,
   reason, broker reference, and error context.
5. **Testable.** The `_MockBroker` in tests provides a complete
   in-memory broker for testing all execution paths without network.
6. **Extensible.** Future execution algorithms (TWAP, VWAP, iceberg,
   bracket, OCO, basket) can be built on top of the `ExecutionEngine`
   without modifying core OMS components.
7. **Immutable models.** Frozen dataclasses prevent mutation bugs and
   enable safe concurrent access.
8. **87 tests.** Full coverage of state transitions, order book CRUD,
   routing, validation, audit, failure handling, and multi-order
   scenarios.

### Negative

1. **In-memory only.** The OrderBook does not persist to disk. Orders
   are lost on process restart. Persistence is a future concern.
2. **Single-broker routing.** The router supports one broker per
   order. Multi-broker smart routing is not yet implemented.
3. **No streaming.** The OMS uses request-response broker interaction.
   Streaming order updates are not yet supported.

### Neutral

1. Order state normalisation from broker `OrderStatus` uses a static
   map. Some broker-specific status nuances may require the
   `broker_params` escape hatch.
2. The `ExecutionEngine.execute()` method is synchronous. Async
   execution is a future concern.
3. The OMS does not handle post-trade settlement, corporate actions,
   or tax lot accounting.

## Future Evolution

### Short Term

- Order persistence (SQLite/PostgreSQL backend for OrderBook).
- Order modification and cancellation through the engine.
- Order status reconciliation (poll broker for updates).
- Streaming order updates via WebSocket.

### Medium Term

- TwapExecutionAlgorithm, VwapExecutionAlgorithm.
- IcebergOrder, BracketOrder, OcoOrder strategy wrappers.
- Basket execution (atomic multi-symbol orders).
- Order validity lifecycle (auto-expire DAY orders at market close).

### Long Term

- Smart order routing across multiple brokers.
- Broker failover and order migration.
- Execution analytics (fill rate, slippage, latency).
- Integration with portfolio rebalancing engine.
