from titan.brokers.broker import Broker
from titan.brokers.exceptions import BrokerError
from titan.brokers.models import BrokerType


class BrokerFactory:
    """Registry-based factory for creating broker instances.

    Usage:
        factory = BrokerFactory()
        factory.register(BrokerType.ZERODHA, ZerodhaBroker)
        broker = factory.create(BrokerType.ZERODHA, api_key="...")
    """

    def __init__(self) -> None:
        self._registry: dict[BrokerType, type[Broker]] = {}

    def register(self, broker_type: BrokerType, broker_cls: type[Broker]) -> None:
        """Register a broker implementation for a given BrokerType.

        Args:
            broker_type: The broker type to register.
            broker_cls: The concrete Broker subclass.

        Raises:
            BrokerError: If broker_type is already registered.
        """
        if broker_type in self._registry:
            raise BrokerError(f"Broker '{broker_type.value}' is already registered.")
        if not issubclass(broker_cls, Broker):
            raise BrokerError(
                f"{broker_cls.__name__} must implement the Broker interface."
            )
        self._registry[broker_type] = broker_cls

    def create(
        self,
        broker_type: BrokerType,
        **kwargs: object,
    ) -> Broker:
        """Create a broker instance for the given type.

        Args:
            broker_type: The broker type to instantiate.
            **kwargs: Configuration arguments forwarded to the constructor.

        Returns:
            An instance of the registered Broker implementation.

        Raises:
            BrokerError: If no implementation is registered for broker_type.
        """
        cls = self._registry.get(broker_type)
        if cls is None:
            raise BrokerError(
                f"No broker registered for '{broker_type.value}'. "
                f"Available: {[b.value for b in self._registry]}"
            )
        return cls(**kwargs)

    def supported_brokers(self) -> list[BrokerType]:
        """Return the list of registered broker types."""
        return list(self._registry.keys())
