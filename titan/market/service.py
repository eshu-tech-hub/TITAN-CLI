from datetime import datetime

from titan.market.exceptions import MarketDataProviderError
from titan.market.models import Symbol
from titan.market.provider import MarketDataProvider
from titan.market.series import MarketDataSeries
from titan.market.timeframe import Timeframe
from titan.market.validator import validate_candles, validate_historical_request


class MarketDataService:
    """Application service for validated, broker-independent market data."""

    def __init__(self, provider: MarketDataProvider) -> None:
        """Initialize the service.

        Args:
            provider: Broker or vendor adapter implementing MarketDataProvider.
        """

        self._provider = provider

    def get_historical_candles(
        self,
        symbol: Symbol,
        timeframe: Timeframe | str,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
    ) -> MarketDataSeries:
        """Fetch validated historical candles.

        Args:
            symbol: Broker-independent instrument identity.
            timeframe: Canonical candle interval.
            start: Optional inclusive start timestamp.
            end: Optional inclusive end timestamp.
            limit: Optional maximum number of candles to return.

        Returns:
            A validated market data series.

        Raises:
            MarketDataValidationError: If request or response data is invalid.
            MarketDataProviderError: If the provider raises an unexpected error.
        """

        normalized_timeframe = validate_historical_request(
            symbol,
            timeframe,
            start=start,
            end=end,
            limit=limit,
        )

        try:
            candles = list(
                self._provider.get_historical_candles(
                    symbol,
                    normalized_timeframe,
                    start=start,
                    end=end,
                    limit=limit,
                )
            )
        except Exception as exc:
            raise MarketDataProviderError("Provider failed to fetch candles.") from exc

        validate_candles(candles)
        return MarketDataSeries(candles)
