from titan.market.models import Candle


def validate_candles(candles: list[Candle]) -> None:
    """
    Validate a list of market candles.

    Raises:
        ValueError: If candle data is invalid.
    """

    if not candles:
        raise ValueError("Candle list cannot be empty.")

    for candle in candles:

        if candle.high < candle.low:
            raise ValueError("High price cannot be lower than low price.")

        if candle.open < 0:
            raise ValueError("Open price cannot be negative.")

        if candle.close < 0:
            raise ValueError("Close price cannot be negative.")

        if candle.volume < 0:
            raise ValueError("Volume cannot be negative.")