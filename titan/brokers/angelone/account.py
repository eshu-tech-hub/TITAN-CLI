from typing import Any

from titan.brokers.angelone.exceptions import translate_error
from titan.brokers.angelone.mapper import (
    funds_from_smartapi,
    margin_from_smartapi,
    profile_from_smartapi,
)
from titan.brokers.models import AccountProfile, FundsInfo, MarginInfo


class AngelOneAccountProvider:
    """Account information provider using the Angel One SmartAPI.

    Implements the AccountProvider interface defined in
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

    def funds(self) -> FundsInfo:
        """Fetch account funds summary."""
        sc = self._require_client()
        try:
            response = sc.getFundsAndMargin()
        except Exception as exc:
            raise translate_error(exc) from exc
        data = self._extract_data(response)
        return funds_from_smartapi(data)

    def margin(self) -> MarginInfo:
        """Fetch account margin details."""
        sc = self._require_client()
        try:
            response = sc.getFundsAndMargin()
        except Exception as exc:
            raise translate_error(exc) from exc
        data = self._extract_data(response)
        return margin_from_smartapi(data)

    def profile(self) -> AccountProfile:
        """Fetch authenticated account profile."""
        sc = self._require_client()
        try:
            response = sc.getProfile(sc.refreshToken)
        except Exception as exc:
            raise translate_error(exc) from exc
        data = self._extract_data(response)
        return profile_from_smartapi(data)

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
    def _extract_data(response: Any) -> dict[str, Any]:
        if isinstance(response, dict):
            data = response.get("data") or {}
            if isinstance(data, dict):
                return data
            if isinstance(data, list) and data:
                return dict(data[0]) if isinstance(data[0], dict) else {}
            return {}
        return {}
