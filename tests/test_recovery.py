from dataclasses import FrozenInstanceError
from threading import Thread
from time import sleep

import pytest

from titan.recovery.backoff import BackoffCalculator, get_backoff
from titan.recovery.checkpoint import CheckpointManager
from titan.recovery.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from titan.recovery.exceptions import (
    RecoveryCheckpointError,
    RecoveryCircuitBreakerError,
    RecoveryError,
    RecoveryInputError,
    RecoveryReconnectError,
    RecoveryRetryError,
    RecoveryShutdownError,
    RecoveryStateError,
    RecoveryStrategyError,
    RecoveryTimeoutError,
)
from titan.recovery.health_recovery import HealthRecovery
from titan.recovery.manager import RecoveryManager
from titan.recovery.models import (
    BrokerSessionState,
    Checkpoint,
    CircuitBreakerState,
    ComponentType,
    ReconnectStrategy,
    RecoveryAttempt,
    RecoveryReport,
    RecoveryRequest,
    RecoveryStatus,
    RecoveryStrategy,
    RetryMode,
    RetryPolicy,
    RuntimeStateSnapshot,
    ShutdownPlan,
    ShutdownStage,
)
from titan.recovery.reconnect import BrokerReconnector
from titan.recovery.retry import RetryEngine
from titan.recovery.shutdown import GracefulShutdown
from titan.recovery.state import StateManager

# ---------------------------------------------------------------------------
# Models — frozen dataclasses, enums, defaults
# ---------------------------------------------------------------------------


class TestRetryPolicy:
    def test_defaults(self) -> None:
        p = RetryPolicy()
        assert p.mode is RetryMode.EXPONENTIAL_BACKOFF
        assert p.max_attempts == 3
        assert p.base_delay_seconds == 1.0
        assert p.max_delay_seconds == 60.0
        assert p.timeout_seconds == 0.0
        assert p.retryable_exceptions == (Exception,)
        assert p.jitter_factor == 0.1

    def test_frozen(self) -> None:
        p = RetryPolicy()
        with pytest.raises(FrozenInstanceError):
            p.max_attempts = 5  # type: ignore[misc]


class TestCircuitBreakerConfig:
    def test_defaults(self) -> None:
        c = CircuitBreakerConfig()
        assert c.failure_threshold == 5
        assert c.recovery_timeout_seconds == 30.0
        assert c.success_threshold == 3
        assert c.half_open_max_calls == 1

    def test_frozen(self) -> None:
        c = CircuitBreakerConfig()
        with pytest.raises(FrozenInstanceError):
            c.failure_threshold = 10  # type: ignore[misc]


class TestRecoveryRequest:
    def test_defaults(self) -> None:
        req = RecoveryRequest(
            component=ComponentType.PIPELINE,
            strategy=RecoveryStrategy.RETRY,
            failure_reason="test",
        )
        assert req.metadata == {}
        assert req.retry_policy is None
        assert req.request_id == ""

    def test_frozen(self) -> None:
        req = RecoveryRequest(
            component=ComponentType.BROKER_SESSION,
            strategy=RecoveryStrategy.RECONNECT,
            failure_reason="fail",
        )
        with pytest.raises(FrozenInstanceError):
            req.component = ComponentType.PIPELINE  # type: ignore[misc]


class TestRecoveryAttempt:
    def test_defaults(self) -> None:
        a = RecoveryAttempt(attempt_number=1, strategy=RecoveryStrategy.RETRY)
        assert a.status is RecoveryStatus.PENDING
        assert a.error == ""
        assert a.duration_seconds == 0.0

    def test_frozen(self) -> None:
        a = RecoveryAttempt(attempt_number=1, strategy=RecoveryStrategy.RETRY)
        with pytest.raises(FrozenInstanceError):
            a.status = RecoveryStatus.SUCCESS  # type: ignore[misc]


class TestRecoveryReport:
    def test_defaults(self) -> None:
        r = RecoveryReport(
            request_id="r1",
            component=ComponentType.PIPELINE,
            strategy=RecoveryStrategy.RETRY,
            status=RecoveryStatus.SUCCESS,
        )
        assert r.attempts == ()
        assert r.metadata == {}

    def test_frozen(self) -> None:
        r = RecoveryReport(
            request_id="r1",
            component=ComponentType.MONITORING,
            strategy=RecoveryStrategy.RESTART,
            status=RecoveryStatus.PENDING,
        )
        with pytest.raises(FrozenInstanceError):
            r.status = RecoveryStatus.SUCCESS  # type: ignore[misc]


class TestCheckpoint:
    def test_defaults(self) -> None:
        cp = Checkpoint(
            checkpoint_id="cp1",
            component=ComponentType.PIPELINE,
            state_data={"key": "value"},
        )
        assert cp.version == "1.0.0"
        assert cp.metadata == {}

    def test_frozen(self) -> None:
        cp = Checkpoint(
            checkpoint_id="cp1",
            component=ComponentType.PIPELINE,
            state_data={"k": "v"},
        )
        with pytest.raises(FrozenInstanceError):
            cp.version = "2.0.0"  # type: ignore[misc]


