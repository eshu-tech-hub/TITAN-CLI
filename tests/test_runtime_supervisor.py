import time

import pytest

from titan.runtime.exceptions import RuntimeError
from titan.runtime.heartbeat import HeartbeatRegistry
from titan.runtime.supervisor import RuntimeSupervisor


def test_heartbeat_registry_registration_and_touch():
    """Verify that touching components prevents them from being flagged as dead."""
    registry = HeartbeatRegistry(timeout_seconds=5.0)
    registry.register("pipeline")

    assert len(registry.get_dead_components()) == 0

    registry.touch("pipeline")
    assert len(registry.get_dead_components()) == 0


def test_heartbeat_registry_timeout():
    """Verify that elapsed time triggers a dead component detection."""
    registry = HeartbeatRegistry(timeout_seconds=0.1)
    registry.register("broker")

    time.sleep(0.15)
    dead = registry.get_dead_components()
    assert "broker" in dead


def test_supervisor_evaluation_healthy():
    """Ensure the supervisor evaluates healthy components without raising exceptions."""
    supervisor = RuntimeSupervisor()
    supervisor.touch("scheduler")

    # Should safely pass
    supervisor.evaluate()


def test_supervisor_evaluation_unhealthy():
    """Ensure the supervisor raises a deterministic RuntimeError on watchdog timeout."""
    registry = HeartbeatRegistry(timeout_seconds=0.01)
    supervisor = RuntimeSupervisor(registry=registry)

    supervisor.touch("stream")
    time.sleep(0.05)

    with pytest.raises(RuntimeError, match="Watchdog timeout"):
        supervisor.evaluate()
