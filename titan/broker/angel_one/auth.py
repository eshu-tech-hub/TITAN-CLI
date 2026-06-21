"""
Angel One authentication.

Handles login and TOTP authentication.
"""

from SmartApi import SmartConnect
import pyotp

from titan.broker.angel_one.session import AngelOneSession
from titan.config import settings
from titan.core.exceptions import BrokerError
from titan.core.logger import logger


class AngelOneAuthenticator:
    """
    Handles authentication with Angel One SmartAPI.
    """

    def authenticate(self) -> AngelOneSession:
        credentials = settings.angel_one

        logger.info("Authenticating with Angel One.")

        try:
            client = SmartConnect(api_key=credentials.api_key)

            totp = pyotp.TOTP(
                credentials.totp_secret
            ).now()

            response = client.generateSession(
                credentials.client_id,
                credentials.pin,
                totp,
            )

        except Exception as exc:
            raise BrokerError(
                "Authentication failed."
            ) from exc

        if not response:
            raise BrokerError("Empty authentication response.")

        data = response.get("data")

        if not data:
            raise BrokerError("Authentication returned no data.")

        jwt = data.get("jwtToken")
        refresh = data.get("refreshToken")
        feed = client.getfeedToken()

        if not jwt:
            raise BrokerError("JWT token missing.")

        if not refresh:
            raise BrokerError("Refresh token missing.")

        if not feed:
            raise BrokerError("Feed token missing.")

        logger.info("Authentication successful.")

        return AngelOneSession(
            jwt_token=jwt,
            refresh_token=refresh,
            feed_token=feed,
        )