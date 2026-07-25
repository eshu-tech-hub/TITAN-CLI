from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReliabilityPolicy:
    """
    Policy defining timeouts, retry limits, and escalation rules for Runtime Reliability.
    """

    heartbeat_timeout_seconds: float = 30.0
    max_missed_heartbeats_before_restart: int = 3
    max_restarts_before_escalation: int = 5
    watchdog_check_interval: float = 5.0
