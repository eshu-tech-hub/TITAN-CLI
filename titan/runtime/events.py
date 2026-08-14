from dataclasses import dataclass, field
from threading import RLock
from typing import Callable

from titan.core.logger import logger
from titan.runtime.models import RuntimeEvent, RuntimeEventType

EventListener = Callable[[RuntimeEvent], None]


@dataclass(slots=True)
class RuntimeEventBus:
    """Simple pub/sub event bus for runtime communication.

    Allows components to publish events and subscribe to
    specific event types. Supports future integration with
    monitoring, logging, and external systems.

    Attributes:
        _listeners: Mapping of event types to listener callbacks.
    """

    _listeners: dict[RuntimeEventType, list[EventListener]] = field(
        default_factory=dict, init=False
    )
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)

    def subscribe(self, event_type: RuntimeEventType, listener: EventListener) -> None:
        """Register a listener for a specific event type.

        Args:
            event_type: The event type to listen for.
            listener: Callback invoked when the event is published.

        Raises:
            ValueError: If listener is not callable.
        """
        if not callable(listener):
            raise ValueError("Listener must be callable.")
        with self._lock:
            if event_type not in self._listeners:
                self._listeners[event_type] = []
            self._listeners[event_type].append(listener)

    def unsubscribe(
        self, event_type: RuntimeEventType, listener: EventListener
    ) -> None:
        """Remove a previously registered listener.

        Args:
            event_type: The event type to unsubscribe from.
            listener: The listener to remove.
        """
        with self._lock:
            if event_type in self._listeners:
                self._listeners[event_type] = [
                    registered
                    for registered in self._listeners[event_type]
                    if registered is not listener
                ]

    def publish(self, event: RuntimeEvent) -> None:
        """Publish an event to all registered listeners.

        Args:
            event: The event to publish.
        """
        with self._lock:
            listeners = tuple(self._listeners.get(event.event_type, ()))
        for listener in listeners:
            try:
                listener(event)
            except Exception:
                logger.exception(
                    f"Runtime event listener failed for {event.event_type.value}"
                )

    def publish_type(
        self,
        event_type: RuntimeEventType,
        source: str,
        data: dict | None = None,
    ) -> None:
        """Convenience method to publish an event by type and source.

        Args:
            event_type: Type of event.
            source: Component name that produced the event.
            data: Optional event payload.
        """
        from titan.runtime.models import RuntimeEvent

        event = RuntimeEvent(
            event_type=event_type,
            source=source,
            data=data or {},
        )
        self.publish(event)

    def clear(self) -> None:
        """Remove all listeners."""
        with self._lock:
            self._listeners.clear()

    def listener_count(self, event_type: RuntimeEventType) -> int:
        """Get the number of listeners for an event type.

        Args:
            event_type: The event type.

        Returns:
            Number of registered listeners.
        """
        with self._lock:
            return len(self._listeners.get(event_type, []))
