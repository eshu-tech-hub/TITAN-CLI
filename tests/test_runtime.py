from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from titan.brokers.models import ConnectionStatus, Exchange, Quote
from titan.paper.broker import PaperBroker
from titan.runtime.events import RuntimeEventBus
from titan.runtime.exceptions import (
    HealthError,
    HeartbeatError,
    RuntimeError,
    SchedulerError,
    StreamConnectionError,
    StreamError,
    SubscriptionError,
)
from titan.runtime.health import HealthCheck
from titan.runtime.supervisor import RuntimeSupervisor
from titan.runtime.models import (
    ComponentHealth,
    HealthStatus,
    RuntimeEvent,
    RuntimeEventType,
    RuntimeReport,
    RuntimeStatus,
    Subscription,
    SubscriptionType,
)
from titan.runtime.runtime import RuntimeEngine
from titan.runtime.scheduler import PipelineScheduler
from titan.runtime.stream import MarketStream
from titan.runtime.subscriptions import SubscriptionManager

# ── Mock Stream Data Source ──────────────────────────────────────


@dataclass
class MockStreamSource:
    """Mock stream data source implementing StreamDataSource protocol."""

    _connected: bool = False
    quotes: list[Quote] = field(default_factory=list)
    _quote_index: int = 0

    def connect(self) -> ConnectionStatus:
        self._connected = True
        return ConnectionStatus.CONNECTED

    def disconnect(self) -> ConnectionStatus:
        self._connected = False
        return ConnectionStatus.DISCONNECTED

    def is_connected(self) -> bool:
        return self._connected

    def subscribe(self, symbol: str, exchange: Exchange) -> None:
        pass

    def unsubscribe(self, symbol: str, exchange: Exchange) -> None:
        pass

    def read(self) -> Quote | None:
        if self._quote_index < len(self.quotes):
            q = self.quotes[self._quote_index]
            self._quote_index += 1
            return q
        return None


class FailingStreamSource:
    """Mock stream source that fails to connect."""

    def connect(self) -> ConnectionStatus:
        return ConnectionStatus.ERROR

    def disconnect(self) -> ConnectionStatus:
        return ConnectionStatus.DISCONNECTED

    def is_connected(self) -> bool:
        return False

    def subscribe(self, symbol: str, exchange: Exchange) -> None:
        pass

    def unsubscribe(self, symbol: str, exchange: Exchange) -> None:
        pass

    def read(self) -> Quote | None:
        return None


def make_quote(symbol: str = "TEST") -> Quote:
    return Quote(
        symbol=symbol,
        exchange=Exchange.NSE,
        last_price=Decimal("100.0"),
        bid=Decimal("99.5"),
        ask=Decimal("100.5"),
        timestamp=datetime.now(timezone.utc),
    )


# ── Exceptions ───────────────────────────────────────────────────


class TestRuntimeExceptions:
    def test_hierarchy(self) -> None:
        assert issubclass(StreamError, RuntimeError)
        assert issubclass(StreamConnectionError, StreamError)
        assert issubclass(SchedulerError, RuntimeError)
        assert issubclass(SubscriptionError, RuntimeError)
        assert issubclass(HeartbeatError, RuntimeError)
        assert issubclass(HealthError, RuntimeError)

    def test_exception_messages(self) -> None:
        assert str(RuntimeError("fail")) == "fail"
        assert str(StreamError("stream down")) == "stream down"


# ── Models ───────────────────────────────────────────────────────


class TestRuntimeStatus:
    def test_enum_values(self) -> None:
        assert RuntimeStatus.STOPPED.name == "STOPPED"
        assert RuntimeStatus.RUNNING.name == "RUNNING"
        assert RuntimeStatus.PAUSED.name == "PAUSED"
        assert RuntimeStatus.ERROR.name == "ERROR"


class TestRuntimeEventType:
    def test_enum_values(self) -> None:
        assert RuntimeEventType.RUNTIME_STARTED.name == "RUNTIME_STARTED"
        assert RuntimeEventType.STREAM_QUOTE.name == "STREAM_QUOTE"
        assert RuntimeEventType.HEARTBEAT_TICK.name == "HEARTBEAT_TICK"
        assert RuntimeEventType.HEALTH_OK.name == "HEALTH_OK"


