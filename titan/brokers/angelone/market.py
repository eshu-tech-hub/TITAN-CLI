from decimal import Decimal
from typing import Any

from titan.brokers.angelone.exceptions import translate_error
from titan.brokers.angelone.mapper import (
    market_depth_from_smartapi,
    quote_from_smartapi,
)
from titan.brokers.models import MarketDepth, Quote


class AngelOneMarketDataProvider:
    """Market data provider using the Angel One SmartAPI.

    Implements the MarketDataProvider interface defined in
    titan.brokers.broker.
    """

    def __init__(self, smart_connect: Any | None = None) -> None:
        self._smart_connect = smart_connect

    @property
    def smart_connect(self) -> Any | None:
        return self._smart_connect

    @smart_connect.setter
    def smart_connect(self, value: Any | None) -> None:
        self._smart_connect = value

    def ltp(self, symbol: str, exchange: str = "NSE") -> Decimal:
        """Fetch the last traded price for a symbol."""
        data = self._fetch_quote(symbol, exchange)
        ltp_val = data.get("ltp") or data.get("last_price") or 0
        return Decimal(str(ltp_val))

    def quote(self, symbol: str, exchange: str = "NSE") -> Quote:
        """Fetch a single snapshot quote."""
        data = self._fetch_quote(symbol, exchange)
        return quote_from_smartapi(data)

    def quotes(self, symbols: list[str], exchange: str = "NSE") -> dict[str, Quote]:
        """Fetch snapshot quotes for multiple symbols."""
        result: dict[str, Quote] = {}
        for sym in symbols:
            try:
                result[sym] = self.quote(sym, exchange)
            except Exception:
                continue
        return result

    def option_chain(
        self,
        symbol: str,
        expiry: str | None = None,
        exchange: str = "NFO",
    ) -> list[Quote]:
        """Fetch option chain quotes for a given underlying."""
        result: list[Quote] = []
        try:
            sc = self._require_client()
            params: dict[str, Any] = {
                "symbol": symbol,
                "exchange": exchange,
            }
            if expiry:
                params["expiry"] = expiry
            response = sc.optionChain(params)
            data_list = self._extract_data_list(response)
            for item in data_list:
                result.append(quote_from_smartapi(item))
        except Exception as exc:
            raise translate_error(exc) from exc
        return result

    def market_depth(self, symbol: str, exchange: str = "NSE") -> MarketDepth:
        """Fetch order book depth."""
        try:
            sc = self._require_client()
            response = sc.getMarketDepth(
                {
                    "symbol": symbol,
                    "exchange": exchange,
                }
            )
            data = self._extract_data(response)
            return market_depth_from_smartapi(data)
        except Exception as exc:
            raise translate_error(exc) from exc

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

    def _fetch_quote(self, symbol: str, exchange: str) -> dict[str, Any]:
        sc = self._require_client()
        try:
            params: dict[str, Any] = {
                "symbol": symbol,
                "exchange": exchange,
            }
            response = sc.getMarketData(params)
            return self._extract_data(response)
        except Exception as exc:
            raise translate_error(exc) from exc

    @staticmethod
    def _extract_data(response: Any) -> dict[str, Any]:
        if isinstance(response, dict):
            data = response.get("data") or {}
            if isinstance(data, dict):
                return data
            if isinstance(data, list) and data:
                return dict(data[0]) if isinstance(data[0], dict) else {}
            if isinstance(data, list):
                return {}
            return {}
        return {}

    @staticmethod
    def _extract_data_list(response: Any) -> list[dict[str, Any]]:
        if isinstance(response, dict):
            data = response.get("data") or []
            if isinstance(data, list):
                return [dict(d) for d in data if isinstance(d, dict)]
            return []
        return []
