from dataclasses import dataclass, field

from titan.brokers.models import Exchange
from titan.runtime.events import RuntimeEventBus
from titan.runtime.exceptions import SubscriptionError
from titan.runtime.models import RuntimeEventType, Subscription, SubscriptionType


@dataclass(slots=True)
class SubscriptionManager:
    """Manages market data subscriptions for the runtime.

    Tracks subscribed symbols, option chains, indices, and
    watchlists. Supports dynamic subscription updates for
    adding and removing symbols at runtime.

    Attributes:
        event_bus: Event bus for publishing subscription events.
        _subscriptions: Internal map of symbol -> Subscription.
    """

    event_bus: RuntimeEventBus | None = None
    _subscriptions: dict[str, Subscription] = field(default_factory=dict, init=False)

    def add(
        self,
        symbol: str,
        exchange: Exchange,
        subscription_type: SubscriptionType = SubscriptionType.SYMBOL,
        metadata: dict | None = None,
    ) -> Subscription:
        """Add a new subscription.

        Args:
            symbol: Trading symbol.
            exchange: Exchange.
            subscription_type: Type of subscription.
            metadata: Optional metadata.

        Returns:
            The created Subscription.

        Raises:
            SubscriptionError: If the symbol is already subscribed.
        """
        key = self._key(symbol, exchange)
        if key in self._subscriptions:
            raise SubscriptionError(
                f"Symbol {symbol} on {exchange.value} is already subscribed."
            )

        sub = Subscription(
            symbol=symbol,
            exchange=exchange,
            subscription_type=subscription_type,
            enabled=True,
            metadata=metadata or {},
        )
        self._subscriptions[key] = sub

        if self.event_bus is not None:
            self.event_bus.publish_type(
                RuntimeEventType.SUBSCRIPTION_ADDED,
                "subscriptions",
                data={"symbol": symbol, "exchange": exchange.value},
            )

        return sub

    def remove(self, symbol: str, exchange: Exchange) -> None:
        """Remove an existing subscription.

        Args:
            symbol: Trading symbol.
            exchange: Exchange.

        Raises:
            SubscriptionError: If the subscription does not exist.
        """
        key = self._key(symbol, exchange)
        if key not in self._subscriptions:
            raise SubscriptionError(
                f"Symbol {symbol} on {exchange.value} is not subscribed."
            )

        del self._subscriptions[key]

        if self.event_bus is not None:
            self.event_bus.publish_type(
                RuntimeEventType.SUBSCRIPTION_REMOVED,
                "subscriptions",
                data={"symbol": symbol, "exchange": exchange.value},
            )

    def get(self, symbol: str, exchange: Exchange) -> Subscription | None:
        """Get a subscription by symbol and exchange.

        Args:
            symbol: Trading symbol.
            exchange: Exchange.

        Returns:
            The Subscription if found, None otherwise.
        """
        return self._subscriptions.get(self._key(symbol, exchange))

    def list_active(self) -> list[Subscription]:
        """Get all active (enabled) subscriptions.

        Returns:
            List of active subscriptions.
        """
        return [s for s in self._subscriptions.values() if s.enabled]

    def list_all(self) -> list[Subscription]:
        """Get all subscriptions regardless of enabled state.

        Returns:
            List of all subscriptions.
        """
        return list(self._subscriptions.values())

    def enable(self, symbol: str, exchange: Exchange) -> Subscription:
        """Enable a subscription.

        Args:
            symbol: Trading symbol.
            exchange: Exchange.

        Returns:
            The updated Subscription.

        Raises:
            SubscriptionError: If the subscription does not exist.
        """
        key = self._key(symbol, exchange)
        existing = self._subscriptions.get(key)
        if existing is None:
            raise SubscriptionError(
                f"Symbol {symbol} on {exchange.value} is not subscribed."
            )
        updated = Subscription(
            symbol=existing.symbol,
            exchange=existing.exchange,
            subscription_type=existing.subscription_type,
            enabled=True,
            metadata=existing.metadata,
        )
        self._subscriptions[key] = updated
        return updated

    def disable(self, symbol: str, exchange: Exchange) -> Subscription:
        """Disable a subscription.

        Args:
            symbol: Trading symbol.
            exchange: Exchange.

        Returns:
            The updated Subscription.

        Raises:
            SubscriptionError: If the subscription does not exist.
        """
        key = self._key(symbol, exchange)
        existing = self._subscriptions.get(key)
        if existing is None:
            raise SubscriptionError(
                f"Symbol {symbol} on {exchange.value} is not subscribed."
            )
        updated = Subscription(
            symbol=existing.symbol,
            exchange=existing.exchange,
            subscription_type=existing.subscription_type,
            enabled=False,
            metadata=existing.metadata,
        )
        self._subscriptions[key] = updated
        return updated

    def symbols(self) -> list[str]:
        """Get all subscribed symbols.

        Returns:
            List of symbol strings.
        """
        return list(self._subscriptions.keys())

    def count(self) -> int:
        """Get the total number of subscriptions.

        Returns:
            Number of subscriptions.
        """
        return len(self._subscriptions)

    def clear(self) -> None:
        """Remove all subscriptions."""
        self._subscriptions.clear()

    @staticmethod
    def _key(symbol: str, exchange: Exchange) -> str:
        """Generate a unique key for a symbol+exchange pair."""
        return f"{exchange.value}:{symbol}"