class TestRuntimeStateSnapshot:
    def test_defaults(self) -> None:
        s = RuntimeStateSnapshot()
        assert s.pipeline_progress == {}
        assert s.open_orders == ()
        assert s.current_stage == ""

    def test_frozen(self) -> None:
        s = RuntimeStateSnapshot()
        with pytest.raises(FrozenInstanceError):
            s.current_stage = "running"  # type: ignore[misc]


class TestBrokerSessionState:
    def test_defaults(self) -> None:
        s = BrokerSessionState()
        assert s.is_connected is False
        assert s.subscriptions == ()
        assert s.reconnect_attempts == 0

    def test_frozen(self) -> None:
        s = BrokerSessionState()
        with pytest.raises(FrozenInstanceError):
            s.is_connected = True  # type: ignore[misc]


class TestShutdownPlan:
    def test_defaults(self) -> None:
        p = ShutdownPlan()
        assert p.stage is ShutdownStage.NOT_STARTED
        assert p.timeout_per_stage == 30.0
        assert p.force_timeout_seconds == 120.0

    def test_frozen(self) -> None:
        p = ShutdownPlan()
        with pytest.raises(FrozenInstanceError):
            p.stage = ShutdownStage.COMPLETED  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TestEnums:
    def test_circuit_breaker_state(self) -> None:
        assert CircuitBreakerState.CLOSED.value == "closed"
        assert CircuitBreakerState.OPEN.value == "open"
        assert CircuitBreakerState.HALF_OPEN.value == "half_open"

    def test_retry_mode(self) -> None:
        assert RetryMode.IMMEDIATE.value == "immediate"
        assert RetryMode.EXPONENTIAL_JITTER.value == "exponential_jitter"

    def test_recovery_strategy(self) -> None:
        assert RecoveryStrategy.RETRY.value == "retry"
        assert RecoveryStrategy.FAILOVER.value == "failover"

    def test_recovery_status(self) -> None:
        assert RecoveryStatus.PENDING.value == "pending"
        assert RecoveryStatus.CANCELLED.value == "cancelled"

    def test_component_type(self) -> None:
        assert ComponentType.PIPELINE.value == "pipeline"
        assert ComponentType.BROKER_SESSION.value == "broker_session"

    def test_reconnect_strategy(self) -> None:
        assert ReconnectStrategy.IMMEDIATE.value == "immediate"
        assert ReconnectStrategy.SEQUENTIAL.value == "sequential"

    def test_shutdown_stage(self) -> None:
        assert ShutdownStage.NOT_STARTED.value == "not_started"
        assert ShutdownStage.COMPLETED.value == "completed"


# ---------------------------------------------------------------------------
# Exceptions — hierarchy
# ---------------------------------------------------------------------------


class TestExceptions:
    def test_hierarchy(self) -> None:
        assert issubclass(RecoveryInputError, RecoveryError)
        assert issubclass(RecoveryStrategyError, RecoveryError)
        assert issubclass(RecoveryTimeoutError, RecoveryError)
        assert issubclass(RecoveryStateError, RecoveryError)
        assert issubclass(RecoveryCheckpointError, RecoveryError)
        assert issubclass(RecoveryCircuitBreakerError, RecoveryError)
        assert issubclass(RecoveryReconnectError, RecoveryError)
        assert issubclass(RecoveryShutdownError, RecoveryError)
        assert issubclass(RecoveryRetryError, RecoveryError)
        assert issubclass(RecoveryInputError, ValueError)

    def test_raise(self) -> None:
        for exc_cls in [
            RecoveryInputError,
            RecoveryStrategyError,
            RecoveryTimeoutError,
            RecoveryStateError,
            RecoveryCheckpointError,
            RecoveryCircuitBreakerError,
            RecoveryReconnectError,
            RecoveryShutdownError,
            RecoveryRetryError,
        ]:
            with pytest.raises(exc_cls):
                raise exc_cls("test error")


# ---------------------------------------------------------------------------
# Backoff
# ---------------------------------------------------------------------------


