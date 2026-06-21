from titan.broker.base import Broker
from titan.core.logger import logger
from titan.market.series import MarketDataSeries


class AngelOneBroker(Broker):
    """
    Angel One broker implementation.
    """

    def __init__(self) -> None:
        self._authenticated = False

    def login(self) -> None:
        logger.info("Angel One login requested.")
        self._authenticated = True

    def logout(self) -> None:
        logger.info("Angel One logout requested.")
        self._authenticated = False

    def is_authenticated(self) -> bool:
        return self._authenticated

    def get_history(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
    ) -> MarketDataSeries:
        logger.info(
            f"History requested: {symbol} {timeframe} ({limit} candles)"
        )
        raise NotImplementedError(
            "SmartAPI integration will be implemented in Sprint 3."
        )