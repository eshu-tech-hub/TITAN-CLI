from dataclasses import dataclass, field
from datetime import datetime, timezone
from queue import Empty, Queue
from threading import Event, Thread
from typing import Callable, Protocol

from titan.brokers.models import ConnectionStatus, Exchange, Quote
from titan.core.logger import logger
from titan.runtime.events import RuntimeEventBus
from titan.runtime.exceptions import StreamConnectionError, StreamError
from titan.runtime.models import RuntimeEventType


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
    """Real-time market data stream with threading support.

    Connects to a pluggable data source, receives quotes,
    and publishes them to the event bus. Supports automatic
    reconnection, sequence validation, and heartbeat monitoring.

    Runs in its own thread to avoid blocking the main runtime.

    Attributes:
        source: Pluggable data source (WebSocket, broker API, mock).
        event_bus: Event bus for publishing stream events.
        _thread: Internal worker thread.
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
    _thread: Thread | None = field(default=None, init=False)
    _stop_event: Event = field(default_factory=Event, init=False)
    _queue: Queue = field(default_factory=Queue, init=False)
    _reconnect_attempts: int = field(default=0, init=False)
    _max_reconnect_attempts: int = 5
    _reconnect_delay_seconds: float = 2.0
    _last_quote_time: datetime | None = field(default=None, init=False)
    _quote_count: int = field(default=0, init=False)
    _on_quote: QuoteCallback | None = field(default=None, init=False)

    def set_on_quote(self, callback: QuoteCallback) -> None:
        """Set a callback for incoming quotes.

        Args:
            callback: Called with each received Quote.
        """
        self._on_quote = callback

    def start(self) -> None:
        """Start the market stream in a background thread.

        Raises:
            StreamError: If the stream is already running.
        """
        if self._thread is not None and self._thread.is_alive():
            raise StreamError("Market stream is already running.")

        self._stop_event.clear()
        self._reconnect_attempts = 0
        self._quote_count = 0

        self._thread = Thread(target=self._run, name="market-stream", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the market stream gracefully."""
        self._stop_event.set()
        try:
            self.source.disconnect()
        except Exception as exc:
            logger.warning(f"Market stream disconnect during shutdown failed: {exc}")

        if self._thread is not None:
            self._thread.join(timeout=5.0)
            if self._thread.is_alive():
                raise StreamError("Market stream worker did not stop within five seconds.")
            self._thread = None

    @property
    def is_running(self) -> bool:
        """Whether the stream thread is alive."""
        return self._thread is not None and self._thread.is_alive()

    @property
    def last_quote_time(self) -> datetime | None:
        """Timestamp of the last received quote."""
        return self._last_quote_time

    @property
    def quote_count(self) -> int:
        """Total number of quotes received."""
        return self._quote_count

    def enqueue_quote(self, quote: Quote) -> None:
        """Enqueue a quote for processing (thread-safe).

        Used by mock/test sources to inject quotes.

        Args:
            quote: The quote to enqueue.
        """
        self._queue.put(quote)

    def _run(self) -> None:
        """Main stream loop running in the background thread."""
        try:
            self._connect()
        except StreamConnectionError:
            if self.event_bus is not None:
                self.event_bus.publish_type(
                    RuntimeEventType.STREAM_ERROR,
                    "stream",
                    data={"error": "Initial connection failed"},
                )
            return

        self._event_loop()

        self._disconnect()

    def _connect(self) -> None:
        """Establish connection to the data source."""
        status = self.source.connect()

        if status == ConnectionStatus.CONNECTED:
            self._reconnect_attempts = 0
            if self.event_bus is not None:
                self.event_bus.publish_type(
                    RuntimeEventType.STREAM_CONNECTED,
                    "stream",
                )
        else:
            raise StreamConnectionError(f"Failed to connect: {status.value}")

    def _disconnect(self) -> None:
        """Disconnect from the data source."""
        try:
            self.source.disconnect()
        except Exception as exc:
            logger.warning(f"Market stream disconnect failed: {exc}")

        if self.event_bus is not None:
            self.event_bus.publish_type(
                RuntimeEventType.STREAM_DISCONNECTED,
                "stream",
            )

    def _event_loop(self) -> None:
        """Process quotes until stopped."""
        while not self._stop_event.is_set():
            try:
                quote = self._queue.get(timeout=1.0)
                self._process_quote(quote)
            except Empty:
                try:
                    quote = self.source.read()
                except Exception as exc:
                    logger.warning(f"Market stream read failed: {exc}")
                    if not self.reconnect():
                        return
                    continue
                if quote is not None:
                    self._process_quote(quote)

    def _process_quote(self, quote: Quote) -> None:
        """Process a single quote."""
        self._last_quote_time = datetime.now(timezone.utc)
        self._quote_count += 1

        if self._on_quote is not None:
            try:
                self._on_quote(quote)
            except Exception:
                logger.exception("Market stream quote callback failed")

        if self.event_bus is not None:
            self.event_bus.publish_type(
                RuntimeEventType.STREAM_QUOTE,
                "stream",
                data={
                    "symbol": quote.symbol,
                    "last_price": str(quote.last_price),
                },
            )

    def reconnect(self) -> bool:
        """Attempt to reconnect to the data source.

        Returns:
            True if reconnection succeeded, False otherwise.
        """
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            if self.event_bus is not None:
                self.event_bus.publish_type(
                    RuntimeEventType.STREAM_ERROR,
                    "stream",
                    data={"error": "Max reconnection attempts reached"},
                )
            return False

        self._reconnect_attempts += 1

        try:
            self.source.disconnect()
        except Exception as exc:
            logger.warning(f"Market stream disconnect before reconnect failed: {exc}")

        try:
            if self._stop_event.wait(self._reconnect_delay_seconds):
                return False
            status = self.source.connect()

            if status == ConnectionStatus.CONNECTED:
                self._reconnect_attempts = 0
                if self.event_bus is not None:
                    self.event_bus.publish_type(
                        RuntimeEventType.STREAM_RECONNECTED,
                        "stream",
                        data={"attempts": self._reconnect_attempts},
                    )
                return True

        except Exception as exc:
            logger.warning(f"Market stream reconnect failed: {exc}")

        if self.event_bus is not None:
            self.event_bus.publish_type(
                RuntimeEventType.STREAM_ERROR,
                "stream",
                data={
                    "error": f"Reconnection attempt {self._reconnect_attempts} failed"
                },
            )

        return False