class TestRuntimeEvent:
    def test_construction(self) -> None:
        event = RuntimeEvent(
            event_type=RuntimeEventType.RUNTIME_STARTED,
            source="test",
        )
        assert event.event_type == RuntimeEventType.RUNTIME_STARTED
        assert event.source == "test"

    def test_with_data(self) -> None:
        event = RuntimeEvent(
            event_type=RuntimeEventType.STREAM_QUOTE,
            source="stream",
            data={"symbol": "NIFTY", "price": "100"},
        )
        assert event.data["symbol"] == "NIFTY"


class TestSubscription:
    def test_construction(self) -> None:
        sub = Subscription(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
        )
        assert sub.symbol == "RELIANCE"
        assert sub.enabled

    def test_custom_type(self) -> None:
        sub = Subscription(
            symbol="NIFTY",
            exchange=Exchange.NFO,
            subscription_type=SubscriptionType.INDEX,
            enabled=False,
        )
        assert sub.subscription_type == SubscriptionType.INDEX
        assert not sub.enabled

    def test_is_frozen(self) -> None:
        sub = Subscription(symbol="TEST", exchange=Exchange.NSE)
        with pytest.raises(AttributeError):
            sub.symbol = "OTHER"  # type: ignore[misc]


class TestComponentHealth:
    def test_default_construction(self) -> None:
        ch = ComponentHealth(component_name="stream")
        assert ch.status == HealthStatus.UNKNOWN
        assert ch.latency_ms == 0.0

    def test_is_frozen(self) -> None:
        ch = ComponentHealth(component_name="broker")
        with pytest.raises(AttributeError):
            ch.status = HealthStatus.HEALTHY  # type: ignore[misc]


class TestRuntimeReport:
    def test_default_construction(self) -> None:
        report = RuntimeReport(
            runtime_status=RuntimeStatus.STOPPED,
        )
        assert report.runtime_status == RuntimeStatus.STOPPED
        assert report.uptime_seconds == 0.0

    def test_is_frozen(self) -> None:
        report = RuntimeReport(runtime_status=RuntimeStatus.RUNNING)
        with pytest.raises(AttributeError):
            report.runtime_status = RuntimeStatus.PAUSED  # type: ignore[misc]


# ── Event Bus ────────────────────────────────────────────────────


class TestRuntimeEventBus:
    def test_subscribe_and_publish(self) -> None:
        bus = RuntimeEventBus()
        received: list[RuntimeEvent] = []

        def listener(event: RuntimeEvent) -> None:
            received.append(event)

        bus.subscribe(RuntimeEventType.RUNTIME_STARTED, listener)
        event = RuntimeEvent(
            event_type=RuntimeEventType.RUNTIME_STARTED,
            source="test",
        )
        bus.publish(event)
        assert len(received) == 1
        assert received[0].source == "test"

    def test_unsubscribe(self) -> None:
        bus = RuntimeEventBus()
        received: list[RuntimeEvent] = []

        def listener(event: RuntimeEvent) -> None:
            received.append(event)

        bus.subscribe(RuntimeEventType.RUNTIME_STARTED, listener)
        bus.unsubscribe(RuntimeEventType.RUNTIME_STARTED, listener)
        bus.publish_type(RuntimeEventType.RUNTIME_STARTED, "test")
        assert len(received) == 0

    def test_multiple_listeners(self) -> None:
        bus = RuntimeEventBus()
        count: list[int] = [0]

        def listener1(event: RuntimeEvent) -> None:
            count[0] += 1

        def listener2(event: RuntimeEvent) -> None:
            count[0] += 1

        bus.subscribe(RuntimeEventType.HEARTBEAT_TICK, listener1)
        bus.subscribe(RuntimeEventType.HEARTBEAT_TICK, listener2)
        bus.publish_type(RuntimeEventType.HEARTBEAT_TICK, "test")
        assert count[0] == 2

    def test_publish_type_convenience(self) -> None:
        bus = RuntimeEventBus()
        received: list[RuntimeEvent] = []

        def listener(event: RuntimeEvent) -> None:
            received.append(event)

        bus.subscribe(RuntimeEventType.STREAM_CONNECTED, listener)
        bus.publish_type(RuntimeEventType.STREAM_CONNECTED, "stream")
        assert len(received) == 1
        assert received[0].source == "stream"

    def test_listener_count(self) -> None:
        bus = RuntimeEventBus()
        assert bus.listener_count(RuntimeEventType.RUNTIME_STARTED) == 0

        def listener(event: RuntimeEvent) -> None:
            pass

        bus.subscribe(RuntimeEventType.RUNTIME_STARTED, listener)
        assert bus.listener_count(RuntimeEventType.RUNTIME_STARTED) == 1

    def test_clear(self) -> None:
        bus = RuntimeEventBus()

        def listener(event: RuntimeEvent) -> None:
            pass

        bus.subscribe(RuntimeEventType.RUNTIME_STARTED, listener)
        bus.clear()
        assert bus.listener_count(RuntimeEventType.RUNTIME_STARTED) == 0

    def test_invalid_listener_raises(self) -> None:
        bus = RuntimeEventBus()
        with pytest.raises(ValueError):
            bus.subscribe(RuntimeEventType.RUNTIME_STARTED, "not_callable")  # type: ignore[arg-type]


