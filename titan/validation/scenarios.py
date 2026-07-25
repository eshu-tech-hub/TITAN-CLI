from typing import List
from titan.validation.fault_injection import FaultInjectionPoint


class ValidationScenarioRunner:
    """Executes repeatable scenarios using accelerated deterministic simulation."""

    def __init__(self, speed_multiplier: float = 1.0):
        self.speed_multiplier = speed_multiplier
        self.active_faults: List[FaultInjectionPoint] = []

    def inject_fault(self, fault: FaultInjectionPoint) -> None:
        self.active_faults.append(fault)

    def clear_faults(self) -> None:
        self.active_faults.clear()

    def execute(self) -> None:
        # In a real validation context, this would mount the RuntimeEngine
        # and tick it with the speed multiplier applied to inputs.
        pass