class TestBackoff:
    def test_immediate(self) -> None:
        policy = RetryPolicy(mode=RetryMode.IMMEDIATE)
        calc = BackoffCalculator(policy)
        for i in range(1, 10):
            assert calc.delay(i) == 0.0

    def test_fixed_delay(self) -> None:
        policy = RetryPolicy(mode=RetryMode.FIXED_DELAY, base_delay_seconds=2.0)
        calc = BackoffCalculator(policy)
        for i in range(1, 5):
            assert calc.delay(i) == 2.0

    def test_linear_backoff(self) -> None:
        policy = RetryPolicy(
            mode=RetryMode.LINEAR_BACKOFF,
            base_delay_seconds=1.0,
            max_delay_seconds=10.0,
        )
        calc = BackoffCalculator(policy)
        assert calc.delay(1) == 1.0
        assert calc.delay(2) == 2.0
        assert calc.delay(3) == 3.0

    def test_linear_backoff_capped(self) -> None:
        policy = RetryPolicy(
            mode=RetryMode.LINEAR_BACKOFF,
            base_delay_seconds=5.0,
            max_delay_seconds=12.0,
        )
        calc = BackoffCalculator(policy)
        assert calc.delay(1) == 5.0
        assert calc.delay(2) == 10.0
        assert calc.delay(3) == 12.0

    def test_exponential_backoff(self) -> None:
        policy = RetryPolicy(
            mode=RetryMode.EXPONENTIAL_BACKOFF,
            base_delay_seconds=1.0,
            max_delay_seconds=100.0,
        )
        calc = BackoffCalculator(policy)
        assert calc.delay(1) == 1.0
        assert calc.delay(2) == 2.0
        assert calc.delay(3) == 4.0
        assert calc.delay(4) == 8.0

    def test_exponential_backoff_capped(self) -> None:
        policy = RetryPolicy(
            mode=RetryMode.EXPONENTIAL_BACKOFF,
            base_delay_seconds=10.0,
            max_delay_seconds=30.0,
        )
        calc = BackoffCalculator(policy)
        assert calc.delay(1) == 10.0
        assert calc.delay(2) == 20.0
        assert calc.delay(3) == 30.0

    def test_exponential_jitter_range(self) -> None:
        policy = RetryPolicy(
            mode=RetryMode.EXPONENTIAL_JITTER,
            base_delay_seconds=1.0,
            max_delay_seconds=10.0,
            jitter_factor=0.1,
        )
        calc = BackoffCalculator(policy)
        for i in range(1, 5):
            delay = calc.delay(i)
            assert delay >= 0.0
            expected_base = min(1.0 * (2.0 ** (i - 1)), 10.0)
            expected_max = expected_base + expected_base * 0.1
            assert delay <= expected_max + 0.001

    def test_attempt_zero_returns_zero(self) -> None:
        policy = RetryPolicy(mode=RetryMode.EXPONENTIAL_BACKOFF)
        calc = BackoffCalculator(policy)
        assert calc.delay(0) == 0.0

    def test_total_timeout(self) -> None:
        policy = RetryPolicy(
            mode=RetryMode.FIXED_DELAY,
            base_delay_seconds=1.0,
            max_attempts=3,
        )
        calc = BackoffCalculator(policy)
        total = calc.total_timeout()
        assert total == 3.0

    def test_deadline(self) -> None:
        policy = RetryPolicy(
            mode=RetryMode.FIXED_DELAY,
            base_delay_seconds=1.0,
            max_attempts=2,
        )
        calc = BackoffCalculator(policy)
        dl = calc.deadline()
        assert dl > 0

    def test_get_backoff_unknown_mode_fallsback(self) -> None:
        policy = RetryPolicy(mode=RetryMode.IMMEDIATE)
        func = get_backoff(policy)
        assert func(1) == 0.0


# ---------------------------------------------------------------------------
# Retry Engine
# ---------------------------------------------------------------------------


class TestRetryEngine:
    def test_immediate_success(self) -> None:
        policy = RetryPolicy(mode=RetryMode.IMMEDIATE, max_attempts=3)
        engine = RetryEngine(policy)
        status = engine.execute(lambda: True)
        assert status is RecoveryStatus.SUCCESS
        assert engine.attempt_count >= 1

    def test_immediate_failure(self) -> None:
        policy = RetryPolicy(mode=RetryMode.IMMEDIATE, max_attempts=1)
        engine = RetryEngine(policy)
        with pytest.raises(RecoveryRetryError):
            engine.execute(lambda: False)

    def test_retry_eventually_succeeds(self) -> None:
        policy = RetryPolicy(mode=RetryMode.IMMEDIATE, max_attempts=5)
        engine = RetryEngine(policy)
        call_count = 0

        def action() -> bool:
            nonlocal call_count
            call_count += 1
            return call_count >= 3

        status = engine.execute(action)
        assert status is RecoveryStatus.SUCCESS
        assert call_count == 3

    def test_all_attempts_exhausted(self) -> None:
        policy = RetryPolicy(mode=RetryMode.IMMEDIATE, max_attempts=3)
        engine = RetryEngine(policy)
        with pytest.raises(RecoveryRetryError, match="All 3 attempts returned False"):
            engine.execute(lambda: False)

    def test_retryable_exception(self) -> None:
        policy = RetryPolicy(
            mode=RetryMode.IMMEDIATE,
            max_attempts=3,
            retryable_exceptions=(ValueError,),
        )
        engine = RetryEngine(policy)
        call_count = 0

        def action() -> bool:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("transient")
            return True

        status = engine.execute(action)
        assert status is RecoveryStatus.SUCCESS
        assert call_count == 3

    def test_non_retryable_exception(self) -> None:
        policy = RetryPolicy(
            mode=RetryMode.IMMEDIATE,
            max_attempts=3,
            retryable_exceptions=(ValueError,),
        )
        engine = RetryEngine(policy)

        def action() -> bool:
            raise TypeError("not retryable")

        with pytest.raises(RecoveryRetryError, match="Non-retryable exception"):
            engine.execute(action)

    def test_timeout(self) -> None:
        policy = RetryPolicy(
            mode=RetryMode.FIXED_DELAY,
            base_delay_seconds=5.0,
            max_attempts=10,
            timeout_seconds=0.1,
        )
        engine = RetryEngine(policy)
        with pytest.raises(RecoveryTimeoutError):
            engine.execute(lambda: False)

    def test_reset(self) -> None:
        policy = RetryPolicy(mode=RetryMode.IMMEDIATE, max_attempts=1)
        engine = RetryEngine(policy)
        with pytest.raises(RecoveryRetryError):
            engine.execute(lambda: False)
        assert engine.attempt_count > 0
        engine.reset()
        assert engine.attempt_count == 0
        assert engine.last_error == ""

    def test_last_error_recorded(self) -> None:
        policy = RetryPolicy(
            mode=RetryMode.IMMEDIATE,
            max_attempts=2,
            retryable_exceptions=(RuntimeError,),
        )
        engine = RetryEngine(policy)

        def action() -> bool:
            raise RuntimeError("boom")

        with pytest.raises(RecoveryRetryError):
            engine.execute(action)
        assert "boom" in engine.last_error


# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------


class TestCircuitBreaker:
    def test_initial_state_closed(self) -> None:
        cb = CircuitBreaker()
        assert cb.state is CircuitBreakerState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0

    def test_success_keeps_closed(self) -> None:
        cb = CircuitBreaker()
        cb.call(lambda: True)
        assert cb.state is CircuitBreakerState.CLOSED
        assert cb.success_count == 1

    def test_failures_open_circuit(self) -> None:
        cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=3))
        result = cb.call(lambda: False)
        assert result is False
        assert cb.state is CircuitBreakerState.CLOSED
        assert cb.failure_count == 1

        result = cb.call(lambda: False)
        assert result is False
        assert cb.failure_count == 2

        result = cb.call(lambda: False)
        assert result is False
        assert cb.state is CircuitBreakerState.OPEN
        assert cb.failure_count == 3

    def test_open_circuit_rejects_calls(self) -> None:
        cb = CircuitBreaker(
            CircuitBreakerConfig(failure_threshold=2, recovery_timeout_seconds=9999)
        )
        cb.call(lambda: False)
        cb.call(lambda: False)
        assert cb.state is CircuitBreakerState.OPEN

        with pytest.raises(
            RecoveryCircuitBreakerError, match="Circuit breaker is OPEN"
        ):
            cb.call(lambda: True)

    def test_half_open_success_resets(self) -> None:
        cb = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=2,
                recovery_timeout_seconds=0.01,
                success_threshold=2,
                half_open_max_calls=3,
            )
        )
        cb.call(lambda: False)
        cb.call(lambda: False)
        assert cb.state is CircuitBreakerState.OPEN

        sleep(0.02)
        cb.call(lambda: True)
        assert cb.state is CircuitBreakerState.HALF_OPEN

        cb.call(lambda: True)
        assert cb.state is CircuitBreakerState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0

    def test_half_open_failure_reopens(self) -> None:
        cb = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=2,
                recovery_timeout_seconds=0.01,
                success_threshold=2,
                half_open_max_calls=3,
            )
        )
        cb.call(lambda: False)
        cb.call(lambda: False)
        assert cb.state is CircuitBreakerState.OPEN

        sleep(0.02)
        cb.call(lambda: True)
        assert cb.state is CircuitBreakerState.HALF_OPEN

        result = cb.call(lambda: False)
        assert result is False
        assert cb.state is CircuitBreakerState.OPEN

    def test_half_open_max_calls_respected(self) -> None:
        cb = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=1,
                recovery_timeout_seconds=0.01,
                half_open_max_calls=1,
            )
        )
        result = cb.call(lambda: False)
        assert result is False
        assert cb.state is CircuitBreakerState.OPEN

        sleep(0.02)
        cb.call(lambda: True)
        assert cb.state is CircuitBreakerState.HALF_OPEN

        with pytest.raises(RecoveryCircuitBreakerError, match="max test calls reached"):
            cb.call(lambda: True)

    def test_exception_in_action(self) -> None:
        cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1))

        def action() -> bool:
            raise RuntimeError("action failed")

        with pytest.raises(RecoveryCircuitBreakerError):
            cb.call(action)
        assert cb.state is CircuitBreakerState.OPEN

    def test_reset(self) -> None:
        cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1))
        result = cb.call(lambda: False)
        assert result is False
        assert cb.state is CircuitBreakerState.OPEN
        cb.reset()
        assert cb.state is CircuitBreakerState.CLOSED
        assert cb.failure_count == 0

    def test_repr(self) -> None:
        cb = CircuitBreaker()
        r = repr(cb)
        assert "CircuitBreaker" in r
        assert "closed" in r


# ---------------------------------------------------------------------------
# Checkpoint Manager
# ---------------------------------------------------------------------------


