from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Candle:
    """
    Represents one OHLCV candle.
    """

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int