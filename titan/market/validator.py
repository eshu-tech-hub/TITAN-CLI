from collections.abc import Sequence
from datetime import datetime

from titan.market.exceptions import (
    MarketDataValidationError,
    SymbolValidationError,
    TimeframeValidationError,
)
from titan.market.models import Candle, SymbolIdentifier
from titan.market.timeframe import Timeframe

MIN_PRICE = 0.0
MIN_VOLUME = 0
MIN_LIMIT = 1


def validate_symbol(symbol: SymbolIdentifier) -> None:
    """Validate broker-independent symbol identity.

    Args:
        symbol: Symbol-like object containing exchange and ticker.

    Raises:
        SymbolValidationError: If the symbol is incomplete.
    """

    if not symbol.exchange.strip():
        raise SymbolValidationError("Symbol exchange cannot be empty.")
    if not symbol.ticker.strip():
        raise SymbolValidationError("Symbol ticker cannot be empty.")


def validate_timeframe(timeframe: Timeframe | str) -> Timeframe:
    """Validate and normalize a timeframe.

    Args:
        timeframe: Timeframe enum or canonical string value.

    Returns:
        A canonical timeframe enum.

    Raises:
        TimeframeValidationError: If the timeframe is unsupported.
    """

    try:
        return Timeframe.from_value(timeframe)
    except ValueError as exc:
        raise TimeframeValidationError("Unsupported timeframe.") from exc


def validate_historical_request(
    symbol: SymbolIdentifier,
    timeframe: Timeframe | str,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int | None = None,
) -> Timeframe:
    """Validate a historical candle request.

    Args:
        symbol: Symbol-like object containing exchange and ticker.
        timeframe: Requested candle interval.
        start: Optional inclusive start timestamp.
        end: Optional inclusive end timestamp.
        limit: Optional maximum number of candles to return.

    Returns:
        A canonical timeframe enum.

    Raises:
        MarketDataValidationError: If request inputs are invalid.
    """

    validate_symbol(symbol)
    normalized_timeframe = validate_timeframe(timeframe)

    if start is not None and not isinstance(start, datetime):
        raise MarketDataValidationError("Start must be a datetime.")
    if end is not None and not isinstance(end, datetime):
        raise MarketDataValidationError("End must be a datetime.")
    if start is not None and end is not None and start > end:
        raise MarketDataValidationError("Start cannot be after end.")
    if limit is not None and limit < MIN_LIMIT:
        raise MarketDataValidationError("Limit must be greater than zero.")

    return normalized_timeframe


def validate_candles(candles: Sequence[Candle]) -> None:
    """Validate a sequence of normalized market candles.

    Args:
        candles: Candles returned by a market data provider.

    Raises:
        MarketDataValidationError: If candle data is invalid.
    """

    if not candles:
        raise MarketDataValidationError("Candle list cannot be empty.")

    for candle in candles:

        if not isinstance(candle.timestamp, datetime):
            raise MarketDataValidationError("Candle timestamp must be a datetime.")

        if candle.high < candle.low:
            raise MarketDataValidationError(
                "High price cannot be lower than low price."
            )

        if candle.open < MIN_PRICE:
            raise MarketDataValidationError("Open price cannot be negative.")

        if candle.high < MIN_PRICE:
            raise MarketDataValidationError("High price cannot be negative.")

        if candle.low < MIN_PRICE:
            raise MarketDataValidationError("Low price cannot be negative.")

        if candle.close < MIN_PRICE:
            raise MarketDataValidationError("Close price cannot be negative.")

        if candle.volume < MIN_VOLUME:
            raise MarketDataValidationError("Volume cannot be negative.")
