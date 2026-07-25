from titan.execution.exceptions import InvalidStateTransitionError
from titan.execution.models import OrderEvent, OrderState


class OrderStateMachine:
    """Deterministic finite state machine for order lifecycle.

    Enforces valid state transitions and records every transition
    as an OrderEvent for full auditability.
    """

    _TRANSITIONS: dict[OrderState, set[OrderState]] = {
        OrderState.NEW: {
            OrderState.VALIDATED,
            OrderState.REJECTED,
            OrderState.FAILED,
        },
        OrderState.VALIDATED: {
            OrderState.SUBMITTED,
            OrderState.REJECTED,
            OrderState.FAILED,
        },
        OrderState.SUBMITTED: {
            OrderState.ACKNOWLEDGED,
            OrderState.REJECTED,
            OrderState.FAILED,
        },
        OrderState.ACKNOWLEDGED: {
            OrderState.PARTIALLY_FILLED,
            OrderState.FILLED,
            OrderState.CANCELLED,
            OrderState.MODIFIED,
            OrderState.REJECTED,
            OrderState.EXPIRED,
            OrderState.FAILED,
        },
        OrderState.MODIFIED: {
            OrderState.ACKNOWLEDGED,
            OrderState.REJECTED,
            OrderState.FAILED,
        },
        OrderState.PARTIALLY_FILLED: {
            OrderState.PARTIALLY_FILLED,
            OrderState.FILLED,
            OrderState.CANCELLED,
            OrderState.MODIFIED,
            OrderState.REJECTED,
            OrderState.EXPIRED,
            OrderState.FAILED,
        },
        OrderState.FILLED: set(),
        OrderState.REJECTED: set(),
        OrderState.CANCELLED: set(),
        OrderState.EXPIRED: set(),
        OrderState.FAILED: set(),
    }

    _TERMINAL_STATES: frozenset[OrderState] = frozenset(
        {
            OrderState.FILLED,
            OrderState.REJECTED,
            OrderState.CANCELLED,
            OrderState.EXPIRED,
            OrderState.FAILED,
        }
    )

    def __init__(self) -> None:
        self._current: OrderState = OrderState.NEW
        self._events: list[OrderEvent] = [
            OrderEvent(to_state=OrderState.NEW, reason="Order created"),
        ]

    @property
    def current_state(self) -> OrderState:
        return self._current

    @property
    def events(self) -> tuple[OrderEvent, ...]:
        return tuple(self._events)

    @property
    def is_terminal(self) -> bool:
        return self._current in self._TERMINAL_STATES

    @staticmethod
    def is_valid_transition(from_state: OrderState, to_state: OrderState) -> bool:
        """Check whether a state transition is allowed."""
        valid_targets = OrderStateMachine._TRANSITIONS.get(from_state, set())
        return to_state in valid_targets

    def validate_transition(self, to_state: OrderState) -> bool:
        """Check whether a transition from the current state is allowed."""
        return self.is_valid_transition(self._current, to_state)

    def transition(
        self,
        to_state: OrderState,
        reason: str = "",
        broker_order_id: str | None = None,
        error: str | None = None,
    ) -> OrderState:
        """Attempt a state transition.

        Args:
            to_state: The target state.
            reason: Human-readable reason for the transition.
            broker_order_id: Broker order ID if applicable.
            error: Error message if the transition is a failure.

        Returns:
            The new current state.

        Raises:
            InvalidStateTransitionError: If the transition is not allowed.
        """
        if not self.validate_transition(to_state):
            raise InvalidStateTransitionError(
                f"Cannot transition from {self._current.value} " f"to {to_state.value}."
            )

        event = OrderEvent(
            from_state=self._current,
            to_state=to_state,
            reason=reason,
            broker_order_id=broker_order_id,
            error=error,
        )
        self._events.append(event)
        self._current = to_state
        return self._current

    def reset(self) -> None:
        """Reset the state machine to initial state (for testing)."""
        self._current = OrderState.NEW
        self._events = [
            OrderEvent(to_state=OrderState.NEW, reason="State machine reset"),
        ]