class TestCheckpointManager:
    def test_save_and_load(self) -> None:
        mgr = CheckpointManager()
        cp = mgr.save("cp1", ComponentType.PIPELINE, {"key": "value"})
        assert cp.checkpoint_id == "cp1"
        assert cp.component is ComponentType.PIPELINE

        loaded = mgr.load("cp1")
        assert loaded == cp

    def test_load_missing(self) -> None:
        mgr = CheckpointManager()
        with pytest.raises(RecoveryCheckpointError, match="Checkpoint not found"):
            mgr.load("nonexistent")

    def test_delete(self) -> None:
        mgr = CheckpointManager()
        mgr.save("cp1", ComponentType.PIPELINE, {"k": "v"})
        mgr.delete("cp1")
        with pytest.raises(RecoveryCheckpointError):
            mgr.load("cp1")

    def test_delete_missing(self) -> None:
        mgr = CheckpointManager()
        with pytest.raises(RecoveryCheckpointError, match="Checkpoint not found"):
            mgr.delete("nonexistent")

    def test_list_by_component(self) -> None:
        mgr = CheckpointManager()
        mgr.save("cp1", ComponentType.PIPELINE, {"a": 1})
        mgr.save("cp2", ComponentType.BROKER_SESSION, {"b": 2})
        mgr.save("cp3", ComponentType.PIPELINE, {"c": 3})
        pipelines = mgr.list_by_component(ComponentType.PIPELINE)
        assert len(pipelines) == 2

    def test_list_all(self) -> None:
        mgr = CheckpointManager()
        mgr.save("cp1", ComponentType.PIPELINE, {"a": 1})
        mgr.save("cp2", ComponentType.BROKER_SESSION, {"b": 2})
        assert len(mgr.list_all()) == 2

    def test_count(self) -> None:
        mgr = CheckpointManager()
        assert mgr.count() == 0
        mgr.save("cp1", ComponentType.PIPELINE, {"a": 1})
        assert mgr.count() == 1

    def test_clear(self) -> None:
        mgr = CheckpointManager()
        mgr.save("cp1", ComponentType.PIPELINE, {"a": 1})
        mgr.clear()
        assert mgr.count() == 0

    def test_latest(self) -> None:
        mgr = CheckpointManager()
        assert mgr.latest(ComponentType.PIPELINE) is None
        mgr.save("cp1", ComponentType.PIPELINE, {"a": 1})
        mgr.save("cp2", ComponentType.PIPELINE, {"b": 2})
        latest = mgr.latest(ComponentType.PIPELINE)
        assert latest is not None
        assert latest.checkpoint_id == "cp2"

    def test_save_with_metadata(self) -> None:
        mgr = CheckpointManager()
        cp = mgr.save(
            "cp1",
            ComponentType.PIPELINE,
            {"key": "val"},
            version="2.0.0",
            metadata={"author": "test"},
        )
        assert cp.version == "2.0.0"
        assert cp.metadata == {"author": "test"}


# ---------------------------------------------------------------------------
# State Manager
# ---------------------------------------------------------------------------


class TestStateManager:
    def test_capture_empty(self) -> None:
        mgr = StateManager()
        snapshot = mgr.capture()
        assert snapshot.pipeline_progress == {}
        assert snapshot.current_stage == ""

    def test_capture_with_funcs(self) -> None:
        mgr = StateManager()
        mgr.register_capture("pipeline_progress", lambda: {"stage": "running"})
        mgr.register_capture("current_stage", lambda: "qualification")
        snapshot = mgr.capture()
        assert snapshot.pipeline_progress == {"stage": "running"}

    def test_capture_error(self) -> None:
        mgr = StateManager()
        mgr.register_capture("pipeline_progress", lambda: {"ok": True})
        mgr.register_capture(
            "current_stage", lambda: (_ for _ in ()).throw(ValueError("bad"))
        )

        with pytest.raises(RecoveryStateError, match="Partial state capture"):
            mgr.capture()

    def test_restore(self) -> None:
        mgr = StateManager()
        restored: dict[str, object] = {}

        def restore_portfolio(data: object) -> None:
            restored["portfolio"] = data

        mgr.register_restore("portfolio_snapshot", restore_portfolio)
        mgr.register_capture("portfolio_snapshot", lambda: {"cash": 10000})
        snapshot = mgr.capture()
        mgr.restore(snapshot)
        assert restored.get("portfolio") == {"cash": 10000}

    def test_restore_no_snapshot(self) -> None:
        mgr = StateManager()
        with pytest.raises(RecoveryStateError, match="No snapshot available"):
            mgr.restore()

    def test_restore_error(self) -> None:
        mgr = StateManager()

        def bad_restore(data: object) -> None:
            raise ValueError("restore failed")

        mgr.register_restore("pipeline_progress", bad_restore)
        mgr.register_capture("pipeline_progress", lambda: {"x": 1})
        snapshot = mgr.capture()

        with pytest.raises(RecoveryStateError, match="Partial state restore"):
            mgr.restore(snapshot)

    def test_unregister(self) -> None:
        mgr = StateManager()
        mgr.register_capture("key", lambda: 1)
        mgr.unregister("key")
        snapshot = mgr.capture()
        assert "key" not in snapshot.pipeline_progress

    def test_last_snapshot(self) -> None:
        mgr = StateManager()
        assert mgr.last_snapshot is None
        mgr.capture()
        assert mgr.last_snapshot is not None

    def test_clear(self) -> None:
        mgr = StateManager()
        mgr.register_capture("key", lambda: 1)
        mgr.capture()
        mgr.clear()
        assert mgr.last_snapshot is None
        snapshot = mgr.capture()
        assert snapshot.pipeline_progress == {}


