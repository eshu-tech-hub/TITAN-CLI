from typing import Any

from titan.broker.base import BrokerBase
from titan.core.logger import logger


class AngelOneBroker(BrokerBase):
    """
    Angel One Broker Adapter.
    """

    def __init__(self) -> None:
        self._logged_in = False

    def login(self) -> bool:
        logger.info("Angel One login requested.")
        return False

    def logout(self) -> bool:
        logger.info("Angel One logout requested.")
        self._logged_in = False
        return True

    def is_logged_in(self) -> bool:
        return self._logged_in

    def get_profile(self) -> dict[str, Any]:
        logger.info("Fetching profile.")
        return {}

    def get_quote(self, symbol: str) -> dict[str, Any]:
        logger.info(f"Fetching quote for {symbol}")
        return {}
