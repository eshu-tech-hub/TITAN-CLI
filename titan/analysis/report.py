from dataclasses import dataclass, field
from datetime import datetime

from titan.analysis.models import IndicatorResult


@dataclass(slots=True)
class AnalysisReport:
    """
    Complete analysis report for a market.
    """

    symbol: str
    timeframe: str
    timestamp: datetime
    indicators: dict[str, IndicatorResult] = field(default_factory=dict)

    def add(self, result: IndicatorResult) -> None:
        self.indicators[result.name] = result

    def get(self, name: str) -> IndicatorResult | None:
        return self.indicators.get(name)

    def has(self, name: str) -> bool:
        return name in self.indicators