# ── Subscription Manager ─────────────────────────────────────────


class TestSubscriptionManager:
    def test_add(self) -> None:
        mgr = SubscriptionManager()
        sub = mgr.add("RELIANCE", Exchange.NSE)
        assert sub.symbol == "RELIANCE"
        assert sub.enabled

    def test_add_duplicate_raises(self) -> None:
        mgr = SubscriptionManager()
        mgr.add("RELIANCE", Exchange.NSE)
        with pytest.raises(SubscriptionError):
            mgr.add("RELIANCE", Exchange.NSE)

    def test_remove(self) -> None:
        mgr = SubscriptionManager()
        mgr.add("RELIANCE", Exchange.NSE)
        mgr.remove("RELIANCE", Exchange.NSE)
        assert mgr.count() == 0

    def test_remove_nonexistent_raises(self) -> None:
        mgr = SubscriptionManager()
        with pytest.raises(SubscriptionError):
            mgr.remove("UNKNOWN", Exchange.NSE)

    def test_get(self) -> None:
        mgr = SubscriptionManager()
        mgr.add("RELIANCE", Exchange.NSE)
        sub = mgr.get("RELIANCE", Exchange.NSE)
        assert sub is not None
        assert sub.symbol == "RELIANCE"

    def test_get_nonexistent(self) -> None:
        mgr = SubscriptionManager()
        assert mgr.get("UNKNOWN", Exchange.NSE) is None

    def test_list_active(self) -> None:
        mgr = SubscriptionManager()
        mgr.add("A", Exchange.NSE)
        mgr.add("B", Exchange.NSE)
        sub = mgr.get("A", Exchange.NSE)
        if sub is not None:
            mgr.disable("A", Exchange.NSE)
        active = mgr.list_active()
        assert len(active) == 1

    def test_list_all(self) -> None:
        mgr = SubscriptionManager()
        mgr.add("A", Exchange.NSE)
        mgr.add("B", Exchange.BSE)
        assert len(mgr.list_all()) == 2

    def test_enable_disable(self) -> None:
        mgr = SubscriptionManager()
        mgr.add("A", Exchange.NSE)
        mgr.disable("A", Exchange.NSE)
        assert not mgr.get("A", Exchange.NSE).enabled
        mgr.enable("A", Exchange.NSE)
        assert mgr.get("A", Exchange.NSE).enabled

    def test_symbols(self) -> None:
        mgr = SubscriptionManager()
        mgr.add("A", Exchange.NSE)
        mgr.add("B", Exchange.NSE)
        assert len(mgr.symbols()) == 2

    def test_count(self) -> None:
        mgr = SubscriptionManager()
        assert mgr.count() == 0
        mgr.add("A", Exchange.NSE)
        assert mgr.count() == 1

    def test_clear(self) -> None:
        mgr = SubscriptionManager()
        mgr.add("A", Exchange.NSE)
        mgr.clear()
        assert mgr.count() == 0

    def test_with_event_bus(self) -> None:
        bus = RuntimeEventBus()
        mgr = SubscriptionManager(event_bus=bus)
        received: list[RuntimeEvent] = []

        def listener(event: RuntimeEvent) -> None:
            received.append(event)

        bus.subscribe(RuntimeEventType.SUBSCRIPTION_ADDED, listener)
        mgr.add("TEST", Exchange.NSE)
        assert len(received) == 1

    def test_different_exchanges(self) -> None:
        mgr = SubscriptionManager()
        mgr.add("A", Exchange.NSE)
        mgr.add("A", Exchange.BSE)
        assert mgr.count() == 2