# ---------------------------------------------------------------------------
# Broker Reconnector
# ---------------------------------------------------------------------------


class TestBrokerReconnector:
    def test_successful_reconnect(self) -> None:
        reconnector = BrokerReconnector()
        status = reconnector.reconnect(action=lambda: True)
        assert status is RecoveryStatus.SUCCESS
        assert reconnector.state.is_connected is True

    def test_failed_reconnect(self) -> None:
        reconnector = BrokerReconnector()
        with pytest.raises(RecoveryReconnectError):
            reconnector.reconnect(action=lambda: False)
        assert reconnector.state.is_connected is False

    def test_heartbeat_verification(self) -> None:
        reconnector = BrokerReconnector()
        with pytest.raises(
            RecoveryReconnectError, match="heartbeat verification failed"
        ):
            reconnector.reconnect(
                action=lambda: True,
                heartbeat=lambda: False,
            )

    def test_subscription_restoration(self) -> None:
        reconnector = BrokerReconnector()
        restored: list[str] = []

        def restore(subs: tuple[str, ...]) -> bool:
            restored.extend(subs)
            return True

        status = reconnector.reconnect(
            action=lambda: True,
            subscriptions=("NSE", "BSE"),
            restore_subscriptions=restore,
        )
        assert status is RecoveryStatus.SUCCESS
        assert restored == ["NSE", "BSE"]

    def test_heartbeat_verify_method(self) -> None:
        reconnector = BrokerReconnector()
        reconnector.reconnect(action=lambda: True)
        assert reconnector.verify_heartbeat(lambda: True) is True
        assert reconnector.verify_heartbeat(lambda: False) is False

    def test_reset(self) -> None:
        reconnector = BrokerReconnector()
        reconnector.reconnect(action=lambda: True)
        assert reconnector.reconnect_attempts > 0
        reconnector.reset()
        assert reconnector.reconnect_attempts == 0
        assert reconnector.state.is_connected is False

    def test_default_state(self) -> None:
        reconnector = BrokerReconnector()
        assert reconnector.state.is_connected is False
        assert reconnector.reconnect_attempts == 0

    def test_exception_during_reconnect(self) -> None:
        reconnector = BrokerReconnector()

        def action() -> bool:
            raise RuntimeError("connection refused")

        with pytest.raises(RecoveryReconnectError):
            reconnector.reconnect(action=action)


# ---------------------------------------------------------------------------
# Graceful Shutdown
# ---------------------------------------------------------------------------


class TestGracefulShutdown:
    def test_execute_with_hooks(self) -> None:
        shutdown = GracefulShutdown()
        executed: list[str] = []

        shutdown.register_hook(
            ShutdownStage.STOPPING_PIPELINE, lambda: executed.append("pipeline")
        )
        shutdown.register_hook(
            ShutdownStage.FLUSHING_LOGS, lambda: executed.append("logs")
        )

        shutdown.execute()

        assert "pipeline" in executed
        assert "logs" in executed
        assert shutdown.current_stage is ShutdownStage.COMPLETED

    def test_register_and_unregister_hook(self) -> None:
        shutdown = GracefulShutdown()
        executed: list[str] = []

        def hook() -> None:
            executed.append("ran")

        shutdown.register_hook(ShutdownStage.STOPPING_PIPELINE, hook)
        shutdown.unregister_hook(ShutdownStage.STOPPING_PIPELINE, hook)
        shutdown.execute()
        assert len(executed) == 0

    def test_hook_failure(self) -> None:
        shutdown = GracefulShutdown()
        shutdown.register_hook(
            ShutdownStage.STOPPING_PIPELINE,
            lambda: (_ for _ in ()).throw(RuntimeError("hook failed")),
        )
        with pytest.raises(RecoveryShutdownError, match="hook failed"):
            shutdown.execute()

    def test_abort(self) -> None:
        shutdown = GracefulShutdown()
        shutdown.register_hook(ShutdownStage.STOPPING_PIPELINE, lambda: None)
        shutdown.execute()
        shutdown.abort()
        assert shutdown.current_stage is ShutdownStage.NOT_STARTED

    def test_reset(self) -> None:
        shutdown = GracefulShutdown()
        shutdown.register_hook(ShutdownStage.STOPPING_PIPELINE, lambda: None)
        shutdown.execute()
        shutdown.reset()
        assert shutdown.current_stage is ShutdownStage.NOT_STARTED

    def test_force_timeout(self) -> None:
        plan = ShutdownPlan(force_timeout_seconds=0.05, timeout_per_stage=0.05)
        shutdown = GracefulShutdown(plan)
        shutdown.register_hook(ShutdownStage.STOPPING_PIPELINE, lambda: sleep(0.1))
        with pytest.raises(RecoveryShutdownError, match="timed out"):
            shutdown.execute()


