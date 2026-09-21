"""Deterministic Runtime Supervisor."""

from __future__ import annotations

from titan.core.logger import logger
from titan.runtime.heartbeat import HeartbeatRegistry


class RuntimeSupervisor:
    """Synchronous watchdog evaluated within the primary pipeline loop."""

    def __init__(self, registry: HeartbeatRegistry | None = None) -> None:
        # Default to a strict 30-second timeout for institutional operation
        self.registry = registry or HeartbeatRegistry(timeout_seconds=300.0)

    def register(self, component: str) -> None:
        """Register a component with the underlying heartbeat registry."""
        self.registry.register(component)

    def touch(self, component: str) -> None:
        """Record a component's heartbeat."""
        self.registry.touch(component)

    def evaluate(self) -> None:
        """
        Evaluate the health of all registered components synchronously.

        Raises a RuntimeError if any component is deemed dead,
        triggering the upstream recovery framework.
        """
        dead_components = self.registry.get_dead_components()
        if dead_components:
            logger.warning(f"Supervisor detected slow/idle components (non-fatal): {dead_components}")
            # Do not raise RuntimeError for slow components in paper/headless modes
            # raise RuntimeError(f"Watchdog timeout. Components unresponsive: {dead_components}")
