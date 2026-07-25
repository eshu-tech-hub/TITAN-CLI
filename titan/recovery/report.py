from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any

from titan.recovery.models import RecoveryStatus, ComponentType


@dataclass(frozen=True, slots=True)
class RecoveryStatistics:
    """Aggregated statistics of all recovery attempts over the system's lifetime."""

    total_recoveries_attempted: int = 0
    successful_recoveries: int = 0
    failed_recoveries: int = 0
    recoveries_by_component: Dict[ComponentType, int] = field(default_factory=dict)
    average_recovery_time_seconds: float = 0.0


@dataclass(frozen=True, slots=True)
class RecoveryTimelineEvent:
    """A single chronological event in a recovery sequence."""

    timestamp: datetime
    level: str
    component: ComponentType
    action: str
    status: RecoveryStatus
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RecoveryTimeline:
    """A chronological view of all recovery actions for audit and post-mortem."""

    events: List[RecoveryTimelineEvent] = field(default_factory=list)

    def add_event(self, event: RecoveryTimelineEvent) -> None:
        self.events.append(event)
