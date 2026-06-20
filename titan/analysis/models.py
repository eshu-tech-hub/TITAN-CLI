from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class IndicatorResult:
    """
    Standard result returned by every indicator.
    """

    name: str
    value: float
    signal: str
    metadata: dict[str, Any]