# ── Market Stream ────────────────────────────────────────────────


class TestMarketStream:
    def test_construction(self) -> None:
        source = MockStreamSource()
        stream = MarketStream(source=source)
        assert not stream.is_running

    def test_start_stop(self) -> None:
        source = MockStreamSource()
        stream = MarketStream(source=source)
        stream.start()
        assert stream.is_running
        stream.stop()
        assert not stream.is_running

    def test_double_start_raises(self) -> None:
        source = MockStreamSource()
        stream = MarketStream(source=source)
        stream.start()
        with pytest.raises(StreamError):
            stream.start()
        stream.stop()

    def test_event_bus_integration(self) -> None:
        bus = RuntimeEventBus()
        source = MockStreamSource()
        stream = MarketStream(source=source, event_bus=bus)
        received: list[RuntimeEvent] = []

        def listener(event: RuntimeEvent) -> None:
            received.append(event)

        bus.subscribe(RuntimeEventType.STREAM_CONNECTED, listener)
        stream.start()
        import time

        time.sleep(0.1)
        stream.stop()
        assert len(received) >= 1

    def test_on_quote_callback(self) -> None:
        source = MockStreamSource()
        stream = MarketStream(source=source)
        received_quotes: list[Quote] = []

        def on_quote(quote: Quote) -> None:
            received_quotes.append(quote)

        stream.set_on_quote(on_quote)
        quote = make_quote()
        stream.enqueue_quote(quote)
        stream.start()
        import time

        time.sleep(0.1)
        stream.stop()
        assert len(received_quotes) >= 1

    def test_last_quote_time(self) -> None:
        source = MockStreamSource()
        stream = MarketStream(source=source)
        assert stream.last_quote_time is None
        quote = make_quote()
        stream.enqueue_quote(quote)
        stream.start()
        import time

        time.sleep(0.1)
        stream.stop()
        assert stream.last_quote_time is not None
        assert stream.quote_count >= 1

    def test_failing_source_does_not_crash(self) -> None:
        source = FailingStreamSource()
        stream = MarketStream(source=source)
        stream.start()
        import time

        time.sleep(0.1)
        stream.stop()
        assert not stream.is_running


# ── Pipeline Scheduler ───────────────────────────────────────────


class TestPipelineScheduler:
    def test_construction(self) -> None:
        scheduler = PipelineScheduler()
        assert not scheduler.is_running
        assert scheduler.execution_count == 0

    def test_start_without_runner_raises(self) -> None:
        scheduler = PipelineScheduler(runner=None)
        with pytest.raises(SchedulerError):
            scheduler.start()

    def test_start_stop(self) -> None:
        results: list[int] = []

        def runner() -> int:
            results.append(1)
            return 1

        scheduler = PipelineScheduler(runner=runner, interval_seconds=0.05)
        scheduler.start()
        import time

        time.sleep(0.12)
        scheduler.stop()
        assert not scheduler.is_running
        assert scheduler.execution_count >= 1
        assert len(results) >= 1

    def test_double_start_raises(self) -> None:
        def runner() -> None:
            pass

        scheduler = PipelineScheduler(runner=runner)
        scheduler.start()
        with pytest.raises(SchedulerError):
            scheduler.start()
        scheduler.stop()

    def test_pause_resume(self) -> None:
        count: list[int] = [0]

        def runner() -> None:
            count[0] += 1

        scheduler = PipelineScheduler(runner=runner, interval_seconds=0.02)
        scheduler.start()
        import time

        time.sleep(0.05)
        scheduler.pause()
        assert scheduler.is_paused
        prev_count = count[0]
        time.sleep(0.1)
        assert count[0] == prev_count
        scheduler.resume()
        assert not scheduler.is_paused
        scheduler.stop()

    def test_pause_not_running_raises(self) -> None:
        scheduler = PipelineScheduler()
        with pytest.raises(SchedulerError):
            scheduler.pause()

    def test_resume_not_running_raises(self) -> None:
        scheduler = PipelineScheduler()
        with pytest.raises(SchedulerError):
            scheduler.resume()

    def test_execute_once(self) -> None:
        def runner() -> str:
            return "done"

        scheduler = PipelineScheduler(runner=runner)
        result = scheduler.execute_once()
        assert result == "done"

    def test_execute_once_no_runner_raises(self) -> None:
        scheduler = PipelineScheduler()
        with pytest.raises(SchedulerError):
            scheduler.execute_once()

    def test_last_execution_time(self) -> None:
        def runner() -> None:
            pass

        scheduler = PipelineScheduler(runner=runner, interval_seconds=0.02)
        scheduler.start()
        import time

        time.sleep(0.05)
        scheduler.stop()
        assert scheduler.last_execution_time is not None


