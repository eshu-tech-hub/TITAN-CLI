"""
Angel One session management.

Handles JWT, refresh token and feed token.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class AngelOneSession:
    """
    Represents an authenticated Angel One session.
    """

    jwt_token: str
    refresh_token: str
    feed_token: str

    @property
    def authenticated(self) -> bool:
        return bool(
            self.jwt_token
            and self.refresh_token
            and self.feed_token
        )