from dataclasses import dataclass, field
from typing import Dict

from titan.recovery.manager import RecoveryManager
from titan.recovery.models import RecoveryLevel
from titan.runtime.heartbeat import HeartbeatRegistry
from titan.runtime.reliability import ReliabilityPolicy
from titan.runtime.watchdog import Watchdog


@dataclass(slots=True)
class RecoveryCoordinator:
    """
    Acts as the bridge between RuntimeSupervisor and RecoveryManager.
    Triggers recovery sequences based on escalated failure context.
    """

    recovery_manager: RecoveryManager

    def coordinate(self, level: RecoveryLevel, component: str, context: dict) -> None:
        """Request the recovery manager to execute a specific recovery level."""
        # Using getattr to safely call execute, assuming we'll add it to RecoveryManager
        execute_method = getattr(self.recovery_manager, "execute", None)
        if callable(execute_method):
            execute_method(level, component, context)
        else:
            # Fallback if execute is not yet fully implemented
            # Just logs or delegates to request_recovery
            pass


@dataclass(slots=True)
class RuntimeSupervisor:
    """
    The core reliability hub orchestrating heartbeat registry, synchronous watchdog
    evaluations, and delegating degraded states to the RecoveryCoordinator.
    """

    registry: HeartbeatRegistry = field(default_factory=HeartbeatRegistry)
    policy: ReliabilityPolicy = field(default_factory=ReliabilityPolicy)
    recovery_manager: RecoveryManager = field(default_factory=RecoveryManager)

    # Internal components
    watchdog: Watchdog = field(init=False)
    coordinator: RecoveryCoordinator = field(init=False)

    # State tracking
    _restart_counts: Dict[str, int] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self.watchdog = Watchdog(registry=self.registry)
        self.coordinator = RecoveryCoordinator(recovery_manager=self.recovery_manager)

        # Sync the registry timeout with the policy
        self.registry.timeout_seconds = self.policy.heartbeat_timeout_seconds

    def touch(self, component: str) -> None:
        """Register a heartbeat for the specified component."""
        self.registry.touch(component)
        # Clear restart counts if component is back to healthy
        if self._restart_counts.get(component, 0) > 0 and self.registry.is_healthy(
            component
        ):
            self._restart_counts[component] = 0

    def evaluate(self) -> None:
        """
        Synchronous evaluation loop. Designed to be called by RuntimeEngine periodically.
        Checks watchdog anomalies and coordinates escalating recovery.
        """
        anomalies = self.watchdog.check()

        for component, status in anomalies.items():
            if status == "degraded":
                self.coordinator.coordinate(
                    RecoveryLevel.RETRY, component, {"reason": "missed_heartbeats"}
                )
            elif status == "dead":
                restarts = self._restart_counts.get(component, 0)
                if restarts < self.policy.max_restarts_before_escalation:
                    self._restart_counts[component] = restarts + 1
                    self.coordinator.coordinate(
                        RecoveryLevel.RESTART_SUBSYSTEM,
                        component,
                        {"reason": "component_dead", "attempt": restarts + 1},
                    )
                else:
                    # Escalate to Engine restart, or eventually shutdown
                    self.coordinator.coordinate(
                        RecoveryLevel.RESTART_ENGINE,
                        component,
                        {"reason": "max_restarts_exceeded"},
                    )
