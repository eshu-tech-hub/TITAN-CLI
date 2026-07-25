from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from titan.brokers.angelone.exceptions import translate_error
from titan.brokers.angelone.mapper import candle_from_smartapi
from titan.brokers.models import Candle


class AngelOneHistoricalDataProvider:
    """Historical data provider using the Angel One SmartAPI.

    Implements the HistoricalDataProvider interface defined in
    titan.brokers.broker.
    """

    _INTERVAL_MAP: dict[str, str] = {
        "1min": "ONE_MINUTE",
        "3min": "THREE_MINUTE",
        "5min": "FIVE_MINUTE",
        "10min": "TEN_MINUTE",
        "15min": "FIFTEEN_MINUTE",
        "30min": "THIRTY_MINUTE",
        "60min": "ONE_HOUR",
        "1day": "ONE_DAY",
        "1week": "ONE_WEEK",
        "1month": "ONE_MONTH",
    }

    def __init__(self, smart_connect: Any | None = None) -> None:
        self._smart_connect = smart_connect

    @property
    def smart_connect(self) -> Any | None:
        return self._smart_connect

    @smart_connect.setter
    def smart_connect(self, value: Any | None) -> None:
        self._smart_connect = value

    def history(
        self,
        symbol: str,
        interval: str = "1day",
        start: datetime | None = None,
        end: datetime | None = None,
        exchange: str = "NSE",
    ) -> list[Candle]:
        """Fetch historical candles for a date range."""
        sc = self._require_client()
        smart_interval = self._INTERVAL_MAP.get(interval, "ONE_DAY")
        from_date = start or datetime.now(timezone.utc)
        to_date = end or datetime.now(timezone.utc)

        params: dict[str, Any] = {
            "symbol": symbol,
            "exchange": exchange,
            "interval": smart_interval,
            "fromdate": from_date.strftime("%Y-%m-%d %H:%M"),
            "todate": to_date.strftime("%Y-%m-%d %H:%M"),
        }

        try:
            response = sc.getCandleData(params)
        except Exception as exc:
            raise translate_error(exc) from exc

        return self._parse_candle_response(response)

    def intraday(
        self,
        symbol: str,
        interval: str = "1min",
        exchange: str = "NSE",
    ) -> list[Candle]:
        """Fetch intraday candles for the current trading day."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        start = datetime.fromisoformat(f"{today} 09:15:00+00:00")
        end = datetime.fromisoformat(f"{today} 15:30:00+00:00")
        return self.history(symbol, interval, start, end, exchange)

    def ohlcv(
        self,
        symbol: str,
        interval: str = "1day",
        limit: int = 100,
        exchange: str = "NSE",
    ) -> list[Candle]:
        """Fetch the most recent OHLCV candles."""
        end = datetime.now(timezone.utc)
        days = limit * 2 if interval == "1day" else limit
        start = end.replace(hour=9, minute=15, second=0, microsecond=0)
        start = start.replace(day=start.day - min(days, 365))
        result = self.history(symbol, interval, start, end, exchange)
        return result[-limit:] if len(result) > limit else result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_client(self) -> Any:
        if self._smart_connect is None:
            from titan.brokers.exceptions import ConnectionError

            raise ConnectionError(
                "SmartAPI client is not available. Call connect() first."
            )
        return self._smart_connect

    @staticmethod
    def _parse_candle_response(response: Any) -> list[Candle]:
        """Parse the SmartAPI candle data response.

        SmartAPI returns candle data as a list of lists:
        [
            ["2026-07-03 09:15:00", 2500.0, 2510.0, 2490.0, 2505.0, 100000, 0],
            ...
        ]
        """
        candles: list[Candle] = []
        if isinstance(response, dict):
            data = response.get("data")
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, list) and len(item) >= 6:
                        try:
                            ts = datetime.fromisoformat(str(item[0]))
                        except ValueError, TypeError:
                            ts = datetime.now(timezone.utc)
                        candle = Candle(
                            datetime=ts,
                            open=(
                                Decimal(str(item[1]))
                                if item[1] is not None
                                else Decimal("0")
                            ),
                            high=(
                                Decimal(str(item[2]))
                                if item[2] is not None
                                else Decimal("0")
                            ),
                            low=(
                                Decimal(str(item[3]))
                                if item[3] is not None
                                else Decimal("0")
                            ),
                            close=(
                                Decimal(str(item[4]))
                                if item[4] is not None
                                else Decimal("0")
                            ),
                            volume=int(item[5]) if item[5] is not None else 0,
                            oi=(
                                int(item[6])
                                if len(item) > 6 and item[6] is not None
                                else None
                            ),
                        )
                        candles.append(candle)
                    elif isinstance(item, dict):
                        candles.append(candle_from_smartapi(item))
        return candles