# ── Health Check ─────────────────────────────────────────────────


class TestHealthCheck:
    def test_register(self) -> None:
        hc = HealthCheck()
        health = hc.register("stream")
        assert health.component_name == "stream"
        assert health.status == HealthStatus.UNKNOWN

    def test_register_duplicate_raises(self) -> None:
        hc = HealthCheck()
        hc.register("stream")
        with pytest.raises(HealthError):
            hc.register("stream")

    def test_unregister(self) -> None:
        hc = HealthCheck()
        hc.register("stream")
        hc.unregister("stream")
        assert hc.get("stream") is None

    def test_unregister_nonexistent_raises(self) -> None:
        hc = HealthCheck()
        with pytest.raises(HealthError):
            hc.unregister("unknown")

    def test_report_healthy(self) -> None:
        hc = HealthCheck()
        hc.report_healthy("stream")
        health = hc.get("stream")
        assert health is not None
        assert health.status == HealthStatus.HEALTHY

    def test_report_degraded(self) -> None:
        hc = HealthCheck()
        hc.report_degraded("stream", error="high latency")
        health = hc.get("stream")
        assert health is not None
        assert health.status == HealthStatus.DEGRADED
        assert health.error == "high latency"

    def test_report_unhealthy(self) -> None:
        hc = HealthCheck()
        hc.report_unhealthy("stream", error="connection lost")
        health = hc.get("stream")
        assert health is not None
        assert health.status == HealthStatus.UNHEALTHY

    def test_all_health(self) -> None:
        hc = HealthCheck()
        hc.register("a")
        hc.register("b")
        assert len(hc.all_health()) == 2

    def test_is_healthy(self) -> None:
        hc = HealthCheck()
        hc.report_healthy("a")
        hc.report_healthy("b")
        assert hc.is_healthy()

    def test_is_healthy_with_degraded(self) -> None:
        hc = HealthCheck()
        hc.report_healthy("a")
        hc.report_degraded("b")
        assert not hc.is_healthy()

    def test_has_degraded(self) -> None:
        hc = HealthCheck()
        hc.report_degraded("a")
        assert hc.has_degraded()

    def test_has_unhealthy(self) -> None:
        hc = HealthCheck()
        hc.report_unhealthy("a")
        assert hc.has_unhealthy()

    def test_summary(self) -> None:
        hc = HealthCheck()
        hc.report_healthy("a")
        hc.report_unhealthy("b")
        summary = hc.summary()
        assert summary["a"] == "healthy"
        assert summary["b"] == "unhealthy"

    def test_reset(self) -> None:
        hc = HealthCheck()
        hc.report_healthy("a")
        hc.reset()
        assert len(hc.all_health()) == 0


# ── Runtime Engine ───────────────────────────────────────────────


