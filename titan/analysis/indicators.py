from titan.market.models import Candle


def sma(candles: list[Candle], period: int) -> float:
    """
    Calculate Simple Moving Average.
    """
    if period <= 0:
        raise ValueError("Period must be greater than zero.")

    if len(candles) < period:
        raise ValueError("Not enough candles.")

    closes = [c.close for c in candles[-period:]]
    return sum(closes) / period


def ema(candles: list[Candle], period: int) -> float:
    """
    Calculate Exponential Moving Average.
    """

    if period <= 0:
        raise ValueError("Period must be greater than zero.")

    if len(candles) < period:
        raise ValueError("Not enough candles.")

    closes = [c.close for c in candles]

    multiplier = 2 / (period + 1)

    ema_value = sum(closes[:period]) / period

    for price in closes[period:]:
        ema_value = (price - ema_value) * multiplier + ema_value

    return ema_value