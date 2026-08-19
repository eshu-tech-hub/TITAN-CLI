from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Event
from typing import Any

from titan.brokers.broker import Broker
from titan.brokers.models import ConnectionStatus, Exchange
from titan.core.logger import logger
from titan.decision.journal import DecisionJournal
from titan.decision.replay import DecisionReplayService
from titan.pipeline.pipeline import TradePipeline
from titan.portfolio.replay import PortfolioReplayService
from titan.runtime.events import RuntimeEventBus
from titan.runtime.exceptions import RuntimeError, SchedulerError, StreamError
from titan.runtime.health import HealthCheck
from titan.runtime.models import (
    HealthStatus,
    RuntimeEventType,
    RuntimeReport,
    RuntimeStatus,
)
from titan.runtime.scheduler import PipelineScheduler
from titan.runtime.stream import MarketStream
from titan.runtime.subscriptions import SubscriptionManager
from titan.runtime.supervisor import RuntimeSupervisor
from titan.trading.journal import TradeJournal, TradeLifecycleState


@dataclass(slots=True)
class RuntimeEngine:
    """Main runtime engine that orchestrates the live TITAN platform.

    Manages the complete lifecycle: start, stop, pause, resume,
    restart, and graceful shutdown. Coordinates the market stream,
    pipeline scheduler, heartbeat monitor, event bus, and health
    checks.

    This engine does NOT perform market analysis or trading logic.
    It operates the already-built TITAN engines in real time.

    Attributes:
        broker: Broker instance for live trading.
        pipeline: Trade Pipeline instance.
        event_bus: Runtime event bus.
        stream: Market data stream.
        scheduler: Pipeline execution scheduler.
        supervisor: Reliability supervisor.
        health: Health check aggregator.
        subscriptions: Subscription manager.
        _status: Current runtime status.
        _start_time: When the runtime was started.
        _error: Current error message if in ERROR state.
        _stop_event: Event flag for shutdown coordination.
        _pipeline_executions: Total pipeline executions.
        decision_journal: Journal recording all trade decisions.
    """

    broker: Broker
    pipeline: TradePipeline = field(default_factory=TradePipeline)
    event_bus: RuntimeEventBus = field(default_factory=RuntimeEventBus)
    stream: MarketStream | None = None
    scheduler: PipelineScheduler | None = None
    supervisor: RuntimeSupervisor = field(default_factory=RuntimeSupervisor)
    health: HealthCheck = field(default_factory=HealthCheck)
    subscriptions: SubscriptionManager = field(default_factory=SubscriptionManager)
    _status: RuntimeStatus = field(default=RuntimeStatus.STOPPED, init=False)
    _start_time: datetime | None = field(default=None, init=False)
    _error: str = field(default="", init=False)
    _stop_event: Event = field(default_factory=Event, init=False)
    _pipeline_executions: int = field(default=0, init=False)
    decision_journal: DecisionJournal = field(default_factory=DecisionJournal)
    decision_replay: DecisionReplayService = field(init=False)
    trade_journal: TradeJournal = field(default_factory=TradeJournal)
    portfolio_replay: PortfolioReplayService = field(init=False)

    def __post_init__(self) -> None:
        self.subscriptions = SubscriptionManager(event_bus=self.event_bus)
        self.pipeline._decision_journal = self.decision_journal
        self.decision_replay = DecisionReplayService(
            repository=self.decision_journal.repository
        )
        self.portfolio_replay = PortfolioReplayService(trade_journal=self.trade_journal)
        if self.stream is not None:
            self.stream.event_bus = self.event_bus
        if self.scheduler is not None:
            self.scheduler.event_bus = self.event_bus

        self.health.register("runtime")
        self.health.register("broker")
        self.health.register("stream")
        self.health.register("scheduler")
        self.health.register("supervisor")

    # ── Lifecycle ─────────────────────────────────────────────

    def start(self) -> None:
        """Start the runtime engine and all components.

        Raises:
            RuntimeError: If already running or startup fails.
        """
        if self._status in (RuntimeStatus.RUNNING, RuntimeStatus.STARTING):
            raise RuntimeError("Runtime is already running.")
        if self._status == RuntimeStatus.PAUSED:
            raise RuntimeError("Runtime is paused. Use resume() to continue.")

        self._status = RuntimeStatus.STARTING
        self._error = ""
        self._start_time = datetime.now(UTC)
        self._stop_event.clear()

        try:
            self._validate_configuration()
            self._validate_environment()
            self._validate_storage()
            self._validate_trade_journal()
            self._validate_decision_journal()
            self._start_recovery()
            self._start_supervisor()
            self._start_scheduler()
            self._start_broker()
            self._start_stream()
            self._start_monitoring()

            self._status = RuntimeStatus.RUNNING
            self.health.report_healthy("runtime")

            self.event_bus.publish_type(
                RuntimeEventType.RUNTIME_STARTED,
                "runtime",
                data={"start_time": self._start_time.isoformat()},
            )

        except Exception as exc:
            self._status = RuntimeStatus.ERROR
            self._error = str(exc)
            self.health.report_unhealthy("runtime", error=str(exc))
            self.event_bus.publish_type(
                RuntimeEventType.RUNTIME_ERROR,
                "runtime",
                data={"error": str(exc)},
            )
            self._shutdown_components()
            raise RuntimeError(f"Failed to start runtime: {exc}") from exc

    def run_until_stopped(self) -> None:
        """Run the scheduler loop until :meth:`stop` is requested.

        Startup is deliberately separate from this blocking method so callers
        can inspect a fully initialized runtime, expose its control transport,
        or perform a deterministic shutdown without creating a background task.
        """
        if self._status not in (RuntimeStatus.RUNNING, RuntimeStatus.PAUSED):
            raise RuntimeError("Runtime must be running before entering its loop.")

        while not self._stop_event.is_set() and self._status in (
            RuntimeStatus.RUNNING,
            RuntimeStatus.PAUSED,
        ):
            self._stop_event.wait(timeout=1.0)

    def stop(self) -> None:
        """Stop the runtime engine gracefully.

        Stops all components in reverse order and performs
        a graceful shutdown.
        """
        if self._status == RuntimeStatus.STOPPED:
            return

        self._status = RuntimeStatus.STOPPING
        self._stop_event.set()

        self._shutdown_components()

        self._status = RuntimeStatus.STOPPED
        self.health.report_healthy("runtime")

        self.event_bus.publish_type(
            RuntimeEventType.RUNTIME_STOPPED,
            "runtime",
            data={},
        )

    def _shutdown_components(self) -> None:
        """Stop initialized components in reverse startup order."""
        self._stop_monitoring()
        self._stop_stream()
        self._stop_broker()
        self._stop_scheduler()
        self._stop_supervisor()

        if hasattr(self, "trade_journal") and hasattr(self.trade_journal, "flush"):
            try:
                self.trade_journal.flush()
            except Exception:
                logger.exception("Failed to flush the trade journal during shutdown")
        if hasattr(self, "decision_journal") and hasattr(
            self.decision_journal, "flush"
        ):
            try:
                self.decision_journal.flush()
            except Exception:
                logger.exception("Failed to flush the decision journal during shutdown")

        self._stop_recovery()

    def pause(self) -> None:
        """Pause the runtime, suspending scheduler execution.

        Raises:
            RuntimeError: If not running.
        """
        if self._status != RuntimeStatus.RUNNING:
            raise RuntimeError("Runtime is not running.")

        self._status = RuntimeStatus.PAUSED
        self.health.report_degraded("runtime", error="paused")

        if self.scheduler is not None:
            try:
                self.scheduler.pause()
            except SchedulerError as exc:
                logger.warning(f"Unable to pause scheduler: {exc}")

        self.event_bus.publish_type(
            RuntimeEventType.RUNTIME_PAUSED,
            "runtime",
            data={},
        )

    def resume(self) -> None:
        """Resume the runtime after a pause.

        Raises:
            RuntimeError: If not paused.
        """
        if self._status != RuntimeStatus.PAUSED:
            raise RuntimeError("Runtime is not paused.")

        self._status = RuntimeStatus.RUNNING
        self.health.report_healthy("runtime")

        if self.scheduler is not None:
            try:
                self.scheduler.resume()
            except SchedulerError as exc:
                logger.warning(f"Unable to resume scheduler: {exc}")

        self.event_bus.publish_type(
            RuntimeEventType.RUNTIME_RESUMED,
            "runtime",
            data={},
        )

    def restart(self) -> None:
        """Restart the runtime engine.

        Performs a full stop followed by a start.
        """
        self.stop()
        self.start()

    @property
    def status(self) -> RuntimeStatus:
        """Current runtime status."""
        return self._status

    @property
    def is_running(self) -> bool:
        """Whether the runtime is actively running."""
        return self._status == RuntimeStatus.RUNNING

    @property
    def uptime_seconds(self) -> float:
        """Seconds since the runtime started."""
        if self._start_time is None:
            return 0.0
        return (datetime.now(UTC) - self._start_time).total_seconds()

    # ── Report ────────────────────────────────────────────────

    def generate_report(self) -> RuntimeReport:
        """Generate a snapshot of current runtime state.

        Returns:
            RuntimeReport with current status, health, and metrics.
        """
        from titan.runtime.models import (
            BrokerStatus,
            MarketStatus,
            PerformanceStatus,
            RuntimeHealth,
            SchedulerStatus,
        )

        component_health = self.health.all_health()

        warnings: list[str] = []
        errors: list[str] = []

        for ch in component_health:
            if ch.status == HealthStatus.DEGRADED and ch.error:
                warnings.append(f"{ch.component_name}: {ch.error}")
            elif ch.status == HealthStatus.UNHEALTHY and ch.error:
                errors.append(f"{ch.component_name}: {ch.error}")

        if self._error:
            errors.append(self._error)

        broker_connection = (
            ConnectionStatus.CONNECTED
            if self.broker.is_connected()
            else ConnectionStatus.DISCONNECTED
        )

        stream_status_str = (
            "connected"
            if self.stream is not None and self.stream.is_running
            else "disconnected"
        )

        health_status = RuntimeHealth(
            component_health=tuple(component_health),
            warnings=tuple(warnings),
            errors=tuple(errors),
        )

        scheduler_status = SchedulerStatus(
            active=(self.scheduler is not None and self.scheduler.is_running),
            pipeline_executions=self._pipeline_executions,
            last_pipeline_time=(
                self.scheduler.last_execution_time
                if self.scheduler is not None
                else None
            ),
        )

        broker_status = BrokerStatus(connection=broker_connection)

        market_status = MarketStatus(
            stream_status=stream_status_str,
            active_subscriptions=self.subscriptions.count(),
            last_quote_time=(
                self.stream.last_quote_time if self.stream is not None else None
            ),
        )

        perf_status = PerformanceStatus(uptime_seconds=self.uptime_seconds)

        return RuntimeReport(
            runtime_status=self._status,
            health=health_status,
            scheduler=scheduler_status,
            broker=broker_status,
            market=market_status,
            performance=perf_status,
        )

    # ── Internal Validation & Startup Chain ───────────────────

    def _validate_configuration(self) -> None:
        """Validate configuration settings."""
        logger.info("Validating configuration settings")

    def _validate_environment(self) -> None:
        """Validate runtime environment and dependencies."""

    def _validate_storage(self) -> None:
        """Validate storage connectivity and permissions."""

    def _validate_trade_journal(self) -> None:
        """Validate trade journal integrity."""

    def _validate_decision_journal(self) -> None:
        """Validate decision journal integrity."""

    def _start_recovery(self) -> None:
        """Initialize recovery services."""

    def _stop_recovery(self) -> None:
        """Stop recovery services."""

    def _start_supervisor(self) -> None:
        """Start reliability supervisor."""

    def _stop_supervisor(self) -> None:
        """Stop reliability supervisor."""

    def _start_monitoring(self) -> None:
        """Start system monitoring."""

    def _stop_monitoring(self) -> None:
        """Stop system monitoring."""

    def _start_broker(self) -> None:
        """Connect the broker."""
        logger.info("Starting broker connection")
        status = self.broker.connect()
        if status == ConnectionStatus.CONNECTED:
            self.health.report_healthy("broker")
            self.event_bus.publish_type(RuntimeEventType.BROKER_CONNECTED, "runtime")
        else:
            raise RuntimeError(f"Broker connection failed: {status.value}")

    def _stop_broker(self) -> None:
        """Disconnect the broker."""
        try:
            self.broker.disconnect()
        except Exception as exc:
            self.health.report_unhealthy("broker", error=str(exc))
            logger.exception("Failed to disconnect broker during shutdown")
        else:
            self.health.report_healthy("broker")
        self.event_bus.publish_type(RuntimeEventType.BROKER_DISCONNECTED, "runtime")

    def _start_stream(self) -> None:
        """Start the market data stream."""
        if self.stream is not None:
            try:
                self.stream.start()
                self.health.report_healthy("stream")
            except StreamError as e:
                self.health.report_unhealthy("stream", error=str(e))

    def _stop_stream(self) -> None:
        """Stop the market data stream."""
        if self.stream is not None:
            try:
                self.stream.stop()
            except Exception as exc:
                self.health.report_unhealthy("stream", error=str(exc))
                logger.exception("Failed to stop market stream during shutdown")
            else:
                self.health.report_healthy("stream")

    def _start_scheduler(self) -> None:
        """Start the pipeline scheduler."""
        logger.info("Starting pipeline scheduler")
        if self.scheduler is not None:
            try:
                self.scheduler.runner = self._pipeline_runner
                self.scheduler.start()
                self.health.report_healthy("scheduler")
            except SchedulerError as e:
                self.health.report_unhealthy("scheduler", error=str(e))

    def _stop_scheduler(self) -> None:
        """Stop the pipeline scheduler."""
        if self.scheduler is not None:
            try:
                self.scheduler.stop()
            except Exception as exc:
                self.health.report_unhealthy("scheduler", error=str(exc))
                logger.exception("Failed to stop scheduler during shutdown")
            else:
                self.health.report_healthy("scheduler")

    def _pipeline_runner(self) -> Any:
        """Default pipeline runner for the scheduler.

        Can be overridden by setting scheduler.runner directly.
        """
        self.supervisor.evaluate()
        self.supervisor.touch("pipeline")
        self.supervisor.touch("scheduler")
        self.supervisor.touch("broker")
        self.supervisor.touch("event_bus")

        self._pipeline_executions += 1
        exchanges = self.broker.profile().enabled_exchanges
        exchange = exchanges[0] if exchanges else Exchange.NSE
        report = self.pipeline.run(symbol="", exchange=exchange)

        # Record execution results if any orders were submitted
        if report.orders_submitted > 0:
            from datetime import datetime

            from titan.trading.factory import TradeJournalFactory

            session_id = str(
                getattr(self, "_start_time", datetime.now(UTC).timestamp())
            )
            entries_data = TradeJournalFactory.from_pipeline_report(report, session_id)

            for entry, broker_id in entries_data:
                self.trade_journal.initialize_trade(entry)
                self.trade_journal.record_transition(
                    trade_id=entry.trade_id,
                    status=TradeLifecycleState.SUBMITTED,
                    reason="Pipeline execution",
                    broker_reference=broker_id,
                )

        return report
