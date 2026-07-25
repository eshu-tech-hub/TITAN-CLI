import time
import uuid
from datetime import datetime, timezone

from titan.execution.book import OrderBook
from titan.execution.exceptions import (
    BrokerUnavailableError,
    RouteNotFoundError,
)
from titan.execution.models import (
    ExecutionRequest,
    ExecutionResult,
    OrderRoute,
    OrderState,
)
from titan.execution.order import Order
from titan.execution.router import OrderRouter
from titan.execution.state import OrderStateMachine


class ExecutionEngine:
    """Central orchestrator for order execution.

    The ExecutionEngine is the entry point into the OMS. It:

    1. Validates the execution request (portfolio, risk, order validity).
    2. Creates an Order and adds it to the OrderBook.
    3. Routes the order through the OrderRouter to a broker.
    4. Tracks state transitions through the OrderStateMachine.
    5. Produces an ExecutionResult with full audit trail.

    The engine does NOT decide WHAT or WHEN to trade. It only
    manages the lifecycle of orders after a decision has been made.
    """

    def __init__(
        self,
        order_book: OrderBook,
        router: OrderRouter,
    ) -> None:
        self._order_book = order_book
        self._router = router

    @property
    def order_book(self) -> OrderBook:
        return self._order_book

    @property
    def router(self) -> OrderRouter:
        return self._router

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute a trade decision through the OMS.

        Args:
            request: The validated execution request.

        Returns:
            An ExecutionResult with the outcome.
        """
        start_time = time.monotonic()
        errors: list[str] = []

        # 1. Validate the request.
        validation_errors = self._validate_request(request)
        if validation_errors:
            return ExecutionResult(
                request_id=request.request_id,
                success=False,
                errors=tuple(validation_errors),
                execution_time_ms=(time.monotonic() - start_time) * 1000,
            )

        # 2. Create the order.
        state_machine = OrderStateMachine()
        order = self._create_order(request, state_machine)

        # 3. Add to the order book.
        self._order_book.add(order)

        # 4. Transition to VALIDATED.
        state_machine.transition(OrderState.VALIDATED, reason="Request validated")
        order = order.with_state(OrderState.VALIDATED, reason="Request validated")
        self._order_book.update(order)

        # 5. Check broker availability.
        broker_available = self._check_broker(request)
        if not broker_available:
            state_machine.transition(
                OrderState.FAILED,
                reason="Broker unavailable",
                error="No connected broker found",
            )
            order = order.with_state(
                OrderState.FAILED,
                reason="Broker unavailable",
                error="No connected broker found",
            )
            self._order_book.update(order)
            elapsed = (time.monotonic() - start_time) * 1000
            return ExecutionResult(
                request_id=request.request_id,
                success=False,
                order=order,
                errors=("No connected broker available for execution.",),
                execution_time_ms=elapsed,
            )

        # 6. Route the order.
        try:
            state_machine.transition(
                OrderState.SUBMITTED, reason="Submitting to broker"
            )
            order = order.with_state(
                OrderState.SUBMITTED, reason="Submitting to broker"
            )
            self._order_book.update(order)

            report = self._router.route(order)

            if report.success:
                route = OrderRoute(
                    broker_type=(
                        request.broker_type
                        if request.broker_type
                        else self._router.registered_brokers()[0]
                    ),
                    broker_order_id=report.broker_order_id,
                    status=report.state,
                )

                state_machine.transition(
                    OrderState.ACKNOWLEDGED,
                    reason="Broker acknowledged",
                    broker_order_id=report.broker_order_id,
                )
                order = order.with_state(
                    OrderState.ACKNOWLEDGED,
                    reason="Broker acknowledged",
                    broker_order_id=report.broker_order_id,
                    route=route,
                )

                if report.state in {
                    OrderState.PARTIALLY_FILLED,
                    OrderState.FILLED,
                }:
                    filled = order.quantity if report.state == OrderState.FILLED else 0
                    pending = order.quantity - filled

                    state_machine.transition(
                        report.state,
                        reason=report.message,
                        broker_order_id=report.broker_order_id,
                    )
                    order = order.with_state(
                        report.state,
                        reason=report.message,
                        broker_order_id=report.broker_order_id,
                        filled_quantity=filled,
                        pending_quantity=pending,
                    )
            else:
                errors.extend(report.errors)

        except (BrokerUnavailableError, RouteNotFoundError) as e:
            state_machine.transition(
                OrderState.FAILED, reason="Routing failed", error=str(e)
            )
            order = order.with_state(
                OrderState.FAILED, reason="Routing failed", error=str(e)
            )
            errors.append(str(e))

        self._order_book.update(order)

        elapsed = (time.monotonic() - start_time) * 1000
        return ExecutionResult(
            request_id=request.request_id,
            success=len(errors) == 0,
            order=order,
            errors=tuple(errors),
            execution_time_ms=elapsed,
        )

    def validate_request(self, request: ExecutionRequest) -> list[str]:
        """Validate an execution request without executing it.

        Returns a list of validation error messages (empty if valid).
        """
        return self._validate_request(request)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_request(request: ExecutionRequest) -> list[str]:
        errors: list[str] = []

        if not request.request_id:
            errors.append("Request ID is required.")

        if not request.symbol:
            errors.append("Trading symbol is required.")

        if request.quantity <= 0:
            errors.append("Quantity must be greater than zero.")

        if (
            request.order_type.value in ("limit", "stop_loss_limit")
            and request.price is None
        ):
            errors.append(
                "Limit price is required for LIMIT and STOP_LOSS_LIMIT orders."
            )

        if (
            request.order_type.value in ("stop_loss", "stop_loss_limit")
            and request.trigger_price is None
        ):
            errors.append("Trigger price is required for stop-loss orders.")

        if request.disclose_quantity < 0:
            errors.append("Disclose quantity cannot be negative.")

        if request.disclose_quantity > request.quantity:
            errors.append("Disclose quantity cannot exceed order quantity.")

        return errors

    @staticmethod
    def _create_order(
        request: ExecutionRequest,
        state_machine: OrderStateMachine | None = None,
    ) -> Order:
        order_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        return Order(
            order_id=order_id,
            symbol=request.symbol,
            exchange=request.exchange,
            side=request.side,
            order_type=request.order_type,
            quantity=request.quantity,
            product=request.product,
            validity=request.validity,
            price=request.price,
            trigger_price=request.trigger_price,
            disclose_quantity=request.disclose_quantity,
            tag=request.tag,
            state=OrderState.NEW,
            trade_decision_id=request.trade_decision_id,
            request_id=request.request_id,
            created_at=now,
        )

    def _check_broker(self, request: ExecutionRequest) -> bool:
        """Check whether a suitable broker is available for routing."""
        registered = self._router.registered_brokers()
        if not registered:
            return False

        if request.broker_type is not None:
            return request.broker_type in self._router._brokers

        return True
