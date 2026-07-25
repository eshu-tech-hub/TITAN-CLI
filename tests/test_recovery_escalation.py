from titan.recovery.manager import RecoveryManager
from titan.recovery.models import RecoveryStrategy


def test_recovery_escalation_path():
    """Verify that repeated failures escalate through the proper strategic tiers."""
    # 2 Retries -> 1 Component Restart -> 1 Runtime Restart -> Shutdown
    manager = RecoveryManager(max_retries=2, max_restarts=1)

    # Attempt 1: Retry
    assert manager.handle_failure("stream", "timeout") == RecoveryStrategy.RETRY

    # Attempt 2: Retry
    assert manager.handle_failure("stream", "timeout") == RecoveryStrategy.RETRY

    # Attempt 3: Restart Component
    assert (
        manager.handle_failure("stream", "timeout")
        == RecoveryStrategy.RESTART_COMPONENT
    )

    # Attempt 4: Restart Runtime
    assert (
        manager.handle_failure("stream", "timeout") == RecoveryStrategy.RESTART_RUNTIME
    )

    # Attempt 5: Shutdown
    assert manager.handle_failure("stream", "timeout") == RecoveryStrategy.SHUTDOWN


def test_recovery_success_reset():
    """Verify that a successful recovery resets the component's failure count."""
    manager = RecoveryManager(max_retries=2, max_restarts=1)

    # First failure -> Retry
    assert manager.handle_failure("broker", "disconnect") == RecoveryStrategy.RETRY

    # Mark as recovered
    manager.mark_recovered("broker")

    # Next failure should be treated as a fresh incident -> Retry
    assert manager.handle_failure("broker", "disconnect") == RecoveryStrategy.RETRY


def test_recovery_history_immutability():
    """Verify the history log accurately tracks incidents via frozen DTOs."""
    manager = RecoveryManager()
    manager.handle_failure("scheduler", "stuck")

    history = manager.get_escalation_history()
    assert len(history) == 1
    assert history[0].component == "scheduler"
    assert history[0].strategy == RecoveryStrategy.RETRY
