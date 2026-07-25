from collections.abc import Callable
from dataclasses import dataclass, field
from threading import Lock
from time import monotonic, sleep

from titan.recovery.backoff import get_backoff
from titan.recovery.exceptions import RecoveryRetryError, RecoveryTimeoutError
from titan.recovery.models import RecoveryStatus, RetryPolicy

RetryAction = Callable[[], bool]


@dataclass(slots=True)
class RetryEngine:
    _policy: RetryPolicy
    _attempt_count: int = 0
    _last_error: str = ""
    _lock: Lock = field(default_factory=Lock, init=False)

    @property
    def attempt_count(self) -> int:
        return self._attempt_count

    @property
    def last_error(self) -> str:
        return self._last_error

    def execute(self, action: RetryAction) -> RecoveryStatus:
        backoff = get_backoff(self._policy)
        deadline = 0.0
        if self._policy.timeout_seconds > 0:
            deadline = monotonic() + self._policy.timeout_seconds

        for attempt in range(1, self._policy.max_attempts + 1):
            with self._lock:
                self._attempt_count = attempt

            if self._policy.timeout_seconds > 0 and monotonic() >= deadline:
                raise RecoveryTimeoutError(
                    f"Retry timed out after {self._policy.timeout_seconds}s"
                )

            try:
                result = action()
            except Exception as exc:
                if not self._is_retryable(exc):
                    raise RecoveryRetryError(f"Non-retryable exception: {exc}") from exc
                with self._lock:
                    self._last_error = str(exc)
                if attempt == self._policy.max_attempts:
                    raise RecoveryRetryError(
                        f"All {self._policy.max_attempts} retry attempts exhausted: {exc}"
                    ) from exc
                delay = backoff(attempt)
                sleep(delay)
                continue

            if result:
                return RecoveryStatus.SUCCESS

            with self._lock:
                self._last_error = "Action returned False"
            if attempt == self._policy.max_attempts:
                raise RecoveryRetryError(
                    f"All {self._policy.max_attempts} attempts returned False"
                )
            delay = backoff(attempt)
            sleep(delay)

        return RecoveryStatus.FAILED

    def _is_retryable(self, exc: Exception) -> bool:
        return isinstance(exc, self._policy.retryable_exceptions)

    def reset(self) -> None:
        with self._lock:
            self._attempt_count = 0
            self._last_error = ""
