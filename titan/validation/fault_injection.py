from enum import Enum, auto
from dataclasses import dataclass
from typing import Callable, Any, Optional


class FaultScenario(Enum):
    BrokerDisconnect = auto()
    SlowBroker = auto()
    BrokerTimeout = auto()
    MarketDataGap = auto()
    EmptyOptionChain = auto()
    StorageFailure = auto()
    DiskFull = auto()
    JournalFailure = auto()
    RecoveryFailure = auto()
    HeartbeatTimeout = auto()
    EventBusOverflow = auto()
    SchedulerDelay = auto()
    PipelineException = auto()
    ConfigurationCorruption = auto()


@dataclass(frozen=True, slots=True)
class FaultInjectionPoint:
    scenario: FaultScenario
    target_component: str
    trigger_condition: Callable[[Any], bool]
    fault_action: Callable[[Any], None]
    recovery_validation: Optional[Callable[[Any], bool]] = None
