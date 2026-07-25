from enum import Enum, auto


class StressTarget(Enum):
    DecisionJournal = auto()
    TradeJournal = auto()
    Replay = auto()
    Configuration = auto()
    Recovery = auto()
    Scheduler = auto()
    Pipeline = auto()
    TUI = auto()
    CLI = auto()
    Storage = auto()
    Alerting = auto()
    Monitoring = auto()


class SubsystemStressor:
    """Bombards independent subsystems to detect bottlenecks."""

    def __init__(self, target: StressTarget, volume: int):
        self.target = target
        self.volume = volume

    def run(self) -> None:
        # Generate N volume of operations targeted specifically at the isolated subsystem
        pass
