import random
from collections.abc import Callable
from dataclasses import dataclass, field
from threading import Lock
from time import monotonic

from titan.recovery.models import RetryMode, RetryPolicy

BackoffFunc = Callable[[int], float]


def _immediate(attempt: int) -> float:
    return 0.0


def _fixed_delay(policy: RetryPolicy) -> BackoffFunc:
    def inner(attempt: int) -> float:
        return policy.base_delay_seconds

    return inner


def _linear_backoff(policy: RetryPolicy) -> BackoffFunc:
    def inner(attempt: int) -> float:
        delay = policy.base_delay_seconds * attempt
        return min(delay, policy.max_delay_seconds)

    return inner


def _exponential_backoff(policy: RetryPolicy) -> BackoffFunc:
    def inner(attempt: int) -> float:
        delay = policy.base_delay_seconds * (2.0 ** (attempt - 1))
        return min(delay, policy.max_delay_seconds)

    return inner


def _exponential_jitter(policy: RetryPolicy) -> BackoffFunc:
    def inner(attempt: int) -> float:
        base = policy.base_delay_seconds * (2.0 ** (attempt - 1))
        capped = min(base, policy.max_delay_seconds)
        jitter = random.uniform(0, capped * policy.jitter_factor)
        return capped + jitter

    return inner


_BACKOFF_MAP: dict[RetryMode, Callable[[RetryPolicy], BackoffFunc]] = {
    RetryMode.IMMEDIATE: lambda _: _immediate,
    RetryMode.FIXED_DELAY: _fixed_delay,
    RetryMode.LINEAR_BACKOFF: _linear_backoff,
    RetryMode.EXPONENTIAL_BACKOFF: _exponential_backoff,
    RetryMode.EXPONENTIAL_JITTER: _exponential_jitter,
}


def get_backoff(policy: RetryPolicy) -> BackoffFunc:
    factory = _BACKOFF_MAP.get(policy.mode, _exponential_backoff)
    return factory(policy)


@dataclass(slots=True)
class BackoffCalculator:
    _policy: RetryPolicy
    _lock: Lock = field(default_factory=Lock, init=False)

    def delay(self, attempt: int) -> float:
        if attempt < 1:
            return 0.0
        backoff = get_backoff(self._policy)
        with self._lock:
            return backoff(attempt)

    def total_timeout(self, max_wait: float = 0.0) -> float:
        total = 0.0
        limit = max_wait if max_wait > 0 else self._policy.timeout_seconds
        for i in range(1, self._policy.max_attempts + 1):
            total += self.delay(i)
            if limit > 0 and total >= limit:
                return limit
        return total

    def deadline(self, max_wait: float = 0.0) -> float:
        return monotonic() + self.total_timeout(max_wait)
