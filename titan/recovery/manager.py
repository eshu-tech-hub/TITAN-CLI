from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from time import monotonic
from typing import Any

from titan.recovery.checkpoint import CheckpointManager
from titan.recovery.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from titan.recovery.exceptions import (
    RecoveryError,
)
from titan.recovery.health_recovery import HealthRecovery
from titan.recovery.models import (
    ComponentType,
    RecoveryAttempt,
    RecoveryHistoryEntry,
    RecoveryLevel,
    RecoveryReport,
    RecoveryRequest,
    RecoveryStatus,
    RecoveryStrategy,
    RetryPolicy,
)
from titan.recovery.reconnect import BrokerReconnector
from titan.recovery.retry import RetryEngine
from titan.recovery.shutdown import GracefulShutdown
from titan.recovery.state import StateManager


@dataclass(slots=True)
class RecoveryManager:
    _checkpoints: CheckpointManager = field(default_factory=CheckpointManager)
    _state_manager: StateManager = field(default_factory=StateManager)
    _shutdown: GracefulShutdown = field(default_factory=GracefulShutdown)
    _health_recovery: HealthRecovery = field(default_factory=HealthRecovery)
    _circuit_breakers: dict[str, CircuitBreaker] = field(
        default_factory=dict, init=False
    )
    _reconnect: BrokerReconnector = field(default_factory=BrokerReconnector)
    _recovery_history: list[RecoveryReport] = field(default_factory=list, init=False)
    _start_time: datetime = field(default_factory=lambda: datetime.now(UTC), init=False)
    _lock: Lock = field(default_factory=Lock, init=False)

    # Escalating Recovery Support
    max_retries: int = 2
    max_restarts: int = 1
    _failures: dict[str, int] = field(default_factory=dict, init=False)
    _escalation_history: list[RecoveryHistoryEntry] = field(
        default_factory=list, init=False
    )

    def __post_init__(self) -> None:
        self._health_recovery.set_recovery_trigger(self._auto_recovery)

    @property
    def checkpoints(self) -> CheckpointManager:
        return self._checkpoints

    @property
    def state_manager(self) -> StateManager:
        return self._state_manager

    @property
    def shutdown(self) -> GracefulShutdown:
        return self._shutdown

    @property
    def health_recovery(self) -> HealthRecovery:
        return self._health_recovery

    @property
    def reconnect(self) -> BrokerReconnector:
        return self._reconnect

    def get_circuit_breaker(self, name: str) -> CircuitBreaker | None:
        with self._lock:
            return self._circuit_breakers.get(name)

    def register_circuit_breaker(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
    ) -> CircuitBreaker:
        cb = CircuitBreaker(config or CircuitBreakerConfig())
        with self._lock:
            self._circuit_breakers[name] = cb
        return cb

    def request_recovery(
        self,
        component: ComponentType,
        failure_reason: str,
        strategy: RecoveryStrategy = RecoveryStrategy.RETRY,
        metadata: Mapping[str, Any] | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> RecoveryReport:
        request = RecoveryRequest(
            component=component,
            strategy=strategy,
            failure_reason=failure_reason,
            metadata=metadata or {},
            retry_policy=retry_policy,
        )

        return self._execute_recovery(request)

    def execute(self, level: RecoveryLevel, component: str, context: dict) -> None:
        """
        Execute an escalating recovery sequence requested by the supervisor.
        """
        try:
            comp_type = ComponentType(component.lower())
        except ValueError:
            comp_type = ComponentType.PIPELINE

        if level == RecoveryLevel.RETRY:
            self.request_recovery(
                comp_type, "degraded", RecoveryStrategy.RETRY, context
            )
        elif level == RecoveryLevel.RESTART_SUBSYSTEM:
            self.request_recovery(comp_type, "dead", RecoveryStrategy.RESTART, context)
        elif level == RecoveryLevel.RESTART_ENGINE:
            self.request_recovery(
                comp_type, "escalated_failure", RecoveryStrategy.ESCALATE, context
            )
        elif level == RecoveryLevel.GRACEFUL_SHUTDOWN:
            self.request_recovery(
                comp_type, "unrecoverable", RecoveryStrategy.SHUTDOWN, context
            )

    def _execute_recovery(self, request: RecoveryRequest) -> RecoveryReport:
        start = monotonic()
        attempts: list[RecoveryAttempt] = []

        try:
            if request.strategy is RecoveryStrategy.RETRY:
                result = self._execute_retry(request, attempts)
            elif request.strategy is RecoveryStrategy.RECONNECT:
                result = self._execute_reconnect(request, attempts)
            elif request.strategy is RecoveryStrategy.RESTART:
                result = self._execute_restart(request, attempts)
            elif request.strategy is RecoveryStrategy.SHUTDOWN:
                result = self._execute_shutdown(request, attempts)
            else:
                result = self._execute_retry(request, attempts)
        except RecoveryError:
            result = RecoveryStatus.FAILED

        duration = monotonic() - start

        report = RecoveryReport(
            request_id=request.request_id,
            component=request.component,
            strategy=request.strategy,
            status=result,
            total_attempts=len(attempts),
            successful_attempts=sum(
                1 for a in attempts if a.status is RecoveryStatus.SUCCESS
            ),
            failed_attempts=sum(
                1 for a in attempts if a.status is RecoveryStatus.FAILED
            ),
            duration_seconds=duration,
            failure_reason=request.failure_reason,
            error=(
                attempts[-1].error
                if attempts and result is RecoveryStatus.FAILED
                else ""
            ),
            attempts=tuple(attempts),
            metadata=request.metadata,
        )

        with self._lock:
            self._recovery_history.append(report)

        return report

    def _execute_retry(
        self,
        request: RecoveryRequest,
        attempts: list[RecoveryAttempt],
    ) -> RecoveryStatus:
        policy = request.retry_policy or RetryPolicy()
        engine = RetryEngine(policy)

        def action() -> bool:
            return True

        attempt = RecoveryAttempt(
            attempt_number=len(attempts) + 1,
            strategy=RecoveryStrategy.RETRY,
        )

        try:
            status = engine.execute(action)
            attempts.append(
                RecoveryAttempt(
                    attempt_number=attempt.attempt_number,
                    strategy=attempt.strategy,
                    status=status,
                    error=engine.last_error,
                )
            )
            return status
        except Exception as exc:
            attempts.append(
                RecoveryAttempt(
                    attempt_number=attempt.attempt_number,
                    strategy=attempt.strategy,
                    status=RecoveryStatus.FAILED,
                    error=str(exc),
                )
            )
            return RecoveryStatus.FAILED

    def _execute_reconnect(
        self,
        request: RecoveryRequest,
        attempts: list[RecoveryAttempt],
    ) -> RecoveryStatus:
        attempt = RecoveryAttempt(
            attempt_number=len(attempts) + 1,
            strategy=RecoveryStrategy.RECONNECT,
        )
        try:
            self._reconnect.reconnect(
                action=lambda: True,
                subscriptions=tuple(request.metadata.get("subscriptions", [])),
            )
            attempts.append(
                RecoveryAttempt(
                    attempt_number=attempt.attempt_number,
                    strategy=attempt.strategy,
                    status=RecoveryStatus.SUCCESS,
                )
            )
            return RecoveryStatus.SUCCESS
        except Exception as exc:
            attempts.append(
                RecoveryAttempt(
                    attempt_number=attempt.attempt_number,
                    strategy=attempt.strategy,
                    status=RecoveryStatus.FAILED,
                    error=str(exc),
                )
            )
            return RecoveryStatus.FAILED

    def _execute_restart(
        self,
        request: RecoveryRequest,
        attempts: list[RecoveryAttempt],
    ) -> RecoveryStatus:
        attempt = RecoveryAttempt(
            attempt_number=len(attempts) + 1,
            strategy=RecoveryStrategy.RESTART,
        )
        try:
            restored = self._state_manager.last_snapshot is not None
            if not restored:
                attempts.append(
                    RecoveryAttempt(
                        attempt_number=attempt.attempt_number,
                        strategy=attempt.strategy,
                        status=RecoveryStatus.FAILED,
                        error="No state snapshot available for restart",
                    )
                )
                return RecoveryStatus.FAILED
            self._state_manager.restore()
            attempts.append(
                RecoveryAttempt(
                    attempt_number=attempt.attempt_number,
                    strategy=attempt.strategy,
                    status=RecoveryStatus.SUCCESS,
                )
            )
            return RecoveryStatus.SUCCESS
        except Exception as exc:
            attempts.append(
                RecoveryAttempt(
                    attempt_number=attempt.attempt_number,
                    strategy=attempt.strategy,
                    status=RecoveryStatus.FAILED,
                    error=str(exc),
                )
            )
            return RecoveryStatus.FAILED

    def _execute_shutdown(
        self,
        request: RecoveryRequest,
        attempts: list[RecoveryAttempt],
    ) -> RecoveryStatus:
        attempt = RecoveryAttempt(
            attempt_number=len(attempts) + 1,
            strategy=RecoveryStrategy.SHUTDOWN,
        )
        try:
            self._shutdown.execute()
            attempts.append(
                RecoveryAttempt(
                    attempt_number=attempt.attempt_number,
                    strategy=attempt.strategy,
                    status=RecoveryStatus.SUCCESS,
                )
            )
            return RecoveryStatus.SUCCESS
        except Exception as exc:
            attempts.append(
                RecoveryAttempt(
                    attempt_number=attempt.attempt_number,
                    strategy=attempt.strategy,
                    status=RecoveryStatus.FAILED,
                    error=str(exc),
                )
            )
            return RecoveryStatus.FAILED

    def _auto_recovery(
        self, component: ComponentType, failure_reason: str
    ) -> RecoveryStatus:
        report = self.request_recovery(
            component=component,
            failure_reason=failure_reason,
        )
        return report.status

    def get_recovery_history(
        self,
    ) -> tuple[RecoveryReport, ...]:
        with self._lock:
            return tuple(self._recovery_history)

    def generate_report(self) -> RecoveryReport:
        history = self.get_recovery_history()
        total = len(history)
        successful = sum(1 for r in history if r.status is RecoveryStatus.SUCCESS)
        failed = sum(1 for r in history if r.status is RecoveryStatus.FAILED)

        return RecoveryReport(
            request_id="_summary_",
            component=ComponentType.PIPELINE,
            strategy=RecoveryStrategy.RETRY,
            status=RecoveryStatus.SUCCESS if failed == 0 else RecoveryStatus.FAILED,
            total_attempts=total,
            successful_attempts=successful,
            failed_attempts=failed,
            recovered_components=tuple(
                r.component.value for r in history if r.status is RecoveryStatus.SUCCESS
            ),
            metadata={"total_recovery_requests": total},
        )

    def reset(self) -> None:
        with self._lock:
            self._checkpoints.clear()
            self._state_manager.clear()
            self._shutdown.reset()
            self._health_recovery.reset()
            self._circuit_breakers.clear()
            self._reconnect.reset()
            self._recovery_history.clear()
            self._start_time = datetime.now(UTC)
            self._failures.clear()
            self._escalation_history.clear()

    def handle_failure(self, component: str, reason: str) -> RecoveryStrategy:
        """
        Determine the appropriate recovery strategy based on failure history.
        Increments the failure count for the specified component.
        """
        import uuid

        from titan.core.logger import logger

        with self._lock:
            current_failures = self._failures.get(component, 0) + 1
            self._failures[component] = current_failures

            if current_failures <= self.max_retries:
                strategy = RecoveryStrategy.RETRY
            elif current_failures <= self.max_retries + self.max_restarts:
                strategy = RecoveryStrategy.RESTART_COMPONENT
            elif current_failures <= self.max_retries + self.max_restarts + 1:
                strategy = RecoveryStrategy.RESTART_RUNTIME
            else:
                strategy = RecoveryStrategy.SHUTDOWN

            entry = RecoveryHistoryEntry(
                request_id=str(uuid.uuid4()),
                component=component,
                strategy=strategy,
                status=RecoveryStatus.IN_PROGRESS,
                total_attempts=current_failures,
                failure_reason=reason,
            )
            self._escalation_history.append(entry)

        logger.warning(
            f"[RecoveryManager] Escalating {component} to {strategy.value.upper()} "
            f"(Attempt {current_failures}) - Reason: {reason}"
        )
        return strategy

    def mark_recovered(self, component: str) -> None:
        """
        Clear the failure count for a component upon successful recovery.
        """
        from titan.core.logger import logger

        with self._lock:
            if component in self._failures:
                del self._failures[component]
                logger.info(
                    f"[RecoveryManager] Component '{component}' successfully recovered."
                )

    def get_escalation_history(self) -> tuple[RecoveryHistoryEntry, ...]:
        """Return a read-only snapshot of the escalation history."""
        with self._lock:
            return tuple(self._escalation_history)
