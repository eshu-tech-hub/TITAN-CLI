from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock

from titan.recovery.exceptions import RecoveryReconnectError
from titan.recovery.models import (
    BrokerSessionState,
    ReconnectStrategy,
    RecoveryStatus,
    RetryPolicy,
)
from titan.recovery.retry import RetryEngine

ReconnectAction = Callable[[], bool]
HeartbeatCheck = Callable[[], bool]
SubscriptionRestore = Callable[[tuple[str, ...]], bool]


@dataclass(slots=True)
class BrokerReconnector:
    _strategy: ReconnectStrategy = ReconnectStrategy.GRACEFUL
    _retry_policy: RetryPolicy = field(
        default_factory=lambda: RetryPolicy(max_attempts=3, base_delay_seconds=2.0)
    )
    _state: BrokerSessionState = field(default_factory=BrokerSessionState)
    _reconnect_attempts: int = 0
    _last_reconnect_time: datetime | None = None
    _lock: Lock = field(default_factory=Lock, init=False)

    @property
    def state(self) -> BrokerSessionState:
        return self._state

    @property
    def reconnect_attempts(self) -> int:
        return self._reconnect_attempts

    def reconnect(
        self,
        action: ReconnectAction,
        heartbeat: HeartbeatCheck | None = None,
        subscriptions: tuple[str, ...] = (),
        restore_subscriptions: SubscriptionRestore | None = None,
    ) -> RecoveryStatus:
        engine = RetryEngine(self._retry_policy)
        result = RecoveryStatus.FAILED

        try:
            result = engine.execute(action)
        except Exception as exc:
            with self._lock:
                self._state = BrokerSessionState(
                    is_connected=False,
                    session_id=self._state.session_id,
                    last_heartbeat=self._state.last_heartbeat,
                    subscriptions=subscriptions,
                    reconnect_attempts=self._reconnect_attempts + 1,
                    error=str(exc),
                )
            raise RecoveryReconnectError(f"Broker reconnection failed: {exc}") from exc

        if result is RecoveryStatus.SUCCESS:
            with self._lock:
                self._reconnect_attempts += 1
                self._last_reconnect_time = datetime.now(timezone.utc)
                self._state = BrokerSessionState(
                    is_connected=True,
                    session_id=self._state.session_id,
                    last_heartbeat=datetime.now(timezone.utc),
                    subscriptions=subscriptions,
                    reconnect_attempts=self._reconnect_attempts,
                )

            if heartbeat is not None:
                try:
                    alive = heartbeat()
                except Exception:
                    alive = False
                if not alive:
                    raise RecoveryReconnectError(
                        "Reconnected but heartbeat verification failed"
                    )

            if subscriptions and restore_subscriptions is not None:
                try:
                    restore_subscriptions(subscriptions)
                except Exception as exc:
                    raise RecoveryReconnectError(
                        f"Reconnected but subscription restoration failed: {exc}"
                    ) from exc

        return result

    def verify_heartbeat(self, heartbeat: HeartbeatCheck) -> bool:
        try:
            alive = heartbeat()
        except Exception:
            alive = False

        with self._lock:
            self._state = BrokerSessionState(
                is_connected=alive,
                session_id=self._state.session_id,
                last_heartbeat=(
                    datetime.now(timezone.utc) if alive else self._state.last_heartbeat
                ),
                subscriptions=self._state.subscriptions,
                reconnect_attempts=self._reconnect_attempts,
                error="" if alive else self._state.error,
            )

        return alive

    def reset(self) -> None:
        with self._lock:
            self._reconnect_attempts = 0
            self._last_reconnect_time = None
            self._state = BrokerSessionState()
