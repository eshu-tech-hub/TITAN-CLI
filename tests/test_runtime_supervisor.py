from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from titan.recovery.manager import RecoveryManager
from titan.recovery.models import RecoveryLevel
from titan.runtime.supervisor import RuntimeSupervisor


def test_heartbeat_registry_touch_and_evaluate():
    supervisor = RuntimeSupervisor()

    # Simulate a subsystem touching the registry
    supervisor.touch("pipeline")
    assert supervisor.registry.is_healthy("pipeline")

    # Evaluate immediately, should still be healthy
    supervisor.evaluate()
    assert supervisor.registry.is_healthy("pipeline")

    # Simulate time passing by manipulating the last heartbeat
    old_time = datetime.now(timezone.utc) - timedelta(seconds=40)
    supervisor.registry._heartbeats["pipeline"].last_heartbeat = old_time

    # Now it should be degraded
    supervisor.evaluate()
    assert not supervisor.registry.is_healthy("pipeline")
    assert supervisor.registry.get_missed_count("pipeline") == 1


def test_watchdog_timeout_escalation():
    recovery_manager = MagicMock(spec=RecoveryManager)
    supervisor = RuntimeSupervisor(recovery_manager=recovery_manager)

    # Make it dead by missing 4 heartbeats
    old_time = datetime.now(timezone.utc) - timedelta(seconds=40)
    supervisor.touch("pipeline")

    for _ in range(4):
        supervisor.registry._heartbeats["pipeline"].last_heartbeat = old_time
        supervisor.evaluate()

    # The coordinator should have requested RESTART_SUBSYSTEM because it hit dead
    recovery_manager.execute.assert_called_with(
        RecoveryLevel.RESTART_SUBSYSTEM,
        "pipeline",
        {"reason": "component_dead", "attempt": 1},
    )
