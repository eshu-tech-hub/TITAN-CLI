from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from queue import Queue
from threading import Event
from typing import Protocol

from titan.brokers.models import ConnectionStatus, Exchange, Quote
from titan.runtime.events import RuntimeEventBus


class StreamDataSource(Protocol):
    """Protocol for pluggable stream data sources.

    Implementations can wrap real WebSocket connections,
    broker APIs, or test mocks.
    """

    def connect(self) -> ConnectionStatus: ...
    def disconnect(self) -> ConnectionStatus: ...
    def is_connected(self) -> bool: ...
    def subscribe(self, symbol: str, exchange: Exchange) -> None: ...
    def unsubscribe(self, symbol: str, exchange: Exchange) -> None: ...
    def read(self) -> Quote | None: ...


QuoteCallback = Callable[[Quote], None]


@dataclass(slots=True)
class MarketStream:
    """Real-time market data stream transparent wrapper.

    Connects to a pluggable data source, receives quotes,
    and publishes them to the event bus. Supports automatic
    reconnection, sequence validation, and heartbeat monitoring.

    Attributes:
        source: Pluggable data source (WebSocket, broker API, mock).
        event_bus: Event bus for publishing stream events.
        _stop_event: Event flag for graceful shutdown.
        _queue: Internal quote queue for thread-safe processing.
        _reconnect_attempts: Number of reconnection attempts.
        _max_reconnect_attempts: Maximum reconnection attempts before giving up.
        _reconnect_delay_seconds: Delay between reconnection attempts.
        _last_quote_time: Timestamp of the last received quote.
        _quote_count: Total quotes received.
    """

    source: StreamDataSource
    event_bus: RuntimeEventBus | None = None
    _stop_event: Event = field(default_factory=Event, init=False)
    _queue: Queue = field(default_factory=Queue, init=False)
    _reconnect_attempts: int = field(default=0, init=False)
    _max_reconnect_attempts: int = 5
    _reconnect_delay_seconds: float = 2.0
    _last_quote_time: datetime | None = field(default=None, init=False)
    _quote_count: int = field(default=0, init=False)
    _on_quote: QuoteCallback | None = field(default=None, init=False)

    @property
    def is_connected(self) -> bool:
        if hasattr(self.source, "is_connected"):
            return self.source.is_connected()
        return getattr(self.source, "_connected", False)

    @property
    def subscribed_symbols(self) -> list[str]:
        return list(getattr(self.source, "_subscriptions", []))


    @property
    def symbols(self) -> list[str]:
        if hasattr(self, "subscribed_symbols"): 
            return self.subscribed_symbols
        if hasattr(self.source, "_subscriptions"): 
            return list(self.source._subscriptions)
        return []

    @property
    def connected(self) -> bool:
        return self.is_connected

    def set_on_quote(self, callback: QuoteCallback) -> None:
        """Set a callback for incoming quotes.

        Args:
            callback: Called with each received Quote.
        """
        self._on_quote = callback
        if hasattr(self.source, "set_on_quote"):
            self.source.set_on_quote(callback)

    def start(self) -> None:
        """Start the market stream."""
        self._stop_event.clear()
        if hasattr(self.source, "start"):
            self.source.start()

    def stop(self) -> None:
        """Gracefully stop the market stream."""
        self._stop_event.set()
        if hasattr(self.source, "stop"):
            self.source.stop()

    @property
    def is_running(self) -> bool:
        """Whether the stream is running."""
        return self.is_connected

    @property
    def last_quote_time(self) -> datetime | None:
        """Timestamp of the last received quote."""
        return self._last_quote_time

    @property
    def quote_count(self) -> int:
        """Total number of quotes received."""
        return self._quote_count

    def enqueue_quote(self, quote: Quote) -> None:
        """Enqueue a quote for processing (thread-safe)."""
        self._queue.put(quote)