# ---------------------------------------------------------------------------
# Health Recovery
# ---------------------------------------------------------------------------


class TestHealthRecovery:
    def test_register_and_run_health_checks(self) -> None:
        hr = HealthRecovery()
        hr.register_health_check("check1", lambda: True, ComponentType.PIPELINE)
        hr.register_health_check("check2", lambda: False, ComponentType.BROKER_SESSION)
        results = hr.run_health_checks()
        assert results["check1"] is True
        assert results["check2"] is False

    def test_unregister_health_check(self) -> None:
        hr = HealthRecovery()
        hr.register_health_check("check1", lambda: True, ComponentType.PIPELINE)
        hr.unregister_health_check("check1")
        results = hr.run_health_checks()
        assert "check1" not in results

    def test_auto_recovery_triggered(self) -> None:
        hr = HealthRecovery()
        triggered: list[str] = []

        def trigger(component: ComponentType, reason: str) -> RecoveryStatus:
            triggered.append(component.value)
            return RecoveryStatus.SUCCESS

        hr.set_recovery_trigger(trigger)
        hr.register_health_check("check1", lambda: False, ComponentType.PIPELINE)
        hr.run_health_checks()
        assert "pipeline" in triggered

    def test_auto_recovery_disabled(self) -> None:
        hr = HealthRecovery()
        triggered: list[str] = []

        def trigger(component: ComponentType, reason: str) -> RecoveryStatus:
            triggered.append(component.value)
            return RecoveryStatus.SUCCESS

        hr.set_auto_recovery(False)
        hr.set_recovery_trigger(trigger)
        hr.register_health_check("check1", lambda: False, ComponentType.PIPELINE)
        hr.run_health_checks()
        assert len(triggered) == 0

    def test_get_recovery_history(self) -> None:
        hr = HealthRecovery()
        assert hr.get_recovery_history() == {}

    def test_clear_history(self) -> None:
        hr = HealthRecovery()
        hr.set_recovery_trigger(lambda c, r: RecoveryStatus.SUCCESS)
        hr.register_health_check("c1", lambda: False, ComponentType.PIPELINE)
        hr.run_health_checks()
        assert len(hr.get_recovery_history()) == 1
        hr.clear_history()
        assert hr.get_recovery_history() == {}

    def test_reset(self) -> None:
        hr = HealthRecovery()
        hr.register_health_check("c1", lambda: True, ComponentType.PIPELINE)
        hr.reset()
        results = hr.run_health_checks()
        assert results == {}

    def test_auto_recovery_flag(self) -> None:
        hr = HealthRecovery()
        assert hr.auto_recovery_enabled is True
        hr.set_auto_recovery(False)
        assert hr.auto_recovery_enabled is False

    def test_exception_in_health_check(self) -> None:
        hr = HealthRecovery()

        def bad_check() -> bool:
            raise RuntimeError("health check failed")

        hr.register_health_check("c1", bad_check, ComponentType.PIPELINE)
        results = hr.run_health_checks()
        assert results["c1"] is False


# ---------------------------------------------------------------------------
# Recovery Manager
# ---------------------------------------------------------------------------


