from dataclasses import dataclass
from typing import Dict

from titan.runtime.heartbeat import HeartbeatRegistry


@dataclass(slots=True)
class Watchdog:
    """
    Synchronous watchdog that evaluates the HeartbeatRegistry to detect
    stalled subsystems or deadlocks. This is designed to be executed
    inline during the main RuntimeEngine heartbeat loop, avoiding thread complexity.
    """

    registry: HeartbeatRegistry

    def check(self) -> Dict[str, str]:
        """
        Evaluate health and return status report of anomalous components.
        Returns a dictionary mapping anomalous component names to their status
        (e.g., 'degraded', 'dead'). Returns an empty dict if all is well.
        """
        report = self.registry.evaluate_health()
        return {
            component: status
            for component, status in report.items()
            if status != "healthy"
        }
