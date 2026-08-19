from collections.abc import Callable
from typing import Any

from titan.brokers.angelone.exceptions import translate_error
from titan.brokers.models import ConnectionStatus

TOTPGenerator = Callable[[str], str]


def default_totp_generator(secret: str) -> str:
    if not secret:
        return ""
    try:
        import pyotp

        return str(pyotp.TOTP(secret).now())
    except ImportError:
        return ""
    except Exception as exc:
        from titan.brokers.exceptions import AuthenticationError

        raise AuthenticationError(f"Failed to generate TOTP: {exc}") from exc


class AngelOneAuthenticator:
    """Handles Angel One SmartAPI authentication lifecycle.

    Accepts credentials via constructor (dependency injection) or
    falls back to reading from titan.config.settings.

    The SmartConnect client is optional and injected for testability.
    When not provided, the authenticator creates its own on login().
    """

    def __init__(
        self,
        api_key: str | None = None,
        client_id: str | None = None,
        pin: str | None = None,
        totp_secret: str | None = None,
        smart_connect: Any | None = None,
        totp_generator: TOTPGenerator | None = None,
    ) -> None:
        self._api_key = api_key
        self._client_id = client_id
        self._pin = pin
        self._totp_secret = totp_secret
        self._smart_connect = smart_connect
        self._totp_generator = totp_generator or default_totp_generator
        self._feed_token: str = ""
        self._refresh_token: str = ""
        self._status: ConnectionStatus = ConnectionStatus.DISCONNECTED

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def login(self) -> ConnectionStatus:
        """Authenticate with Angel One SmartAPI.

        Returns the resulting connection status.

        Raises:
            AuthenticationError: If login fails.
            ConnectionError: If the SmartAPI SDK is unavailable.
        """
        try:
            smart_connect = self._get_smart_connect()
        except ImportError as exc:
            self._status = ConnectionStatus.ERROR
            raise ImportError(
                "SmartAPI SDK is not installed. "
                "Install with: pip install smartapi-python"
            ) from exc

        self._status = ConnectionStatus.CONNECTING

        try:
            totp = self._generate_totp()
            response = smart_connect.generateSession(
                self._get_client_id(),
                self._get_pin(),
                totp,
            )
        except Exception as exc:
            self._status = ConnectionStatus.ERROR
            raise translate_error(exc) from exc

        if not response:
            self._status = ConnectionStatus.ERROR
            from titan.brokers.exceptions import AuthenticationError

            raise AuthenticationError("Empty response from SmartAPI generateSession.")

        data = response.get("data") or {}
        jwt_token = data.get("jwtToken") or data.get("jwt_token") or ""

        if not jwt_token:
            self._status = ConnectionStatus.ERROR
            from titan.brokers.exceptions import AuthenticationError

            raise AuthenticationError("JWT token missing from authentication response.")

        self._refresh_token = (
            data.get("refreshToken") or data.get("refresh_token") or ""
        )

        try:
            self._feed_token = smart_connect.getfeedToken()
        except Exception:
            self._feed_token = ""

        self._smart_connect = smart_connect
        self._status = ConnectionStatus.CONNECTED
        return self._status

    def logout(self) -> ConnectionStatus:
        """Disconnect from Angel One SmartAPI.

        Returns the resulting connection status.
        """
        if self._smart_connect is not None and self._client_id:
            try:
                self._smart_connect.terminateSession(self._client_id)
            except Exception:
                pass

        self._smart_connect = None
        self._feed_token = ""
        self._refresh_token = ""
        self._status = ConnectionStatus.DISCONNECTED
        return self._status

    def refresh_token(self) -> str:
        """Refresh the authentication session token.

        Returns the new refresh token string.

        Raises:
            AuthenticationError: If token refresh fails.
        """
        if self._smart_connect is None or not self._refresh_token:
            from titan.brokers.exceptions import AuthenticationError

            raise AuthenticationError("Cannot refresh token: no active session.")

        try:
            response = self._smart_connect.renewAccessToken(self._refresh_token)
        except Exception as exc:
            self._status = ConnectionStatus.ERROR
            raise translate_error(exc) from exc

        data = response.get("data") or {}
        new_refresh = data.get("refreshToken") or data.get("refresh_token") or ""
        if new_refresh:
            self._refresh_token = new_refresh

        self._status = ConnectionStatus.CONNECTED
        return self._refresh_token

    def validate_session(self) -> bool:
        """Check whether the current session is valid.

        Returns True if the SmartConnect client exists and tokens
        are available.
        """
        return self._smart_connect is not None and bool(self._refresh_token)

    @property
    def connection_status(self) -> ConnectionStatus:
        return self._status

    @property
    def feed_token(self) -> str:
        return self._feed_token

    @property
    def smart_connect(self) -> Any | None:
        return self._smart_connect

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_smart_connect(self) -> Any:
        if self._smart_connect is not None:
            return self._smart_connect
        try:
            from SmartApi import SmartConnect

            return SmartConnect(api_key=self._get_api_key())
        except ImportError:
            raise

    def _generate_totp(self) -> str:
        secret = self._get_totp_secret()
        return self._totp_generator(secret)

    def _get_api_key(self) -> str:
        if self._api_key:
            return self._api_key
        from titan.config.settings import settings

        return settings.angel_api_key

    def _get_client_id(self) -> str:
        if self._client_id:
            return self._client_id
        from titan.config.settings import settings

        return settings.angel_client_id

    def _get_pin(self) -> str:
        if self._pin:
            return self._pin
        from titan.config.settings import settings

        return settings.angel_pin

    def _get_totp_secret(self) -> str:
        if self._totp_secret:
            return self._totp_secret
        from titan.config.settings import settings

        return settings.angel_totp_secret