class TestRecoveryManager:
    def test_initialization(self) -> None:
        mgr = RecoveryManager()
        assert mgr.checkpoints is not None
        assert mgr.state_manager is not None
        assert mgr.shutdown is not None
        assert mgr.health_recovery is not None
        assert mgr.get_circuit_breaker("none") is None

    def test_register_and_get_circuit_breaker(self) -> None:
        mgr = RecoveryManager()
        cb = mgr.register_circuit_breaker("broker")
        assert cb.state is CircuitBreakerState.CLOSED
        assert mgr.get_circuit_breaker("broker") is cb

    def test_register_circuit_breaker_with_config(self) -> None:
        mgr = RecoveryManager()
        config = CircuitBreakerConfig(failure_threshold=10)
        cb = mgr.register_circuit_breaker("custom", config)
        assert cb.config.failure_threshold == 10

    def test_request_recovery_retry(self) -> None:
        mgr = RecoveryManager()
        report = mgr.request_recovery(
            component=ComponentType.PIPELINE,
            failure_reason="transient error",
            strategy=RecoveryStrategy.RETRY,
        )
        assert report.status is RecoveryStatus.SUCCESS
        assert report.component is ComponentType.PIPELINE
        assert report.strategy is RecoveryStrategy.RETRY

    def test_request_recovery_reconnect(self) -> None:
        mgr = RecoveryManager()
        report = mgr.request_recovery(
            component=ComponentType.BROKER_SESSION,
            failure_reason="connection lost",
            strategy=RecoveryStrategy.RECONNECT,
        )
        assert report.status is RecoveryStatus.SUCCESS
        assert report.strategy is RecoveryStrategy.RECONNECT

    def test_request_recovery_restart_no_snapshot(self) -> None:
        mgr = RecoveryManager()
        report = mgr.request_recovery(
            component=ComponentType.PIPELINE,
            failure_reason="corrupt state",
            strategy=RecoveryStrategy.RESTART,
        )
        assert report.status is RecoveryStatus.FAILED
        assert "No state snapshot" in report.error

    def test_request_recovery_restart_with_snapshot(self) -> None:
        mgr = RecoveryManager()
        mgr.state_manager.register_capture(
            "pipeline_progress", lambda: {"stage": "done"}
        )
        mgr.state_manager.capture()

        report = mgr.request_recovery(
            component=ComponentType.PIPELINE,
            failure_reason="restart needed",
            strategy=RecoveryStrategy.RESTART,
        )
        assert report.status is RecoveryStatus.SUCCESS

    def test_request_recovery_shutdown(self) -> None:
        mgr = RecoveryManager()
        report = mgr.request_recovery(
            component=ComponentType.PIPELINE,
            failure_reason="shutdown requested",
            strategy=RecoveryStrategy.SHUTDOWN,
        )
        assert report.status is RecoveryStatus.SUCCESS
        assert mgr.shutdown.current_stage is ShutdownStage.COMPLETED

    def test_get_recovery_history(self) -> None:
        mgr = RecoveryManager()
        assert len(mgr.get_recovery_history()) == 0
        mgr.request_recovery(
            component=ComponentType.PIPELINE,
            failure_reason="test",
        )
        assert len(mgr.get_recovery_history()) == 1

    def test_generate_report(self) -> None:
        mgr = RecoveryManager()
        mgr.request_recovery(
            component=ComponentType.PIPELINE,
            failure_reason="test",
        )
        report = mgr.generate_report()
        assert report.total_attempts == 1
        assert report.successful_attempts == 1

    def test_reset(self) -> None:
        mgr = RecoveryManager()
        mgr.register_circuit_breaker("test")
        mgr.request_recovery(
            component=ComponentType.PIPELINE,
            failure_reason="test",
        )
        mgr.reset()
        assert len(mgr.get_recovery_history()) == 0
        assert mgr.get_circuit_breaker("test") is None

    def test_health_recovery_integration(self) -> None:
        mgr = RecoveryManager()
        triggered: list[str] = []
        mgr.health_recovery.set_recovery_trigger(
            lambda c, r: (
                triggered.append(c.value),
                RecoveryStatus.SUCCESS,
            )[1]
        )
        mgr.health_recovery.register_health_check(
            "h1", lambda: False, ComponentType.PIPELINE
        )
        mgr.health_recovery.run_health_checks()
        assert "pipeline" in triggered


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------


class TestConcurrency:
    def test_concurrent_checkpoint_access(self) -> None:
        mgr = CheckpointManager()
        errors: list[Exception] = []

        def worker(n: int) -> None:
            try:
                for _ in range(20):
                    mgr.save(f"cp{n}", ComponentType.PIPELINE, {"n": n})
                    mgr.load(f"cp{n}")
            except Exception as exc:
                errors.append(exc)

        threads = [Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0

    def test_concurrent_circuit_breaker(self) -> None:
        cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=20))
        errors: list[Exception] = []

        def worker() -> None:
            try:
                for _ in range(5):
                    cb.call(lambda: True)
            except Exception as exc:
                errors.append(exc)

        threads = [Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0

    def test_concurrent_recovery_requests(self) -> None:
        mgr = RecoveryManager()
        reports: list[RecoveryReport] = []
        errors: list[Exception] = []

        def worker() -> None:
            try:
                report = mgr.request_recovery(
                    component=ComponentType.PIPELINE,
                    failure_reason="concurrent test",
                )
                reports.append(report)
            except Exception as exc:
                errors.append(exc)

        threads = [Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0
        assert len(reports) == 10


# ---------------------------------------------------------------------------
# Dependency Injection
# ---------------------------------------------------------------------------


class TestDependencyInjection:
    def test_recovery_manager_injects_components(self) -> None:
        mgr = RecoveryManager()
        assert isinstance(mgr.checkpoints, CheckpointManager)
        assert isinstance(mgr.state_manager, StateManager)
        assert isinstance(mgr.shutdown, GracefulShutdown)
        assert isinstance(mgr.health_recovery, HealthRecovery)
        assert isinstance(mgr.reconnect, BrokerReconnector)

    def test_circuit_breaker_injects_config(self) -> None:
        config = CircuitBreakerConfig(
            failure_threshold=10, recovery_timeout_seconds=60.0
        )
        cb = CircuitBreaker(config)
        assert cb.config.failure_threshold == 10
        assert cb.config.recovery_timeout_seconds == 60.0

    def test_retry_engine_injects_policy(self) -> None:
        policy = RetryPolicy(mode=RetryMode.FIXED_DELAY, base_delay_seconds=5.0)
        engine = RetryEngine(policy)
        engine.execute(lambda: True)
        assert engine.attempt_count == 1

    def test_backoff_calculator_injects_policy(self) -> None:
        policy = RetryPolicy(mode=RetryMode.LINEAR_BACKOFF, base_delay_seconds=2.0)
        calc = BackoffCalculator(policy)
        assert calc.delay(2) == 4.0
