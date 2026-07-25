from unittest.mock import patch

from titan.recovery.manager import RecoveryManager
from titan.recovery.models import ComponentType, RecoveryLevel, RecoveryStrategy


def test_recovery_sequencing_levels():
    manager = RecoveryManager()

    with patch.object(RecoveryManager, "request_recovery") as mock_req:
        # Test Level 1: Retry
        manager.execute(RecoveryLevel.RETRY, "pipeline", {})
        mock_req.assert_called_with(
            ComponentType.PIPELINE, "degraded", RecoveryStrategy.RETRY, {}
        )

        # Test Level 2: Restart Subsystem
        manager.execute(RecoveryLevel.RESTART_SUBSYSTEM, "broker_session", {})
        mock_req.assert_called_with(
            ComponentType.BROKER_SESSION, "dead", RecoveryStrategy.RESTART, {}
        )

        # Test Level 3: Restart Engine
        manager.execute(RecoveryLevel.RESTART_ENGINE, "pipeline", {})
        mock_req.assert_called_with(
            ComponentType.PIPELINE, "escalated_failure", RecoveryStrategy.ESCALATE, {}
        )

        # Test Level 4: Graceful Shutdown
        manager.execute(RecoveryLevel.GRACEFUL_SHUTDOWN, "pipeline", {})
        mock_req.assert_called_with(
            ComponentType.PIPELINE, "unrecoverable", RecoveryStrategy.SHUTDOWN, {}
        )
