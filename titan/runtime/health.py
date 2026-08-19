from dataclasses import dataclass, field
from datetime import UTC, datetime

from titan.runtime.exceptions import HealthError
from titan.runtime.models import ComponentHealth, HealthStatus


@dataclass(slots=True)
class HealthCheck:
    """Aggregate health monitor for all runtime components.

    Collects and exposes health status from the stream, scheduler,
    heartbeat, broker, pipeline, and the runtime engine itself.

    Attributes:
        _components: Map of component name -> ComponentHealth.
    """

    _components: dict[str, ComponentHealth] = field(default_factory=dict, init=False)

    def register(self, component_name: str) -> ComponentHealth:
        """Register a new component for health tracking.

        Args:
            component_name: Unique component identifier.

        Returns:
            The initial ComponentHealth.

        Raises:
            HealthError: If the component is already registered.
        """
        if component_name in self._components:
            raise HealthError(f"Component '{component_name}' is already registered.")

        health = ComponentHealth(
            component_name=component_name,
            status=HealthStatus.UNKNOWN,
        )
        self._components[component_name] = health
        return health

    def unregister(self, component_name: str) -> None:
        """Remove a component from health tracking.

        Args:
            component_name: Component to remove.

        Raises:
            HealthError: If the component is not registered.
        """
        if component_name not in self._components:
            raise HealthError(f"Component '{component_name}' is not registered.")
        del self._components[component_name]

    def report_healthy(
        self,
        component_name: str,
        latency_ms: float = 0.0,
        metadata: dict | None = None,
    ) -> None:
        """Report a component as healthy.

        Args:
            component_name: Component name.
            latency_ms: Current latency.
            metadata: Optional metadata.
        """
        self._update(
            component_name,
            HealthStatus.HEALTHY,
            latency_ms=latency_ms,
            metadata=metadata,
        )

    def report_degraded(
        self,
        component_name: str,
        error: str = "",
        latency_ms: float = 0.0,
        metadata: dict | None = None,
    ) -> None:
        """Report a component as degraded.

        Args:
            component_name: Component name.
            error: Description of the degradation.
            latency_ms: Current latency.
            metadata: Optional metadata.
        """
        self._update(
            component_name,
            HealthStatus.DEGRADED,
            error=error,
            latency_ms=latency_ms,
            metadata=metadata,
        )

    def report_unhealthy(
        self,
        component_name: str,
        error: str = "",
        metadata: dict | None = None,
    ) -> None:
        """Report a component as unhealthy.

        Args:
            component_name: Component name.
            error: Description of the error.
            metadata: Optional metadata.
        """
        self._update(
            component_name,
            HealthStatus.UNHEALTHY,
            error=error,
            metadata=metadata,
        )

    def get(self, component_name: str) -> ComponentHealth | None:
        """Get health for a specific component.

        Args:
            component_name: Component name.

        Returns:
            ComponentHealth if found, None otherwise.
        """
        return self._components.get(component_name)

    def all_health(self) -> list[ComponentHealth]:
        """Get health for all registered components.

        Returns:
            List of all ComponentHealth objects.
        """
        return list(self._components.values())

    def is_healthy(self) -> bool:
        """Whether all components are healthy.

        Returns:
            True if no component is unhealthy or degraded.
        """
        return all(c.status == HealthStatus.HEALTHY for c in self._components.values())

    def has_degraded(self) -> bool:
        """Whether any component is degraded.

        Returns:
            True if at least one component is degraded.
        """
        return any(c.status == HealthStatus.DEGRADED for c in self._components.values())

    def has_unhealthy(self) -> bool:
        """Whether any component is unhealthy.

        Returns:
            True if at least one component is unhealthy.
        """
        return any(
            c.status == HealthStatus.UNHEALTHY for c in self._components.values()
        )

    def summary(self) -> dict[str, str]:
        """Get a human-readable summary of all component health.

        Returns:
            Dict mapping component name to health status string.
        """
        return {name: health.status.value for name, health in self._components.items()}

    def _update(
        self,
        component_name: str,
        status: HealthStatus,
        error: str = "",
        latency_ms: float = 0.0,
        metadata: dict | None = None,
    ) -> None:
        """Update health for a component.

        Args:
            component_name: Component name.
            status: New health status.
            error: Error description (if unhealthy).
            latency_ms: Current latency.
            metadata: Optional metadata.
        """
        if component_name not in self._components:
            self._components[component_name] = ComponentHealth(
                component_name=component_name,
            )

        existing = self._components[component_name]
        updated = ComponentHealth(
            component_name=component_name,
            status=status,
            status_changed_at=(
                datetime.now(UTC)
                if existing.status != status
                else existing.status_changed_at
            ),
            last_update=datetime.now(UTC),
            latency_ms=latency_ms,
            error=error,
            metadata=metadata or {},
        )
        self._components[component_name] = updated

    def reset(self) -> None:
        """Clear all component health data."""
        self._components.clear()