class TestRuntimeEngine:
    def test_construction(self) -> None:
        broker = PaperBroker()
        engine = RuntimeEngine(broker=broker)
        assert engine.status == RuntimeStatus.STOPPED
        assert not engine.is_running

    def test_start_stop(self) -> None:
        broker = PaperBroker()
        engine = RuntimeEngine(broker=broker)
        engine.start()
        assert engine.is_running
        assert engine.status == RuntimeStatus.RUNNING
        engine.stop()
        assert engine.status == RuntimeStatus.STOPPED

    def test_double_start_raises(self) -> None:
        broker = PaperBroker()
        engine = RuntimeEngine(broker=broker)
        engine.start()
        with pytest.raises(RuntimeError):
            engine.start()
        engine.stop()

    def test_pause_resume(self) -> None:
        broker = PaperBroker()
        engine = RuntimeEngine(broker=broker)
        engine.start()
        engine.pause()
        assert engine.status == RuntimeStatus.PAUSED
        engine.resume()
        assert engine.status == RuntimeStatus.RUNNING
        engine.stop()

    def test_pause_not_running_raises(self) -> None:
        broker = PaperBroker()
        engine = RuntimeEngine(broker=broker)
        with pytest.raises(RuntimeError):
            engine.pause()

    def test_resume_not_paused_raises(self) -> None:
        broker = PaperBroker()
        engine = RuntimeEngine(broker=broker)
        engine.start()
        with pytest.raises(RuntimeError):
            engine.resume()
        engine.stop()

    def test_restart(self) -> None:
        broker = PaperBroker()
        engine = RuntimeEngine(broker=broker)
        engine.start()
        engine.restart()
        assert engine.is_running
        engine.stop()

    def test_uptime(self) -> None:
        broker = PaperBroker()
        engine = RuntimeEngine(broker=broker)
        assert engine.uptime_seconds == 0.0
        engine.start()
        import time

        time.sleep(0.05)
        assert engine.uptime_seconds > 0
        engine.stop()

    def test_generate_report_stopped(self) -> None:
        broker = PaperBroker()
        engine = RuntimeEngine(broker=broker)
        report = engine.generate_report()
        assert isinstance(report, RuntimeReport)
        assert report.runtime_status == RuntimeStatus.STOPPED

    def test_generate_report_running(self) -> None:
        broker = PaperBroker()
        engine = RuntimeEngine(broker=broker)
        engine.start()
        report = engine.generate_report()
        assert report.runtime_status == RuntimeStatus.RUNNING
        engine.stop()

    def test_broker_connected(self) -> None:
        broker = PaperBroker()
        engine = RuntimeEngine(broker=broker)
        engine.start()
        assert broker.is_connected()
        engine.stop()
        assert not broker.is_connected()

    def test_with_stream(self) -> None:
        broker = PaperBroker()
        source = MockStreamSource()
        stream = MarketStream(source=source)
        engine = RuntimeEngine(broker=broker, stream=stream)
        engine.start()
        assert engine.stream is not None
        assert engine.stream.is_running
        engine.stop()

    def test_with_scheduler(self) -> None:
        broker = PaperBroker()
        scheduler = PipelineScheduler(interval_seconds=0.05)
        engine = RuntimeEngine(broker=broker, scheduler=scheduler)
        engine.start()
        import time

        time.sleep(0.12)
        engine.stop()
        assert scheduler.is_running is False  # stopped
        assert engine._pipeline_executions >= 1  # internal runner executed

    def test_with_supervisor(self) -> None:
        broker = PaperBroker()
        supervisor = RuntimeSupervisor()
        engine = RuntimeEngine(broker=broker, supervisor=supervisor)
        engine.start()
        engine.stop()

    def test_health_checks_registered(self) -> None:
        broker = PaperBroker()
        engine = RuntimeEngine(broker=broker)
        health_components = {h.component_name for h in engine.health.all_health()}
        assert "runtime" in health_components
        assert "broker" in health_components
        assert "stream" in health_components
        assert "scheduler" in health_components
        assert "supervisor" in health_components

    def test_broker_connect_health(self) -> None:
        broker = PaperBroker()
        engine = RuntimeEngine(broker=broker)
        engine.start()
        health = engine.health.get("broker")
        assert health is not None
        assert health.status == HealthStatus.HEALTHY
        engine.stop()

    def test_subscription_manager_wired(self) -> None:
        broker = PaperBroker()
        engine = RuntimeEngine(broker=broker)
        assert engine.subscriptions is not None
        assert engine.subscriptions.event_bus is engine.event_bus


# ── Health Status Enum ───────────────────────────────────────────


class TestHealthStatus:
    def test_enum_values(self) -> None:
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.UNKNOWN.value == "unknown"


# ── SubscriptionType Enum ────────────────────────────────────────


class TestSubscriptionType:
    def test_enum_values(self) -> None:
        assert SubscriptionType.SYMBOL.name == "SYMBOL"
        assert SubscriptionType.OPTION_CHAIN.name == "OPTION_CHAIN"
        assert SubscriptionType.INDEX.name == "INDEX"
        assert SubscriptionType.WATCHLIST.name == "WATCHLIST"
        assert SubscriptionType.MARKET_DEPTH.name == "MARKET_DEPTH"
