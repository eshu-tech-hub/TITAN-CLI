"""Synchronous heartbeat registry for component liveness tracking."""

from __future__ import annotations

from datetime import UTC, datetime


class HeartbeatRegistry:
    """Deterministic registry for component check-ins without background threads."""

    def __init__(self, timeout_seconds: float = 300.0) -> None:
        self.timeout_seconds = timeout_seconds
        self._beats: dict[str, datetime] = {}

    def register(self, component: str) -> None:
        """Register a component for heartbeat tracking."""
        self._beats[component] = datetime.now(UTC)

    def touch(self, component: str) -> None:
        """Update the last active timestamp for a registered component."""
        # Auto-register if not present to match the engine's lazy usage pattern
        if component not in self._beats:
            self.register(component)
        else:
            self._beats[component] = datetime.now(UTC)

    def get_dead_components(self) -> list[str]:
        """Identify components that have not checked in within the timeout window."""
        now = datetime.now(UTC)
        dead = []
        for comp, last_beat in self._beats.items():
            if (now - last_beat).total_seconds() > self.timeout_seconds:
                dead.append(comp)
        return dead

    def clear(self) -> None:
        """Clear all registered heartbeats."""
        self._beats.clear()
