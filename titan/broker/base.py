from abc import ABC, abstractmethod

from titan.market.series import MarketDataSeries


class Broker(ABC):
    """
    Abstract broker interface.
    """

    @abstractmethod
    def login(self) -> None:
        """Authenticate with broker."""

    @abstractmethod
    def logout(self) -> None:
        """Logout from broker."""

    @abstractmethod
    def is_authenticated(self) -> bool:
        """Return authentication state."""

    @abstractmethod
    def get_history(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
    ) -> MarketDataSeries:
        """Fetch historical candles."""