# TITAN Order Management System (OMS)

## Overview

The OMS owns the complete lifecycle of every order in the TITAN
platform. It is the single source of truth for order state and
communicates with broker adapters through the broker abstraction
layer — it contains zero broker-specific logic.

**Location:** `titan/execution/`

**Principle:** The OMS does not decide WHAT or WHEN to trade. It only
manages the lifecycle of orders after a `TradeDecision` has been
approved by the Decision Engine.

---

## Architecture

```
TradeDecision  ──┐
RiskAnalysis  ──┤
Portfolio     ──┤──► ExecutionRequest ──► ExecutionEngine ──► ExecutionResult
Context       ──┘                            │
                                              ├── OrderStateMachine
                                              ├── OrderBook
                                              └── OrderRouter ──► Broker
```

### Package Structure

```
titan/execution/
    __init__.py       # Public API exports
    exceptions.py     # Domain exception hierarchy
    models.py         # Frozen dataclasses and enums
    order.py          # Order domain model
    book.py           # OrderBook
    state.py          # OrderStateMachine
    router.py         # OrderRouter
    execution.py      # ExecutionEngine
```

---

## Order States

The OMS defines 11 lifecycle states:

```
                    ┌─────────────────────────────────────┐
                    │               NEW                    │
                    └────────────┬────────────────────────┘
                                 │
                    ┌────────────▼─────────────┐      ┌───────────┐
                    │        VALIDATED          │─────►│  REJECTED  │
                    └────────────┬─────────────┘      └───────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │        SUBMITTED          │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │       ACKNOWLEDGED        │◄──────────┐
                    └────────────┬─────────────┘            │
                     ┌───────┬──┴──┬────────┐              │
                     │       │     │        │              │
              ┌──────▼──┐ ┌──▼──┐ ┌▼─────┐ ┌▼──────┐      │
              │PARTIAL  │ │FILL │ │CANC  │ │MODIFY │──────┘
              │ _FILLED │ │ED   │ │ELLED │ │       │
              └──┬───┬──┘ └─────┘ └──────┘ └───────┘
                 │   │
        ┌────────┘   └─────────┐
        │                      │
   ┌────▼─────┐          ┌────▼──────┐
   │  FILLED  │          │  EXPIRED   │
   └──────────┘          └───────────┘
```

**Terminal states:** `FILLED`, `REJECTED`, `CANCELLED`, `EXPIRED`, `FAILED`

### State Transition Rules

| From | To | Condition |
|---|---|---|
| NEW | VALIDATED | Request passes validation |
| NEW | REJECTED | Validation fails |
| NEW | FAILED | System error during creation |
| VALIDATED | SUBMITTED | Order sent to broker |
| VALIDATED | REJECTED | Broker rejects pre-submission |
| VALIDATED | FAILED | System error |
| SUBMITTED | ACKNOWLEDGED | Broker confirms receipt |
| SUBMITTED | REJECTED | Broker rejects order |
| SUBMITTED | FAILED | System error during routing |
| ACKNOWLEDGED | PARTIALLY_FILLED | Partial fill received |
| ACKNOWLEDGED | FILLED | Full fill received |
| ACKNOWLEDGED | CANCELLED | User cancels |
| ACKNOWLEDGED | MODIFIED | User modifies |
| ACKNOWLEDGED | REJECTED | Broker rejects |
| ACKNOWLEDGED | EXPIRED | Order expires |
| ACKNOWLEDGED | FAILED | System error |
| MODIFIED | ACKNOWLEDGED | Modification confirmed |
| MODIFIED | REJECTED | Modification rejected |
| MODIFIED | FAILED | System error |
| PARTIALLY_FILLED | PARTIALLY_FILLED | Additional fill received |
| PARTIALLY_FILLED | FILLED | Remaining quantity filled |
| PARTIALLY_FILLED | CANCELLED | Remaining cancelled |
| PARTIALLY_FILLED | MODIFIED | Remaining modified |
| PARTIALLY_FILLED | REJECTED | Remaining rejected |
| PARTIALLY_FILLED | EXPIRED | Remaining expired |
| PARTIALLY_FILLED | FAILED | System error |

