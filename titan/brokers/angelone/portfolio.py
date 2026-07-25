from datetime import datetime
from typing import Any

from titan.brokers.angelone.exceptions import translate_error
from titan.brokers.angelone.mapper import (
    holding_from_smartapi,
    position_from_smartapi,
    trade_from_smartapi,
)
from titan.brokers.models import Holding, Position, Trade


class AngelOnePortfolioProvider:
    """Portfolio and position data provider using the Angel One SmartAPI.

    Implements the PortfolioProvider interface defined in
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

    def positions(self) -> list[Position]:
        """Fetch all open positions."""
        sc = self._require_client()
        try:
            response = sc.getPosition()
        except Exception as exc:
            raise translate_error(exc) from exc
        raw = self._extract_data_list(response)
        return [position_from_smartapi(item) for item in raw]

    def holdings(self) -> list[Holding]:
        """Fetch all demat holdings."""
        sc = self._require_client()
        try:
            response = sc.holdings()
        except Exception as exc:
            raise translate_error(exc) from exc
        raw = self._extract_data_list(response)
        return [holding_from_smartapi(item) for item in raw]

    def trades(
        self,
        symbol: str | None = None,
        since: datetime | None = None,
    ) -> list[Trade]:
        """Fetch executed trades, optionally filtered."""
        sc = self._require_client()
        try:
            response = sc.getTradeBook()
        except Exception as exc:
            raise translate_error(exc) from exc
        raw = self._extract_data_list(response)
        result: list[Trade] = []
        for item in raw:
            trade = trade_from_smartapi(item)
            if symbol and trade.symbol != symbol:
                continue
            if since and trade.trade_time and trade.trade_time < since:
                continue
            result.append(trade)
        return result

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
    def _extract_data_list(response: Any) -> list[dict[str, Any]]:
        if isinstance(response, dict):
            data = response.get("data") or []
            if isinstance(data, list):
                return [dict(d) for d in data if isinstance(d, dict)]
            return []
        return []
