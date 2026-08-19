from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from titan.brokers.models import (
    BrokerType,
    Exchange,
    OrderSide,
    OrderType,
    ProductType,
    Validity,
)


class OrderState(str, Enum):
    """Lifecycle states for an order in the OMS.

    NEW                  Order created, not yet validated.
    VALIDATED            Passed internal validation.
    SUBMITTED            Sent to the broker.
    ACKNOWLEDGED         Broker confirmed receipt.
    MODIFIED             Order modification requested.
    PARTIALLY_FILLED     Order partially filled.
    FILLED               Order fully filled (terminal).
    REJECTED             Order rejected (terminal).
    CANCELLED            Order cancelled (terminal).
    EXPIRED              Order expired (terminal).
    FAILED               System-level failure (terminal).
    """

    NEW = "new"
    VALIDATED = "validated"
    SUBMITTED = "submitted"
    ACKNOWLEDGED = "acknowledged"
    MODIFIED = "modified"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    FAILED = "failed"


class ExecutionAction(str, Enum):
    """High-level execution action determined by the engine."""

    ROUTE = "route"
    BLOCK = "block"
    DEFER = "defer"
    SPLIT = "split"


@dataclass(frozen=True, slots=True)
class OrderRoute:
    """Information about how an order was routed to a broker.

    Attributes:
        broker_type: The broker the order was routed to.
        broker_order_id: The broker-assigned order ID (None if not yet assigned).
        status: Current OMS state of the routed order.
        timestamp: When the route was established.
        metadata: Broker-specific routing metadata.
    """

    broker_type: BrokerType
    broker_order_id: str | None = None
    status: OrderState = OrderState.NEW
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class OrderEvent:
    """A single event recorded during the order lifecycle.

    Attributes:
        timestamp: When the event occurred.
        from_state: Previous order state (None for the initial event).
        to_state: Order state after this event.
        reason: Human-readable explanation for the transition.
        broker_order_id: Broker order ID if applicable.
        error: Error message if the event represents a failure.
        metadata: Additional event metadata.
    """

    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    from_state: OrderState | None = None
    to_state: OrderState = OrderState.NEW
    reason: str = ""
    broker_order_id: str | None = None
    error: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class OrderAudit:
    """Full audit trail for a single order.

    Attributes:
        order_id: The TITAN internal order ID.
        events: Ordered sequence of lifecycle events.
        created_at: When the order was created.
        updated_at: When the order was last updated.
        terminal: Whether the order has reached a terminal state.
    """

    order_id: str
    events: tuple[OrderEvent, ...] = field(default_factory=tuple)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    terminal: bool = False


@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    """Request to execute a trade decision through the OMS.

    Attributes:
        request_id: Unique identifier for this execution request.
        symbol: Trading symbol.
        exchange: Exchange to route the order to.
        side: Buy or sell.
        order_type: Market, limit, or stop-loss.
        quantity: Number of units or contracts.
        product: Product type.
        validity: Time validity.
        price: Limit price (required for LIMIT orders).
        trigger_price: Trigger price for stop-loss orders.
        disclose_quantity: Quantity to disclose.
        tag: Client-provided identifier.
        trade_decision_id: Reference to the originating TradeDecision.
        portfolio_context_id: Reference to portfolio context.
        risk_analysis_id: Reference to risk analysis.
        broker_type: Target broker (None for automatic routing).
        metadata: Additional execution metadata.
    """

    request_id: str
    symbol: str
    exchange: Exchange
    side: OrderSide
    order_type: OrderType
    quantity: int
    product: ProductType = ProductType.DELIVERY
    validity: Validity = Validity.DAY
    price: Decimal | None = None
    trigger_price: Decimal | None = None
    disclose_quantity: int = 0
    tag: str = ""
    trade_decision_id: str = ""
    portfolio_context_id: str = ""
    risk_analysis_id: str = ""
    broker_type: BrokerType | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ExecutionReport:
    """Report produced after attempting an execution action.

    Attributes:
        request_id: The originating execution request ID.
        order_id: The TITAN internal order ID.
        success: Whether the action succeeded.
        action: The execution action taken.
        state: Current order state after the action.
        broker_order_id: Broker-assigned order ID if routed.
        message: Human-readable result message.
        errors: Any errors encountered.
        timestamp: When the report was generated.
    """

    request_id: str
    order_id: str
    success: bool
    action: ExecutionAction
    state: OrderState
    broker_order_id: str | None = None
    message: str = ""
    errors: tuple[str, ...] = field(default_factory=tuple)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """Final result of an execution request.

    Attributes:
        request_id: The originating execution request ID.
        success: Whether the overall execution succeeded.
        order: The resulting order (None if execution was blocked).
        reports: Sequence of execution reports produced.
        errors: Any errors encountered during execution.
        execution_time_ms: Total execution time in milliseconds.
        timestamp: When the result was generated.
    """

    request_id: str
    success: bool
    order: Any | None = None
    reports: tuple[ExecutionReport, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)
    execution_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class ExecutionExplanation:
    """Explanation of an execution outcome.

    Attributes:
        summary: One-line summary of what happened.
        validation_issues: Any validation issues encountered.
        routing_details: How the order was routed.
        state_transitions: Key state transitions that occurred.
        warnings: Any warnings generated during execution.
    """

    summary: str = ""
    validation_issues: tuple[str, ...] = field(default_factory=tuple)
    routing_details: str = ""
    state_transitions: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
