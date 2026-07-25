from collections.abc import Callable
from dataclasses import dataclass, field
from threading import Lock
from time import monotonic

from titan.recovery.exceptions import RecoveryCircuitBreakerError
from titan.recovery.models import CircuitBreakerConfig, CircuitBreakerState


@dataclass(slots=True)
class CircuitBreaker:
    _config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    _state: CircuitBreakerState = CircuitBreakerState.CLOSED
    _failure_count: int = 0
    _success_count: int = 0
    _last_failure_time: float = 0.0
    _last_success_time: float = 0.0
    _half_open_calls: int = 0
    _lock: Lock = field(default_factory=Lock, init=False)

    @property
    def state(self) -> CircuitBreakerState:
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    @property
    def success_count(self) -> int:
        return self._success_count

    @property
    def config(self) -> CircuitBreakerConfig:
        return self._config

    def call(self, action: Callable[[], bool]) -> bool:
        with self._lock:
            if self._state is CircuitBreakerState.OPEN:
                if self._should_attempt_reset():
                    self._state = CircuitBreakerState.HALF_OPEN
                    self._half_open_calls = 0
                else:
                    raise RecoveryCircuitBreakerError("Circuit breaker is OPEN")

            if self._state is CircuitBreakerState.HALF_OPEN:
                if self._half_open_calls >= self._config.half_open_max_calls:
                    raise RecoveryCircuitBreakerError(
                        "Circuit breaker HALF_OPEN: max test calls reached"
                    )
                self._half_open_calls += 1

        try:
            result = action()
        except Exception as exc:
            self._record_failure()
            raise RecoveryCircuitBreakerError(
                f"Circuit breaker call failed: {exc}"
            ) from exc

        if result:
            self._record_success()
        else:
            self._record_failure()

        return result

    def _record_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = monotonic()
            self._success_count = 0

            if self._state is CircuitBreakerState.HALF_OPEN:
                self._state = CircuitBreakerState.OPEN
                return

            if self._failure_count >= self._config.failure_threshold:
                self._state = CircuitBreakerState.OPEN

    def _record_success(self) -> None:
        with self._lock:
            self._success_count += 1
            self._last_success_time = monotonic()

            if self._state is CircuitBreakerState.HALF_OPEN:
                if self._success_count >= self._config.success_threshold:
                    self._state = CircuitBreakerState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    self._half_open_calls = 0

    def _should_attempt_reset(self) -> bool:
        elapsed = monotonic() - self._last_failure_time
        return elapsed >= self._config.recovery_timeout_seconds

    def reset(self) -> None:
        with self._lock:
            self._state = CircuitBreakerState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = 0.0
            self._last_success_time = 0.0
            self._half_open_calls = 0

    def __repr__(self) -> str:
        return (
            f"CircuitBreaker(state={self._state.value}, "
            f"failures={self._failure_count}, "
            f"successes={self._success_count})"
        )