---

## ExecutionEngine

The `ExecutionEngine` is the entry point into the OMS. It:

1. **Validates** the `ExecutionRequest` (symbol, quantity, price rules)
2. **Creates** an `Order` and adds it to the `OrderBook`
3. **Transitions** through the `OrderStateMachine` (NEW → VALIDATED → SUBMITTED)
4. **Routes** the order via the `OrderRouter` to the target broker
5. **Normalises** the broker response into the OMS state model
6. **Produces** an `ExecutionResult` with audit trail

### Usage

```python
from titan.execution import (
    ExecutionEngine,
    ExecutionRequest,
    OrderBook,
    OrderRouter,
)
from titan.brokers.models import (
    Exchange, OrderSide, OrderType,
)
from titan.brokers.factory import BrokerFactory

# Set up the engine.
book = OrderBook()
router = OrderRouter()
router.register_broker(BrokerType.ANGEL_ONE, angel_one_broker)
engine = ExecutionEngine(order_book=book, router=router)

# Execute a trade.
request = ExecutionRequest(
    request_id="REQ-001",
    symbol="RELIANCE",
    exchange=Exchange.NSE,
    side=OrderSide.BUY,
    order_type=OrderType.MARKET,
    quantity=10,
)
result = engine.execute(request)

if result.success:
    print(f"Order {result.order.order_id} at state {result.order.state.value}")
```

---

## OrderBook

The `OrderBook` is the central repository for all orders:

| Method | Description |
|---|---|
| `add(order)` | Add a new order |
| `update(order)` | Replace with updated version |
| `remove(order_id)` | Remove from book |
| `lookup(order_id)` | Find by ID (raises if not found) |
| `get(order_id)` | Find by ID (returns None) |
| `all_orders` | All orders |
| `open_orders` | Orders in non-terminal states |
| `active_orders` | Alias for open_orders |
| `filled_orders` | Filled orders |
| `cancelled_orders` | Cancelled orders |
| `rejected_orders` | Rejected orders |
| `orders_by_symbol(symbol)` | Filter by symbol |
| `orders_by_state(state)` | Filter by state |
| `orders_since(datetime)` | Filter by creation time |
| `count` | Total number of orders |
| `clear()` | Remove all orders |

---

## OrderRouter

The `OrderRouter` bridges the OMS to the broker abstraction layer:

- Routes orders to registered broker implementations
- Normalises broker `OrderStatus` to OMS `OrderState`
- Raises `RouteNotFoundError` if no broker is registered
- Raises `BrokerUnavailableError` if broker is disconnected

### Status Normalisation

| Broker Status | OMS State |
|---|---|
| PENDING | SUBMITTED |
| OPEN | ACKNOWLEDGED |
| PARTIALLY_FILLED | PARTIALLY_FILLED |
| FILLED | FILLED |
| CANCELLED | CANCELLED |
| REJECTED | REJECTED |
| EXPIRED | EXPIRED |

---

## Audit Trail

Every order records complete lifecycle events:

```python
@dataclass(frozen=True, slots=True)
class OrderEvent:
    timestamp: datetime
    from_state: OrderState | None
    to_state: OrderState
    reason: str
    broker_order_id: str | None
    error: str | None
```

Events are immutable and ordered. The full event sequence is
accessible via `order.events`.

---

## Future Execution Algorithms

The OMS architecture supports the following execution strategies
without redesign:

- **Split orders** — Multiple child orders under a parent
- **Iceberg orders** — Reserve quantity with visible portion
- **TWAP** — Time-weighted average price slicing
- **VWAP** — Volume-weighted average price slicing
- **Bracket orders** — Entry + stop-loss + target as a unit
- **OCO** — One-cancels-other order pairs
- **Basket orders** — Multi-symbol atomic execution
- **Algo execution** — Custom algorithm wrappers

Each strategy would be implemented as a new module in
`titan/execution/algo/` that consumes the `ExecutionEngine` API.

---

## Quality

- Frozen dataclasses with `slots=True`
- Strict type hints throughout
- Deterministic state machine with enforced transitions
- Full test coverage (87 tests)
- Ruff clean, Black clean, MyPy clean
