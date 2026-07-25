from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional


@dataclass(slots=True)
class SubsystemHeartbeat:
    """Tracks the heartbeat status of a single subsystem."""

    last_heartbeat: datetime
    missed_count: int = 0
    is_healthy: bool = True


class HeartbeatRegistry:
    """
    Centralized registry for subsystem heartbeats.
    Subsystems call `touch()` to assert liveness.
    The RuntimeSupervisor synchronously evaluates this registry.
    """

    def __init__(self, timeout_seconds: float = 30.0) -> None:
        self.timeout_seconds = timeout_seconds
        self._heartbeats: Dict[str, SubsystemHeartbeat] = {}

    def touch(self, component: str) -> None:
        """Record a manual heartbeat for the given component."""
        now = datetime.now(timezone.utc)
        if component not in self._heartbeats:
            self._heartbeats[component] = SubsystemHeartbeat(last_heartbeat=now)
        else:
            hb = self._heartbeats[component]
            hb.last_heartbeat = now
            hb.missed_count = 0
            hb.is_healthy = True

    def evaluate_health(self) -> dict[str, str]:
        """
        Evaluate the health of all registered subsystems.
        Returns a dictionary mapping component name to its status ("healthy", "degraded", "dead").
        """
        now = datetime.now(timezone.utc)
        status_report = {}

        for component, hb in self._heartbeats.items():
            elapsed = (now - hb.last_heartbeat).total_seconds()

            if elapsed > self.timeout_seconds:
                hb.missed_count += 1
                hb.is_healthy = False

                if hb.missed_count > 3:
                    status_report[component] = "dead"
                else:
                    status_report[component] = "degraded"
            else:
                hb.is_healthy = True
                status_report[component] = "healthy"

        return status_report

    def get_last_heartbeat(self, component: str) -> Optional[datetime]:
        """Get the last heartbeat timestamp for a component."""
        if component in self._heartbeats:
            return self._heartbeats[component].last_heartbeat
        return None

    def get_missed_count(self, component: str) -> int:
        """Get the number of missed heartbeats for a component."""
        if component in self._heartbeats:
            return self._heartbeats[component].missed_count
        return 0

    def is_healthy(self, component: str) -> bool:
        """Check if a specific component is healthy."""
        if component in self._heartbeats:
            return self._heartbeats[component].is_healthy
        return False
