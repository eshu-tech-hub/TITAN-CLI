from abc import ABC, abstractmethod
from typing import Any


class BrokerBase(ABC):
    """
    Abstract base class for all broker implementations.
    """

    @abstractmethod
    def login(self) -> bool:
        """Authenticate with the broker."""
        raise NotImplementedError

    @abstractmethod
    def logout(self) -> bool:
        """Terminate the broker session."""
        raise NotImplementedError

    @abstractmethod
    def is_logged_in(self) -> bool:
        """Return True if an active session exists."""
        raise NotImplementedError

    @abstractmethod
    def get_profile(self) -> dict[str, Any]:
        """Return the authenticated user's profile."""
        raise NotImplementedError

    @abstractmethod
    def get_quote(self, symbol: str) -> dict[str, Any]:
        """Fetch the latest market quote."""
        raise NotImplementedError
