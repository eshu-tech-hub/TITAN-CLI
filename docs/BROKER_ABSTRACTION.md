# TITAN Broker Abstraction Layer

## Overview

The Broker Abstraction Layer defines the contract between TITAN and any
broker. It is a pure interface layer with zero broker-specific
implementation, zero network logic, zero API keys, and zero broker SDK
imports.

**Location:** `titan/brokers/`

**Principle:** TITAN core modules must never depend directly on broker
SDKs. All broker interaction goes through these abstractions.

---

## Architecture

```
titan/brokers/
    __init__.py       # Public API exports
    exceptions.py     # Domain exception hierarchy
    models.py         # Frozen dataclasses and enums
    broker.py         # ABC interfaces
    factory.py        # Registry-based factory
```

### Dependency Inversion

```
TITAN Core  ──►  Broker Abstraction  ◄──  Broker Adapter
     │                                      (e.g. AngelOneBroker)
     │                                              │
     └── never imports broker SDKs ────────────── SDK
```

---

## Interfaces

Six abstract base classes in `broker.py`:

| Interface | Responsibility | Methods |
|---|---|---|
| `MarketDataProvider` | Real-time & snapshot data | `quote`, `quotes`, `option_chain`, `market_depth`, `ltp` |
| `HistoricalDataProvider` | Historical market data | `history`, `intraday`, `ohlcv` |
| `OrderProvider` | Order lifecycle management | `place_order`, `modify_order`, `cancel_order`, `order`, `orders` |
| `PortfolioProvider` | Portfolio & position data | `positions`, `holdings`, `trades` |
| `AccountProvider` | Account information | `funds`, `margin`, `profile` |
| `Broker` | Complete broker interface | Combines all five providers + `connect`, `disconnect`, `is_connected` |

### Broker Interface

```python
class Broker(MarketDataProvider, HistoricalDataProvider,
             OrderProvider, PortfolioProvider, AccountProvider, ABC):
    @abstractmethod
    def connect(self) -> ConnectionStatus: ...
    @abstractmethod
    def disconnect(self) -> ConnectionStatus: ...
    @abstractmethod
    def is_connected(self) -> bool: ...
```

---

## Models

All models are frozen dataclasses. Located in `models.py`.

### Enums

| Enum | Values |
|---|---|
| `BrokerType` | `ANGEL_ONE`, `ZERODHA`, `DHAN`, `UPSTOX`, `INTERACTIVE_BROKERS`, `ALPACA`, `BINANCE` |
| `ConnectionStatus` | `CONNECTED`, `DISCONNECTED`, `CONNECTING`, `RECONNECTING`, `ERROR` |
| `OrderStatus` | `PENDING`, `OPEN`, `PARTIALLY_FILLED`, `FILLED`, `CANCELLED`, `REJECTED`, `EXPIRED` |
| `OrderSide` | `BUY`, `SELL` |
| `OrderType` | `MARKET`, `LIMIT`, `STOP_LOSS`, `STOP_LOSS_LIMIT` |
| `ProductType` | `DELIVERY`, `INTRADAY`, `MARGIN`, `OPTIONS`, `FUTURES` |
| `Validity` | `DAY`, `IOC`, `GTC` |
| `InstrumentType` | `EQUITY`, `FUTURES`, `OPTIONS`, `CURRENCY`, `COMMODITY`, `ETF`, `INDEX` |
| `Exchange` | `NSE`, `BSE`, `NFO`, `CDS`, `MCX`, `BSE_FO` |

### Dataclasses

| Model | Purpose |
|---|---|
| `OrderRequest` | Place a new order |
| `OrderResponse` | Response after placing an order |
| `ModifyOrderRequest` | Modify an open order |
| `CancelOrderRequest` | Cancel an open order |
| `Order` | Full order representation |
| `Position` | Open position |
| `Holding` | Demat holding |
| `Trade` | Executed fill |
| `Quote` | Snapshot quote |
| `MarketDepthLevel` | Single order-book level |
| `MarketDepth` | Order book snapshot |
| `MarginInfo` | Account margin details |
| `FundsInfo` | Account funds summary |
| `AccountProfile` | Account profile |
| `Candle` | OHLCV data point |

---

## Factory

`BrokerFactory` uses a registry pattern:

```python
factory = BrokerFactory()
factory.register(BrokerType.ANGEL_ONE, AngelOneBroker)
broker = factory.create(BrokerType.ANGEL_ONE, api_key="...")
```

Methods:
- `register(broker_type, broker_cls)` — Register a broker implementation
- `create(broker_type, **kwargs)` — Instantiate a registered broker
- `supported_brokers()` — List registered broker types

---

## Exceptions

| Exception | Parent | Raised When |
|---|---|---|
| `BrokerError` | `Exception` | Base for all broker errors |
| `ConnectionError` | `BrokerError` | Connection/reconnection fails |
| `AuthenticationError` | `BrokerError` | Authentication or session invalid |
| `OrderError` | `BrokerError` | Order placement/modification/cancellation fails |
| `MarketDataError` | `BrokerError` | Market data query fails |
| `ValidationError` | `BrokerError` | Request or configuration fails validation |

---

## Future Broker Support

The abstraction supports the following brokers without redesign:

- Angel One
- Zerodha
- Dhan
- Upstox
- Interactive Brokers
- Alpaca
- Binance

Each broker adapter lives under `titan/brokers/<name>/` and implements
the `Broker` ABC.

---

## Quality Requirements

- Frozen dataclasses with `slots=True`
- Strict type hints throughout
- ABC interfaces with `@abstractmethod`
- Protocol-friendly design
- Ruff clean
- Black clean
- MyPy clean
- Pytest coverage

---

## Testing

Tests in `tests/test_broker_abstraction.py` verify:

1. All enum values are correct
2. All dataclass fields and defaults work as expected
3. Exception hierarchy is correct
4. All interfaces are ABCs
5. All interfaces cannot be instantiated directly
6. A concrete broker implementing `Broker` works end-to-end
7. Factory registration, creation, deduplication, and kwarg forwarding
