from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class IndicatorResult:
    """
    Standardized result returned by all technical indicators.
    """

    name: str
    value: float
    signal: str = "Neutral"
    metadata: dict[str, Any] = field(default_factory=dict)
